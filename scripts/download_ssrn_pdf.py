#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scrapling.fetchers import StealthySession


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


def click_accept_if_present(page):
    selectors = [
        '#onetrust-accept-btn-handler',
        'button:has-text("Accept")',
        'button:has-text("I Accept")',
        'button:has-text("Allow All")',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count():
                loc.first.click(timeout=3000)
                return sel
        except Exception:
            pass
    return None


def remove_overlays(page):
    page.evaluate(
        """
        () => {
          for (const sel of ['#onetrust-consent-sdk', '.onetrust-pc-dark-filter', '.ot-sdk-container']) {
            for (const el of document.querySelectorAll(sel)) el.remove();
          }
        }
        """
    )


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Usage: download_ssrn_pdf.py <url>"}, ensure_ascii=False))
        sys.exit(1)

    input_url = sys.argv[1]
    paper_url = abstract_url_from_input(input_url)
    out_dir = Path('papers')
    out_dir.mkdir(parents=True, exist_ok=True)

    session = StealthySession(headless=True)
    session.start()

    try:
        session.fetch(paper_url, solve_cloudflare=True)
        page = session.context.new_page()
        page.goto(paper_url, wait_until='domcontentloaded', timeout=60000)
        click_accept_if_present(page)
        remove_overlays(page)
        page.wait_for_timeout(1000)

        title = page.title() or 'SSRN Paper'
        primary = page.locator("a.button-link.primary[href*='Delivery.cfm']")
        if primary.count() == 0:
            raise RuntimeError('Could not find SSRN download button on page')

        with page.expect_download(timeout=45000) as dl_info:
            primary.first.click(force=True)
        download = dl_info.value

        filename = download.suggested_filename or safe_filename(title, paper_url)
        if not filename.lower().endswith('.pdf'):
            filename = safe_filename(title, paper_url)
        pdf_path = out_dir / filename
        download.save_as(str(pdf_path))

        print(json.dumps({
            'ok': True,
            'paper_url': paper_url,
            'pdf_path': str(pdf_path.resolve()),
            'title': title,
            'filename': filename,
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            'ok': False,
            'paper_url': paper_url,
            'error': str(e),
        }, ensure_ascii=False))
        sys.exit(1)
    finally:
        try:
            session.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
