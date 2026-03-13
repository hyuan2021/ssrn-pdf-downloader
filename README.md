# SSRN PDF Downloader

A toolkit for downloading SSRN paper PDFs and browsing SSRN eJournal listings, bypassing Cloudflare protection using [nodriver](https://github.com/ultrafunkamsterdam/nodriver).

## What it does

SSRN blocks direct `curl`/`wget` downloads with Cloudflare challenges and 403 errors. This project provides two main capabilities:

1. **Download individual papers** — navigate to an SSRN abstract page, pass Cloudflare, and save the PDF locally.
2. **Batch download papers** — given a JSON list of papers, download all PDFs, scrape abstracts, and produce an enriched JSON with abstracts and file paths.
3. **Browse eJournal listings** — fetch recent papers (titles, authors, affiliations, dates, URLs) from any SSRN eJournal, with date filtering.

## Requirements

- Python 3.10+
- [nodriver](https://github.com/ultrafunkamsterdam/nodriver)
- Google Chrome / Chromium

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install nodriver
```

## Usage

### Download a paper PDF

```bash
.venv/bin/python scripts/download_ssrn_pdf.py 'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567'
```

Accepts SSRN abstract pages (`papers.cfm?abstract_id=...`) or direct PDF links (`Delivery.cfm/...pdf`). The PDF is saved to `papers/`.

Output (JSON):

```json
{
  "ok": true,
  "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567",
  "pdf_path": "/path/to/papers/some-paper-title.pdf",
  "title": "Some Paper Title",
  "filename": "some-paper-title.pdf"
}
```

### Batch download papers from a JSON list

```bash
.venv/bin/python scripts/batch_download.py papers.json --out-dir papers/ --output results.json
```

Takes a JSON file containing a list of papers (either `{"papers": [...]}` or a plain `[...]` array). For each paper it:

1. Visits the abstract page and scrapes the abstract text
2. Downloads the PDF
3. Records the full file path

Progress is saved after each paper so no work is lost if the process is interrupted.

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--out-dir` | `papers/` | Directory to save PDFs |
| `--output` | `<input>_downloaded.json` | Output JSON file |

Output adds `abstract` and `pdf_path` fields to each paper entry:

```json
{
  "title": "Paper Title",
  "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=...",
  "authors": ["Author One"],
  "affiliations": "University A",
  "abstract": "We study the effect of...",
  "pdf_path": "/absolute/path/to/papers/paper-title.pdf"
}
```

### Fetch recent papers from an eJournal

```bash
.venv/bin/python scripts/fetch_journal_papers.py
```

By default this fetches papers from the last 3 days of the **Capital Markets: Asset Pricing & Valuation eJournal**. Edit `JOURNAL_URL` in the script to target a different journal. See `ssrn_journals.md` for a full list of available journal URLs.

Output is saved to `journal_papers_recent.json` with the following fields per paper:

```json
{
  "title": "Paper Title",
  "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=...",
  "date": "12 Mar 2026",
  "authors": ["Author One", "Author Two"],
  "affiliations": "University A and University B"
}
```

## How it works

1. Launches a real browser session via nodriver to pass Cloudflare verification
2. Accepts cookie consent banners automatically
3. Extracts data from the rendered DOM (paper listings, download links, etc.)
4. For PDF downloads: triggers the browser download via CDP and captures the file

## File structure

```
ssrn-pdf-downloader/
├── README.md
├── LICENSE
├── SKILL.md                              # OpenClaw skill descriptor
├── skill.json                            # Skill metadata
├── ssrn_journals.md                      # Reference list of SSRN eJournal URLs
├── scripts/
│   ├── download_ssrn_pdf.py             # Download a single paper PDF
│   ├── batch_download.py               # Batch download + scrape abstracts
│   └── fetch_journal_papers.py          # Fetch recent papers from an eJournal
├── papers/                               # Downloaded PDFs (gitignored)
└── journal_papers_recent.json           # Latest journal fetch output
```

## License

MIT
