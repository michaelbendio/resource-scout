const state = { seeds: [] };

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}

function showImport(summary) {
  if (!summary) return;
  document.querySelector('#status-pill').textContent = `${summary.sourceName} connected`;
  document.querySelector('#status-pill').classList.add('ready');
  document.querySelector('#resource-count').textContent = summary.resourceCount;
  document.querySelector('#housing-count').textContent = summary.targetResourceCount;
  document.querySelector('#multi-count').textContent = summary.multiCategoryTargetResourceCount;
  document.querySelector('#schema-version').textContent = summary.schema.schemaVersion || 'unversioned';
  document.querySelector('#metrics').hidden = false;
  document.querySelector('#workspace').hidden = false;
}

function renderSeeds(filter = '') {
  const list = document.querySelector('#seed-list');
  const wanted = filter.trim().toLowerCase();
  const seeds = state.seeds.filter(seed => seed.name.toLowerCase().includes(wanted));
  list.replaceChildren(...seeds.map(seed => {
    const item = document.createElement('div');
    item.className = 'seed';
    item.tabIndex = 0;
    const categories = seed.fullRecord.categories || [];
    item.innerHTML = `<strong></strong><small></small>`;
    item.querySelector('strong').textContent = seed.name;
    item.querySelector('small').textContent = `${categories.length} categor${categories.length === 1 ? 'y' : 'ies'} · existing`;
    const open = () => openSeed(seed);
    item.addEventListener('click', open);
    item.addEventListener('keydown', event => { if (event.key === 'Enter') open(); });
    return item;
  }));
}

function asText(value) {
  if (value == null) return '';
  if (Array.isArray(value)) return value.map(asText).filter(Boolean).join('\n');
  if (typeof value === 'object') return value.name || value.label || value.value || JSON.stringify(value);
  return String(value).trim();
}

