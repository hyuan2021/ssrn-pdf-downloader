#!/usr/bin/env python3
"""Fetch recent papers from an SSRN eJournal page using nodriver."""
import asyncio
import json
from datetime import datetime, timedelta
import nodriver as uc

JOURNAL_URL = "https://papers.ssrn.com/sol3/JELJOUR_Results.cfm?form_name=journalBrowse&journal_id=1508951"

JS_EXTRACT = """
JSON.stringify((() => {
    var papers = [];
    var paperDivs = document.querySelectorAll('div.paper');
    for (var i = 0; i < paperDivs.length; i++) {
        var p = paperDivs[i];
        var titleEl = p.querySelector('.title a');
        var statsEl = p.querySelector('.stats');
        var authorsEl = p.querySelector('.authors');
        var affilEl = p.querySelector('.affiliations');

        var title = titleEl ? titleEl.textContent.trim() : '';
        var url = titleEl ? titleEl.href : '';

        // Extract date from stats like "Posted 12 Mar 2026"
        var date = '';
        if (statsEl) {
            var m = statsEl.textContent.match(/Posted\\s+(\\d{1,2}\\s+\\w+\\s+\\d{4})/);
            if (m) date = m[1];
        }

        // Extract authors
        var authors = [];
        if (authorsEl) {
            var authorLinks = authorsEl.querySelectorAll('a');
            for (var j = 0; j < authorLinks.length; j++) {
                authors.push(authorLinks[j].textContent.trim());
            }
        }

        var affiliations = affilEl ? affilEl.textContent.trim() : '';

        papers.push({
            title: title,
            url: url,
            date: date,
            authors: authors,
            affiliations: affiliations
        });
    }
    return papers;
})())
"""

def parse_date(date_str):
    """Parse date like '12 Mar 2026'."""
    try:
        return datetime.strptime(date_str, '%d %b %Y')
    except ValueError:
        return None

async def main():
    browser = await uc.start(headless=False)
    page = await browser.get(JOURNAL_URL)

    # Wait for Cloudflare challenge
    for _ in range(30):
        await asyncio.sleep(2)
        title = await page.evaluate('document.title')
        if title and 'moment' not in title.lower():
            break
    else:
        print("Cloudflare challenge did not resolve")
        browser.stop()
        return

    print(f"Page loaded: {title}")
    await asyncio.sleep(3)

    # Accept cookies
    await page.evaluate("""
        (() => {
            var btn = document.querySelector('#onetrust-accept-btn-handler');
            if (btn) { btn.click(); return 'clicked'; }
            var buttons = document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {
                var t = buttons[i].textContent.toLowerCase();
                if (t.includes('accept all') || t.includes('accept cookies')) {
                    buttons[i].click(); return 'clicked';
                }
            }
            return 'no cookie banner';
        })()
    """)
    await asyncio.sleep(3)

    # Extract papers
    r = await page.send(uc.cdp.runtime.evaluate(expression=JS_EXTRACT))
    papers = json.loads(r[0].value)

    # Filter for last 3 days
    cutoff = datetime.now() - timedelta(days=3)
    recent = []
    for p in papers:
        d = parse_date(p['date'])
        if d and d >= cutoff:
            recent.append(p)

    print(f"\nTotal papers on page: {len(papers)}")
    print(f"Papers from last 3 days (since {cutoff.strftime('%d %b %Y')}): {len(recent)}")
    print("=" * 80)

    for i, p in enumerate(recent, 1):
        print(f"\n{i}. {p['title']}")
        print(f"   Authors: {', '.join(p['authors'])}")
        print(f"   Date:    {p['date']}")
        print(f"   URL:     {p['url']}")

    with open('journal_papers_recent.json', 'w') as f:
        json.dump(recent, f, indent=2, ensure_ascii=False)
    print(f'\nSaved {len(recent)} papers to journal_papers_recent.json')

    browser.stop()

asyncio.run(main())
