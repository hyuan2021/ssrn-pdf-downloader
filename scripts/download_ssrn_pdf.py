#!/usr/bin/env python3
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import nodriver as uc


def abstract_url_from_input(url: str) -> str:
    if 'abstract_id=' in url:
        m = re.search(r'abstract_id=(\d+)', url)
        if m:
            return f'https://papers.ssrn.com/sol3/papers.cfm?abstract_id={m.group(1)}'
    if 'abstractid=' in url:
        m = re.search(r'abstractid=(\d+)', url)
        if m:
            return f'https://papers.ssrn.com/sol3/papers.cfm?abstract_id={m.group(1)}'
    m = re.search(r'/Delivery\.cfm/(\d+)\.pdf', url)
    if m:
        return f'https://papers.ssrn.com/sol3/papers.cfm?abstract_id={m.group(1)}'
    return url


def safe_filename(title: str, abstract_url: str) -> str:
    m = re.search(r'abstract_id=(\d+)', abstract_url)
    abstract_id = m.group(1) if m else 'ssrn-paper'
    base = re.sub(r'[^a-zA-Z0-9]+', '-', (title or '').strip()).strip('-').lower()
    if not base:
        base = f'ssrn-{abstract_id}'
    base = base[:80].strip('-')
    return f'{base or f"ssrn-{abstract_id}"}.pdf'


async def download_paper(paper_url: str, out_dir: Path) -> dict:
    browser = await uc.start(headless=False)
    download_dir = tempfile.mkdtemp()
    try:
        page = await browser.get(paper_url)

        # Wait for Cloudflare challenge to resolve
        for _ in range(30):
            await asyncio.sleep(2)
            title = await page.evaluate('document.title')
            if title and 'moment' not in title.lower():
                break
        else:
            raise RuntimeError('Cloudflare challenge did not resolve within 60 seconds')

        title = await page.evaluate('document.title') or 'SSRN Paper'

        # Find the primary download link
        links = await page.evaluate("""
            Array.from(document.querySelectorAll("a[href*='Delivery.cfm']"))
                .map(a => a.href)
        """)
        if not links:
            raise RuntimeError('Could not find SSRN download link on page')

        pdf_url = links[0]
        if isinstance(pdf_url, dict):
            pdf_url = pdf_url.get('value', pdf_url)

        # Set up CDP download to a temp directory
        await page.send(uc.cdp.browser.set_download_behavior(
            behavior='allow',
            download_path=download_dir,
        ))

        # Navigate to the PDF URL (browser has CF clearance cookies)
        await page.evaluate(f'window.location.href = "{pdf_url}"')

        # Wait for the PDF to finish downloading
        pdf_src = None
        for _ in range(30):
            await asyncio.sleep(2)
            files = os.listdir(download_dir)
            pdf_files = [f for f in files if f.endswith('.pdf')]
            if pdf_files:
                pdf_src = Path(download_dir) / pdf_files[0]
                break

        if not pdf_src or not pdf_src.exists():
            raise RuntimeError('PDF download did not complete within 60 seconds')

        filename = safe_filename(title, paper_url)
        pdf_path = out_dir / filename
        shutil.move(str(pdf_src), str(pdf_path))

        return {
            'ok': True,
            'paper_url': paper_url,
            'pdf_path': str(pdf_path.resolve()),
            'title': title,
            'filename': filename,
        }
    finally:
        shutil.rmtree(download_dir, ignore_errors=True)
        browser.stop()


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Usage: download_ssrn_pdf.py <url>"}, ensure_ascii=False))
        sys.exit(1)

    input_url = sys.argv[1]
    paper_url = abstract_url_from_input(input_url)
    out_dir = Path('papers')
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = asyncio.run(download_paper(paper_url, out_dir))
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            'ok': False,
            'paper_url': paper_url,
            'error': str(e),
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