function safeHref(value) {
  const raw = value.trim();
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(raw)) return `mailto:${raw}`;
  const candidate = /^[a-z][a-z0-9+.-]*:/i.test(raw) ? raw : `https://${raw}`;
  try {
    const url = new URL(candidate);
    return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

function appendInlineMarkdown(target, text) {
  const pattern = /(\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|__([^_]+)__|https?:\/\/[^\s<]+|\b[^\s@]+@[^\s@]+\.[^\s@]+\b)/g;
  let cursor = 0;
  for (const match of text.matchAll(pattern)) {
    target.append(document.createTextNode(text.slice(cursor, match.index)));
    if (match[2] && match[3]) {
      const href = safeHref(match[3]);
      if (href) {
        const link = document.createElement('a');
        link.href = href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = match[2];
        target.append(link);
      } else target.append(document.createTextNode(match[0]));
    } else if (match[4] || match[5]) {
      const strong = document.createElement('strong');
      strong.textContent = match[4] || match[5];
      target.append(strong);
    } else {
      const visible = match[0].replace(/[.,;:!?]+$/, '');
      const trailing = match[0].slice(visible.length);
      const href = safeHref(visible);
      if (href) {
        const link = document.createElement('a');
        link.href = href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = visible;
        target.append(link, document.createTextNode(trailing));
      } else target.append(document.createTextNode(match[0]));
    }
    cursor = match.index + match[0].length;
  }
  target.append(document.createTextNode(text.slice(cursor)));
}

function renderMarkdown(target, source) {
  target.replaceChildren();
  const lines = String(source || '').replace(/\r\n?/g, '\n').split('\n');
  let paragraph = [];
  let list = null;
  let listType = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const element = document.createElement('p');
    paragraph.forEach((line, index) => {
      if (index) element.append(document.createElement('br'));
      appendInlineMarkdown(element, line);
    });
    target.append(element);
    paragraph = [];
  };
  const closeList = () => { list = null; listType = null; };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      flushParagraph();
      closeList();
      continue;
    }
    if (/^\s*---+\s*$/.test(line)) {
      flushParagraph(); closeList(); target.append(document.createElement('hr')); continue;
    }
    const markdownHeading = line.match(/^\s*(#{1,4})\s+(.+)$/);
    const boldLine = line.match(/^\s*\*\*(.+?)\s*\*\*\s*$/);
    const boldHeading = boldLine && boldLine[1].trim().length <= 80 ? boldLine : null;
    if (markdownHeading || boldHeading) {
      flushParagraph(); closeList();
      const heading = document.createElement(markdownHeading ? `h${Math.min(markdownHeading[1].length + 2, 5)}` : 'h4');
      appendInlineMarkdown(heading, markdownHeading ? markdownHeading[2] : boldHeading[1]);
      target.append(heading);
      continue;
    }
    const bullet = line.match(/^\s*[-*+]\s+(.+)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (bullet || numbered) {
      flushParagraph();
      const wantedType = bullet ? 'ul' : 'ol';
      if (!list || listType !== wantedType) {
        list = document.createElement(wantedType);
        listType = wantedType;
        target.append(list);
      }
      const item = document.createElement('li');
      appendInlineMarkdown(item, (bullet || numbered)[1]);
      list.append(item);
      continue;
    }
    closeList();
    paragraph.push(line.trim());
  }
  flushParagraph();
}

function appendLinkifiedValue(target, value) {
  const text = asText(value);
  const segments = text.split(/\s*;\s*/).filter(Boolean);
  segments.forEach((segment, index) => {
    if (index) target.append(document.createElement('br'));
    const email = segment.match(/[^\s@]+@[^\s@]+\.[^\s@]+/);
    const candidate = email?.[0] || segment.match(/(?:https?:\/\/|www\.)[^\s,)]+|\b[a-z0-9.-]+\.[a-z]{2,}(?:\/[^\s,)]*)?/i)?.[0];
    const href = candidate ? safeHref(candidate) : null;
    if (!candidate || !href) {
      target.append(document.createTextNode(segment));
      return;
    }
    const start = segment.indexOf(candidate);
    target.append(document.createTextNode(segment.slice(0, start)));
    const link = document.createElement('a');
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = candidate;
    target.append(link, document.createTextNode(segment.slice(start + candidate.length)));
  });
}

function addContact(label, value, linkify = false) {
  const text = asText(value);
  if (!text) return;
  const wrapper = document.createElement('div');
  wrapper.className = 'contact-item';
  const term = document.createElement('dt');
  term.textContent = label;
  const detail = document.createElement('dd');
  if (linkify) appendLinkifiedValue(detail, text);
  else detail.textContent = text;
  wrapper.append(term, detail);
  document.querySelector('#record-contact').append(wrapper);
}

