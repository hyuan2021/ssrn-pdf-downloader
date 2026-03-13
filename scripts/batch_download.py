#!/usr/bin/env python3
"""
Batch download SSRN papers from a JSON file.

For each paper: visits the abstract page, scrapes the abstract text,
downloads the PDF, and writes an updated JSON with abstract and pdf_path.

Usage:
    python batch_download.py <input_json> [--out-dir papers/] [--output results.json]
"""
import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import nodriver as uc


def safe_filename(title: str, url: str) -> str:
    m = re.search(r'abstract_id=(\d+)', url)
    abstract_id = m.group(1) if m else 'ssrn-paper'
    base = re.sub(r'[^a-zA-Z0-9]+', '-', (title or '').strip()).strip('-').lower()
    if not base:
        base = f'ssrn-{abstract_id}'
    base = base[:80].strip('-')
    return f'{base or f"ssrn-{abstract_id}"}.pdf'


JS_SCRAPE_ABSTRACT = """
JSON.stringify((() => {
    // Accept cookies if banner present
    var btn = document.querySelector('#onetrust-accept-btn-handler');
    if (btn) btn.click();

    var abs = document.querySelector('.abstract-text p')
               || document.querySelector('.abstract-text')
               || document.querySelector('#abstract');
    var abstractText = abs ? abs.innerText.trim() : '';

    // Remove leading "Abstract:" or "Abstract" if present
    abstractText = abstractText.replace(/^Abstract:?\\s*/i, '');

    var links = Array.from(document.querySelectorAll("a[href*='Delivery.cfm']")).map(a => a.href);

    return { abstract: abstractText, downloadLinks: links };
})())
"""


async def process_paper(page, paper: dict, out_dir: Path, download_dir: str) -> dict:
    """Visit abstract page, scrape abstract, download PDF. Returns updated paper dict."""
    url = paper['url']
    result = dict(paper)

    try:
        await page.get(url)

        # Wait for Cloudflare
        for _ in range(30):
            await asyncio.sleep(2)
            title = await page.evaluate('document.title')
            if title and 'moment' not in title.lower():
                break
        else:
            result['error'] = 'Cloudflare challenge did not resolve'
            return result

        await asyncio.sleep(3)

        # Scrape abstract and get download link
        r = await page.send(uc.cdp.runtime.evaluate(expression=JS_SCRAPE_ABSTRACT))
        data = json.loads(r[0].value)

        result['abstract'] = data.get('abstract', '')
        download_links = data.get('downloadLinks', [])

        if not download_links:
            result['error'] = 'No download link found'
            result['pdf_path'] = ''
            return result

        pdf_url = download_links[0]
        if isinstance(pdf_url, dict):
            pdf_url = pdf_url.get('value', pdf_url)

        # Clear temp download dir
        for f in os.listdir(download_dir):
            os.remove(os.path.join(download_dir, f))

        # Set download path and trigger download
        await page.send(uc.cdp.browser.set_download_behavior(
            behavior='allow',
            download_path=download_dir,
        ))
        await page.evaluate(f'window.location.href = "{pdf_url}"')

        # Wait for PDF
        pdf_src = None
        for _ in range(30):
            await asyncio.sleep(2)
            files = os.listdir(download_dir)
            pdf_files = [f for f in files if f.endswith('.pdf')]
            if pdf_files:
                pdf_src = Path(download_dir) / pdf_files[0]
                break

        if not pdf_src or not pdf_src.exists():
            result['error'] = 'PDF download timed out'
            result['pdf_path'] = ''
            return result

        filename = safe_filename(paper.get('title', ''), url)
        pdf_path = out_dir / filename

        # Avoid overwriting — append abstract_id if collision
        if pdf_path.exists():
            m = re.search(r'abstract_id=(\d+)', url)
            aid = m.group(1) if m else 'dup'
            pdf_path = out_dir / f'{pdf_path.stem}-{aid}.pdf'

        shutil.move(str(pdf_src), str(pdf_path))
        result['pdf_path'] = str(pdf_path.resolve())

    except Exception as e:
        result['error'] = str(e)
        result.setdefault('pdf_path', '')

    return result


async def batch_download(input_json: str, out_dir: str, output_json: str):
    with open(input_json) as f:
        data = json.load(f)

    # Support both {"papers": [...]} and plain [...]
    if isinstance(data, dict):
        papers = data.get('papers', [])
        envelope = data
    else:
        papers = data
        envelope = None

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    download_dir = tempfile.mkdtemp()
    browser = await uc.start(headless=False)

    try:
        # Open a blank page first, then reuse it
        page = await browser.get('about:blank')

        results = []
        total = len(papers)
        for i, paper in enumerate(papers, 1):
            print(f'[{i}/{total}] {paper.get("title", "Unknown")[:70]}...')
            result = await process_paper(page, paper, out_path, download_dir)

            if result.get('error'):
                print(f'         ERROR: {result["error"]}')
            else:
                print(f'         OK -> {result.get("pdf_path", "")}')
                if result.get('abstract'):
                    print(f'         Abstract: {result["abstract"][:80]}...')

            results.append(result)

            # Save progress after each paper
            _write_output(output_json, envelope, results)

    finally:
        shutil.rmtree(download_dir, ignore_errors=True)
        browser.stop()

    _write_output(output_json, envelope, results)
    print(f'\nDone. {len(results)} papers processed -> {output_json}')


def _write_output(output_json: str, envelope: dict | None, results: list):
    if envelope is not None:
        out = dict(envelope)
        out['papers'] = results
    else:
        out = results
    with open(output_json, 'w') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Batch download SSRN papers')
    parser.add_argument('input_json', help='Input JSON file with paper list')
    parser.add_argument('--out-dir', default='papers/',
                        help='Directory to save PDFs (default: papers/)')
    parser.add_argument('--output', default=None,
                        help='Output JSON file (default: <input>_downloaded.json)')
    args = parser.parse_args()

    if args.output is None:
        stem = Path(args.input_json).stem
        args.output = f'{stem}_downloaded.json'

    asyncio.run(batch_download(args.input_json, args.out_dir, args.output))


if __name__ == '__main__':
    main()
