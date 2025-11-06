# esm2pdf.py
# Gera um PDF único com o conteúdo de https://engsoftmoderna.info/
# - Mantém ordem: cap0 -> cap1..cap10 -> capAp (Apêndice)
# - Depois inclui demais caminhos internos (artigos, FAQ, etc.)
# - Compatível com Python 3.13 e Pyppeteer, usando Chrome/Edge local
#
# Como usar:
#   pip install pyppeteer==1.0.2 pypdf==5.0.1 beautifulsoup4==4.12.3 urllib3==2.2.3
#   python esm2pdf.py

import asyncio
import os
import re
import sys
import shutil
import pathlib
import urllib.parse as up
import urllib.request as ur
from collections import OrderedDict, deque
from typing import List, Optional

from bs4 import BeautifulSoup
from pypdf import PdfWriter, PdfReader
from pyppeteer import launch

BASE = "https://engsoftmoderna.info"
OUT_DIR = "esm_pdf_pages"
FINAL_PDF = "Engenharia_de_Software_Moderna_site_completo.pdf"

# Ordem canônica dos capítulos
CHAPTERS_IN_ORDER = [
    "/cap0.html",   # Prefácio
    "/cap1.html",
    "/cap2.html",
    "/cap3.html",
    "/cap4.html",
    "/cap5.html",
    "/cap6.html",
    "/cap7.html",
    "/cap8.html",
    "/cap9.html",
    "/cap10.html",
    "/capAp.html",  # Apêndice A (Git)
]

# Páginas-raiz adicionais do site
EXTRA_ROOTS = [
    "/",                            # home
    "/artigos/artigos.html",        # índice de artigos didáticos
    "/praticas.html",               # roteiros práticos
    "/faq/testes-faq.html",
    "/faq/git-faq.html",
]

# Aceita somente URLs internas do domínio e ignora arquivos comuns não-HTML
HTML_OK = re.compile(r"^https://engsoftmoderna\.info(/.*)?$",
                     flags=re.IGNORECASE)

SKIP_EXTS = (".png", ".jpg", ".jpeg", ".svg", ".gif",
             ".pdf", ".zip", ".mp4", ".webm", ".ico")

# ---------- Utilidades ----------

def find_browser_executable() -> Optional[str]:
    """Tenta localizar Chrome/Edge no Windows (ou via PATH)."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in candidates:
        if pathlib.Path(p).exists():
            return p
    for name in ("chrome.exe", "msedge.exe", "google-chrome", "chromium"):
        path = shutil.which(name)
        if path:
            return path
    return None

def is_internal(url: str) -> bool:
    return bool(HTML_OK.match(url))

def normalize(href: str) -> str:
    """Absolutiza URL, remove fragmento/query, filtra domínio/extensões."""
    if not href:
        return ""
    href = href.strip()
    if href.startswith("#"):
        return ""
    absu = up.urljoin(BASE, href)
    u = up.urlparse(absu)
    # limpa fragmentos e query
    u = u._replace(fragment="", query="")
    absu = up.urlunparse(u)
    if not is_internal(absu):
        return ""
    if absu.lower().endswith(SKIP_EXTS):
        return ""
    return absu

def fetch_html(url: str) -> str:
    with ur.urlopen(url) as r:
        return r.read().decode("utf-8", errors="ignore")

def extract_links(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a"):
        href = normalize(a.get("href"))
        if href:
            links.append(href)
    return links

def crawl_all(start_urls: List[str]) -> List[str]:
    """BFS pelas páginas internas do domínio."""
    seen = OrderedDict()
    q = deque(start_urls)
    while q:
        url = q.popleft()
        if url in seen:
            continue
        try:
            html = fetch_html(url)
        except Exception:
            continue
        seen[url] = True
        for nxt in extract_links(html):
            if nxt not in seen:
                q.append(nxt)
    return list(seen.keys())

def url_path(url: str) -> str:
    return up.urlparse(url).path or "/"

def order_urls(all_urls: List[str]) -> List[str]:
    """Coloca capítulos na ordem, depois extras, depois artigos/FAQ e demais."""
    by_path = {url_path(u): u for u in all_urls}

    ordered: List[str] = []
    # 1) capítulos
    for p in CHAPTERS_IN_ORDER:
        if p in by_path:
            ordered.append(by_path[p])

    # 2) extras
    for p in EXTRA_ROOTS:
        if p in by_path and by_path[p] not in ordered:
            ordered.append(by_path[p])

    # 3) demais
    rest = [u for u in all_urls if u not in ordered]
    artigos = sorted([u for u in rest if "/artigos/" in u])
    faq = sorted([u for u in rest if "/faq/" in u])
    others = sorted([u for u in rest if "/artigos/" not in u and "/faq/" not in u])
    ordered.extend(artigos + faq + others)
    return ordered

# ---------- Renderização PDF ----------

async def print_to_pdf(urls: List[str]) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    exe = find_browser_executable()
    launch_args = [
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
    ]

    if exe:
        browser = await launch(args=launch_args, executablePath=exe)
    else:
        # Último recurso: permitir tentativa de download (pode falhar de novo).
        browser = await launch(args=launch_args)

    page = await browser.newPage()
    page.setDefaultNavigationTimeout(120_000)

    for idx, url in enumerate(urls, 1):
        safe_name = url_path(url).strip("/").replace("/", " - ") or "home"
        fname = os.path.join(OUT_DIR, f"{idx:04d} - {safe_name}.pdf")
        try:
            await page.goto(url, {"waitUntil": "networkidle2"})
            # Em geral o site é claro; força background e margens
            await page.pdf({
                "path": fname,
                "format": "A4",
                "printBackground": True,
                "margin": {"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
                "preferCSSPageSize": False
            })
            print(f"[OK] {fname}")
        except Exception as e:
            print(f"[ERRO] {url} -> {e}")

    await browser.close()

def merge_pdfs() -> None:
    writer = PdfWriter()
    parts = sorted(
        os.path.join(OUT_DIR, f)
        for f in os.listdir(OUT_DIR)
        if f.lower().endswith(".pdf")
    )
    added = 0
    for f in parts:
        try:
            r = PdfReader(f)
            for pg in r.pages:
                writer.add_page(pg)
                added += 1
        except Exception:
            continue
    with open(FINAL_PDF, "wb") as fp:
        writer.write(fp)
    print(f"\n>> PDF final gerado: {FINAL_PDF} (páginas mescladas: {added} | arquivos: {len(parts)})")

# ---------- Main ----------

def main() -> None:
    seeds = [up.urljoin(BASE, p) for p in CHAPTERS_IN_ORDER + EXTRA_ROOTS]
    all_urls = crawl_all(seeds)
    ordered = order_urls(all_urls)

    print("\n=== Mapa (primeiros 40) ===")
    for u in ordered[:40]:
        print(" -", u)
    print(f"... total coletado: {len(ordered)} URLs internas")

    # Python 3.13+: use asyncio.run
    asyncio.run(print_to_pdf(ordered))
    merge_pdfs()

if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("Use Python 3.9+")
        sys.exit(1)
    main()
