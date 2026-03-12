# SSRN PDF Downloader

An [OpenClaw](https://openclaw.ai) agent skill for downloading SSRN paper PDFs that are protected by Cloudflare and SSRN's browser-based download flow.

## What it does

SSRN blocks direct `curl`/`wget` downloads with Cloudflare challenges and 403 errors. This skill bypasses that by simulating a real browser session — it navigates to the abstract page, dismisses cookie banners, clicks the actual download button, and saves the PDF locally.

## When to use it

- The URL is an SSRN abstract page: `papers.cfm?abstract_id=...`
- The URL is a direct PDF link: `Delivery.cfm/...pdf?...`
- Direct download fails with Cloudflare verification or a 403

## Requirements

- [OpenClaw](https://openclaw.ai) with the [Scrapling](https://github.com/D4Vinci/Scrapling) stack installed (`scrapling`, `patchright`)
- Python 3.9+

## Usage

Run from your agent workspace:

```bash
export PATH=/data/.local/bin:$PATH
python3 skills/ssrn-pdf-downloader/scripts/download_ssrn_pdf.py 'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567'
```

### Output

On success, the script prints JSON and saves the PDF to `papers/`:

```json
{
  "ok": true,
  "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567",
  "pdf_path": "/path/to/workspace/papers/some-paper-title.pdf",
  "title": "Some Paper Title",
  "filename": "some-paper-title.pdf"
}
```

On failure:

```json
{
  "ok": false,
  "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567",
  "error": "Could not find SSRN download button on page"
}
```

## How it works

1. Normalizes the input URL to an SSRN abstract page
2. Opens a stealth browser session via Scrapling/Patchright to pass Cloudflare
3. Dismisses cookie consent overlays
4. Locates and clicks the primary download button
5. Captures the browser download and saves the PDF

## File structure

```
ssrn-pdf-downloader/
├── SKILL.md                          # OpenClaw skill descriptor
├── skill.json                        # Skill metadata
├── scripts/
│   └── download_ssrn_pdf.py         # Main downloader script
└── LICENSE
```

## License

MIT
