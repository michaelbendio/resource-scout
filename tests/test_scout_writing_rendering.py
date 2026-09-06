from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from resource_research_agent.resource_writing import compose_information, load_writing_guidance

ROOT = Path(__file__).resolve().parents[1]


class ScoutWritingRenderingTests(unittest.TestCase):
    def test_real_information_renderer_preserves_sections_bullets_and_escapes_source(self):
        template = (ROOT / 'resource_research_agent/scout_review_template.html').read_text()
        renderer = template[template.index('const INFORMATION_ADDITIONAL_LABEL'):template.index('function fitTextareaToText')]
        escape = template[template.index('function escapeHTML('):template.index('\n', template.index('function escapeHTML('))]
        cases = json.loads((ROOT / 'tests/fixtures/resource_writing/pilot_cases.json').read_text())['cases']
        guidance = load_writing_guidance()
        texts = [compose_information(case['sections'], guidance) for case in cases]
        texts.append('**Access**\n<script>alert("unsafe")</script>\n\n- José’s office · Mesa\n- https://example.org/apply\n- help@example.org')
        script = escape + '\n' + renderer + '\n' + '''
const assert = require('assert');
const inputs = JSON.parse(process.argv[1]);
const outputs = inputs.map(text => renderInformationHTML(text));
for(const output of outputs.slice(0, -1)) {
  const headings = ['Programs and Services', 'Eligibility Requirements', 'How to Best Connect', 'Access', 'Important Information to Know'];
  let previous = -1;
  for(const heading of headings) {
    const tag = `<strong>${heading}</strong>`;
    assert.strictEqual(output.split(tag).length - 1, 1);
    assert(output.includes(`<div class="information-line information-heading">${tag}</div>`));
    assert(output.indexOf(tag) > previous);
    previous = output.indexOf(tag);
  }
  assert(!output.includes('<strong>Scout Findings</strong>'));
}
assert(outputs[0].includes('jobs.mesaaz@expresspros.com'));
assert(outputs[0].includes('<ul>'));
const escaped = outputs.at(-1);
assert(!escaped.includes('<script>'));
assert(escaped.includes('&lt;script&gt;'));
assert(escaped.includes('José’s office · Mesa'));
assert(escaped.includes('href="https://example.org/apply"'));
assert(escaped.includes('help@example.org'));
'''
        subprocess.run(['node', '-e', script, json.dumps(texts, ensure_ascii=False)], check=True, capture_output=True, text=True)

    def test_approved_example_composition_is_exact_except_documented_email_placement(self):
        cases = json.loads((ROOT / 'tests/fixtures/resource_writing/pilot_cases.json').read_text())['cases']
        text = compose_information(cases[0]['sections'], load_writing_guidance())
        approved = (ROOT / 'docs/scout-writing-example.md').read_text().split('**Programs and Services**', 1)[1]
        expected = '**Programs and Services**' + approved
        # The document separates headings with a blank line; the package composer
        # uses a single newline and keeps the email in its supported text field.
        expected = expected.strip().replace('**\n\n', '**\n')
        actual = text.replace('\n\nEmail: jobs.mesaaz@expresspros.com', '')
        self.assertEqual(expected, actual)