function readableCategory(category) {
  const raw = asText(category);
  return raw.split(/[-_]/).map(word => word.toUpperCase() === 'ID' ? 'ID' : word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function openSeed(seed) {
  const record = seed.fullRecord;
  document.querySelector('#record-name').textContent = seed.name;

  const categories = document.querySelector('#record-categories');
  categories.replaceChildren(...(seed.categories || record.categories || []).map(category => {
    const chip = document.createElement('span');
    chip.textContent = category.label || readableCategory(category.id || category);
    return chip;
  }));

  const contact = document.querySelector('#record-contact');
  contact.replaceChildren();
  addContact('Phone', record.phone);
  addContact('Address', record.address);
  addContact('Website or email', record.website || record.url, true);
  addContact('Hours', record.hours);

  const description = asText(record.description);
  document.querySelector('#record-description').textContent = description;
  document.querySelector('#record-description-section').hidden = !description;

  const information = asText(record.informationText || record.information || record.details);
  renderMarkdown(document.querySelector('#record-information'), information);
  document.querySelector('#record-information-section').hidden = !information;

  const attachmentList = document.querySelector('#record-attachments');
  const attachments = seed.attachments || [];
  attachmentList.replaceChildren(...attachments.map(attachment => {
    const item = attachment.available ? document.createElement('a') : document.createElement('div');
    item.className = `attachment ${attachment.available ? '' : 'unavailable'}`;
    if (attachment.available) {
      const parameters = new URLSearchParams({
        importId: seed.importId, resourceId: seed.resourceId, path: attachment.path,
      });
      item.href = `/api/seed-asset?${parameters}`;
      item.target = '_blank';
      item.rel = 'noopener noreferrer';
    }
    const name = document.createElement('strong');
    name.textContent = attachment.name;
    const detail = document.createElement('small');
    detail.textContent = attachment.available ? (formatBytes(attachment.bytes) || 'Stored package attachment') : 'Attachment reference only';
    item.append(name, detail);
    return item;
  }));
  document.querySelector('#record-attachments-section').hidden = !attachments.length;
  document.querySelector('#record-attachment-note').hidden = !attachments.some(attachment => !attachment.available);

  const metadata = document.querySelector('#record-metadata');
  metadata.replaceChildren();
  const metadataValues = [
    ['Resource ID', seed.resourceId],
    ['Verified', record.verifiedOn],
    ['Last modified', record.lastModified ? new Date(record.lastModified).toLocaleDateString() : ''],
  ];
  for (const [label, value] of metadataValues) {
    if (!value) continue;
    const item = document.createElement('span');
    const strong = document.createElement('strong');
    strong.textContent = `${label}: `;
    item.append(strong, document.createTextNode(value));
    metadata.append(item);
  }

  document.querySelector('#record-json').textContent = JSON.stringify(record, null, 2);
  document.querySelector('.raw-record').open = false;
  const dialog = document.querySelector('#record-dialog');
  dialog.showModal();
  dialog.scrollTop = 0;
}

async function refresh() {
  const status = await request('/api/status');
  if (!status.latestImport) return;
  showImport(status.latestImport);
  const result = await request('/api/seeds');
  state.seeds = result.seeds;
  renderSeeds();
}

document.querySelector('#package-input').addEventListener('change', event => {
  document.querySelector('#file-label').textContent = event.target.files[0]?.name || 'Choose resource-package.zip';
});

document.querySelector('#import-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button');
  const message = document.querySelector('#import-message');
  button.disabled = true;
  message.className = 'message';
  message.textContent = 'Reading the package and building the known-resource index…';
  try {
    const result = await request('/api/import', { method: 'POST', body: new FormData(form) });
    showImport(result.import);
    const seeds = await request('/api/seeds');
    state.seeds = seeds.seeds;
    renderSeeds();
    message.textContent = `Imported ${result.import.targetResourceCount} Housing resources. The source ZIP was not changed.`;
  } catch (error) {
    message.className = 'message error';
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

document.querySelector('#seed-filter').addEventListener('input', event => renderSeeds(event.target.value));
document.querySelector('#close-dialog').addEventListener('click', () => document.querySelector('#record-dialog').close());

document.querySelector('#check-form').addEventListener('submit', async event => {
  event.preventDefault();
  const candidate = {
    name: document.querySelector('#candidate-name').value,
    website: document.querySelector('#candidate-website').value,
    address: document.querySelector('#candidate-address').value,
  };
  const target = document.querySelector('#match-results');
  target.textContent = 'Checking…';
  try {
    const result = await request('/api/duplicate-check', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate }),
    });
    if (!result.matches.length) {
      target.textContent = 'No credible match in the imported package.';
      return;
    }
    target.replaceChildren(...result.matches.map(match => {
      const item = document.createElement('div');
      item.className = `match ${match.classification === 'already-known' ? 'exact' : ''}`;
      const heading = document.createElement('strong');
      heading.textContent = match.name;
      const detail = document.createElement('span');
      detail.textContent = `${match.classification === 'already-known' ? 'Already known' : 'Possible duplicate'} · ${Math.round(match.score * 100)}% signal`;
      item.append(heading, detail);
      return item;
    }));
  } catch (error) { target.textContent = error.message; }
});

refresh().catch(error => { document.querySelector('#import-message').textContent = error.message; });
