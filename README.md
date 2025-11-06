## Gera um único PDF com o conteúdo de Engenharia de Software Moderna

🧠 Como funciona (resumo técnico)

Crawler BFS coleta URLs internas a partir de sementes: capítulos e páginas-raiz (extras).
Normalização e filtros: remove #fragment/?query, ignora externos e arquivos não-HTML.
Ordenação: capítulos (ordem fixa) → extras → /artigos/ → /faq/ → demais.
Renderização: Pyppeteer lança Chrome/Edge local e “imprime” cada página em A4.
Mesclagem: pypdf concatena todos os PDFs parciais em um único arquivo.

⚠️ Uso educacional/pessoal. Para redistribuir o PDF, verifique a política dos autores/editora.

## ✨ Recursos

Varredura (crawl) apenas do domínio interno engsoftmoderna.info
Ordem canônica: cap0 → cap1..10 → capAp (Apêndice A)
Impressão headless de cada página e mesclagem em um único PDF
Compatível com Python 3.13
Pyppeteer usando Chrome/Edge local (evita download de Chromium)

## 📦 Estrutura do projeto
```.
├─ esm2pdf.py                # Script principal (Pyppeteer)
├─ requirements.txt          # Dependências de runtime
├─ requirements-test.txt     # Dependências de testes (pytest, reportlab)
├─ tests/                    # Suíte de testes (pytest + mocks)
│  ├─ conftest.py
│  ├─ test_normalize_and_filters.py
│  ├─ test_order_and_naming.py
│  ├─ test_merge_pdfs.py
│  └─ test_crawl_and_render_with_mocks.py
└─ esm_pdf_pages/            # (gerada) PDFs individuais por página
```

## ✅ Pré-requisitos

Windows 10/11 (funciona em Linux/macOS com ajustes)
Python 3.13+
Google Chrome ou Microsoft Edge instalado

requirements.txt:

pyppeteer==1.0.2
pypdf==5.0.1
beautifulsoup4==4.12.3
urllib3==2.2.3

# Dependências
pip install -r requirements.txt

## ▶️ Uso
python esm2pdf.py

## Saída esperada:

Pasta esm_pdf_pages/ contendo os PDFs parciais (um por página)
Arquivo final Engenharia_de_Software_Moderna_site_completo.pdf na raiz

## 🧪 Testes

Instale dependências de teste e rode a suíte:

pip install -r requirements-test.txt
pytest -q --cov=esm2pdf --cov-report=term-missing

