#!/usr/bin/env python3
"""Copy shared question UI/merge code from the common app into Scout's template.

Scout retains its specialized curation selection and compact saved-state logic.
The question implementation and styling have one editable source in the common
application. This command updates only the marked shared sections.
"""
import argparse
import hashlib
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('common_app',type=Path)
args=parser.parse_args()
module=(args.common_app/'src/js/100f-admin-open-questions.js').read_text()
styles=(args.common_app/'src/styles.css').read_text()
css=re.search(r'/\* Open questions are administrative handoff, not resource verification\. \*/[\s\S]*?#res_open_questions textarea\s*\{[^}]*\}',styles).group(0)
template=ROOT/'resource_research_agent/scout_review_template.html'
document=template.read_text()

def shared(text,start,end,content,anchor):
    block=start+'\n'+content.rstrip()+'\n'+end+'\n'
    if start in text:
        text,count=re.subn(re.escape(start)+r'[\s\S]*?'+re.escape(end)+r'\n?',lambda _:block,text)
        if count!=1:raise SystemExit('Shared source marker is ambiguous')
        return text
    if text.count(anchor)!=1:raise SystemExit('Shared source insertion point is ambiguous')
    return text.replace(anchor,block+'\n'+anchor)

sha=hashlib.sha256(module.encode()).hexdigest()
document=shared(document,'// BEGIN SHARED CURATOR QUESTIONS','// END SHARED CURATOR QUESTIONS',
    '// Source: common application src/js/100f-admin-open-questions.js\n// SHA256: '+sha+'\n'+module,
    '// Source: src/js/110-shortcuts.js')
document=shared(document,'/* BEGIN SHARED CURATOR QUESTION STYLES */','/* END SHARED CURATOR QUESTION STYLES */',css,'</style>')
template.write_text(document)
print('Shared curator question code synchronized.')
