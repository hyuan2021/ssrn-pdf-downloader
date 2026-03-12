---
name: ssrn-pdf-downloader
description: Download SSRN paper PDFs that are protected by Cloudflare and SSRN's browser-based download flow. Use when a user shares an SSRN paper page or Delivery.cfm link and wants the actual PDF saved locally for reading, summarizing, or forwarding. Especially useful when direct curl/web_fetch gets blocked with 403 or Cloudflare verification.
---

# SSRN PDF Downloader

Download SSRN PDFs by simulating the real browser download flow.

## Use this skill

Use this when:
- the URL is an SSRN abstract page like `papers.cfm?abstract_id=...`
- the URL is an SSRN PDF link like `Delivery.cfm/...pdf?...`
- direct download fails with Cloudflare / 403 / redirect back to abstract page

## Workflow

1. Normalize the input to an SSRN abstract page when possible.
2. Run the downloader script with `exec`.
3. Save the PDF into `papers/`.
4. If the user asked for a summary, then use the `pdf` tool on the saved file.

## Command

Always run from the agent workspace and prepend `/data/.local/bin` to `PATH`.

```bash
export PATH=/data/.local/bin:$PATH
python3 skills/ssrn-pdf-downloader/scripts/download_ssrn_pdf.py '<URL>'
```

## Output expectations

The script prints JSON with:
- `ok`
- `paper_url`
- `pdf_path`
- `title`
- `filename`

If it fails, it prints JSON with `ok: false` and an `error` field.

## Notes

- Prefer this skill over raw `curl` for SSRN.
- The script uses the installed Scrapling / Patchright stack and clicks the actual SSRN download button after passing Cloudflare.
- If the user only gives a Delivery link, the script will try to derive the abstract page first.
- After download, summarize from the saved PDF, not from the SSRN landing page.
