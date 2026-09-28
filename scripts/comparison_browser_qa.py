#!/usr/bin/env python3
"""Browser regression checks for exact text, safe markup and visible differences."""
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page()
    page.set_content('<main></main>')
    page.add_script_tag(path=str(root / 'web/comparison.js'))
    for name in ('improvements', 'classifications', 'maintenance'):
        page.evaluate('(s)=>{new Function(s)}', (root / f'web/{name}.js').read_text())
    page.evaluate('''() => {
      function check(a,b,removed,added) {
        const d=highlightComparison(a,b);
        const old=document.createElement('div'),fresh=document.createElement('div');
        old.innerHTML=d.before;fresh.innerHTML=d.after;
        const source=document.createElement('div');source.innerHTML=a;
        if(old.textContent!==source.textContent)throw Error('Changed original text');
        source.innerHTML=b;if(fresh.textContent!==source.textContent)throw Error('Changed proposed text');
        const marked=e=>[...e.querySelectorAll('strong.comparison-change')].map(n=>n.textContent).join('');
        if(marked(old)!==removed || marked(fresh)!==added)throw Error(JSON.stringify({d,removed,added}));
        document.querySelector('main').innerHTML='<h2>Current</h2>'+d.before+'<h2>Proposed</h2>'+d.after;
        return {old,fresh};
      }
      check('Call Monday at 9.','Call Tuesday at 10.','Monday9','Tuesday10');
      check('Keep all details.','Keep all details.','','');
      check('Help for all adults.','Help for adults.','all ','');
      check('Food','Food and clothing','',' and clothing');
      check('Line one\\nLine two','Line one\\nLine three','two','three');
      const {fresh}=check('<p>Call <a href="https://example.org">the office</a> Monday.</p>',
        '<p>Call <a href="https://example.org">the office</a> Tuesday.</p>','Monday','Tuesday');
      if(fresh.querySelector('a').getAttribute('href')!=='https://example.org')throw Error('Lost link');
      check('&lt;script&gt;old&lt;/script&gt;','&lt;script&gt;new&lt;/script&gt;','old','new');
      if(document.querySelector('main script'))throw Error('Unescaped source');
      check('Call Monday.','Call Tuesday.','Monday','Tuesday');
    }''')
    for width in (390, 768, 1200):
        page.set_viewport_size({'width': width, 'height': 900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.emulate_media(media='print')
    assert page.locator('strong.comparison-change').count() == 2
    assert page.locator('del').is_visible()
    browser.close()
print('Comparison browser QA passed: exact text, multiple edits, additions, removals, links, escaping, print and responsive display.')
