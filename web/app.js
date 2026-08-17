const state = { seeds: [], runs: [], discoveries: [], lessons: [], agent: null, currentCandidate: null, pollTimer: null };

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
  document.querySelector('#research-panel').hidden = false;
  document.querySelector('#research-results').hidden = false;
}

function showAgent(agent) {
  state.agent = agent;
  const card = document.querySelector('#agent-state');
  card.classList.toggle('ready', Boolean(agent?.ready));
  card.classList.toggle('attention', Boolean(agent?.installed && !agent?.ready));
  document.querySelector('#agent-state-title').textContent = agent?.ready ? 'Hermes ready' : agent?.installed ? 'Hermes needs setup' : 'Hermes not installed';
  document.querySelector('#agent-state-detail').textContent = agent?.version || agent?.message || '';
  document.querySelector('#agent-setup').hidden = !agent?.installed || agent?.ready;
  document.querySelector('#start-research').disabled = !agent?.ready;
  document.querySelector('#copy-setup').dataset.command = agent?.setupCommand || 'hermes setup';
  const settings = agent?.settings || {};
  document.querySelector('#agent-adapter').value = settings.adapter || 'hermes';
  document.querySelector('#agent-profile').value = settings.profile || '';
  document.querySelector('#agent-provider').value = settings.provider || '';
  document.querySelector('#agent-model').value = settings.model || '';
  document.querySelector('#agent-command').value = settings.command || '';
  document.querySelector('#agent-timeout').value = settings.timeoutSeconds || 900;
}

function renderSeedOptions() {
  const select = document.querySelector('#research-seed');
  const current = select.value;
  const broad = document.createElement('option');
  broad.value = '';
  broad.textContent = 'Research Housing broadly';
  select.replaceChildren(broad, ...state.seeds.map(seed => {
    const option = document.createElement('option');
    option.value = seed.resourceId;
    option.textContent = `Branch from ${seed.name}`;
    return option;
  }));
  if ([...select.options].some(option => option.value === current)) select.value = current;
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
  renderSeedOptions();
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

function friendlyStatus(value) {
  return String(value || '').replaceAll('-', ' ');
}

function formatWhen(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function emptyState(text) {
  const element = document.createElement('div');
  element.className = 'empty-state';
  element.textContent = text;
  return element;
}

function renderRuns() {
  const target = document.querySelector('#run-list');
  if (!state.runs.length) {
    target.replaceChildren(emptyState('No research runs yet.'));
    return;
  }
  target.replaceChildren(...state.runs.map(run => {
    const item = document.createElement('div');
    item.className = 'run';
    const head = document.createElement('div');
    head.className = 'run-head';
    const title = document.createElement('strong');
    title.textContent = run.seedResourceId
      ? `Seeded research · ${state.seeds.find(seed => seed.resourceId === run.seedResourceId)?.name || run.seedResourceId}`
      : 'Broad Housing research';
    const status = document.createElement('span');
    status.className = `run-status ${run.status}`;
    status.textContent = friendlyStatus(run.status);
    head.append(title, status);
    const time = document.createElement('small');
    time.textContent = `${formatWhen(run.createdAt)} · ${run.adapter}`;
    item.append(head, time);
    if (run.result?.summary) {
      const summary = document.createElement('p');
      summary.className = 'run-summary';
      summary.textContent = run.result.summary;
      item.append(summary);
    }
    if (run.error) {
      const error = document.createElement('div');
      error.className = 'run-error';
      error.textContent = run.error;
      item.append(error);
    }
    return item;
  }));
}

function candidateDescription(discovery) {
  const candidate = discovery.candidate || {};
  return asText(candidate.housingNeed || candidate.description || candidate.resourceType || 'Awaiting review');
}

function renderCandidates() {
  const target = document.querySelector('#candidate-list');
  document.querySelector('#candidate-count').textContent = state.discoveries.length;
  if (!state.discoveries.length) {
    target.replaceChildren(emptyState('Hermes candidates will appear here after a research run.'));
    return;
  }
  target.replaceChildren(...state.discoveries.map(discovery => {
    const item = document.createElement('div');
    item.className = 'candidate';
    item.tabIndex = 0;
    const head = document.createElement('div');
    head.className = 'candidate-head';
    const name = document.createElement('strong');
    name.textContent = discovery.name;
    const status = document.createElement('span');
    status.className = `candidate-status ${discovery.status}`;
    status.textContent = friendlyStatus(discovery.status);
    head.append(name, status);
    const description = document.createElement('p');
    description.textContent = candidateDescription(discovery);
    item.append(head, description);
    if (discovery.match) {
      const match = document.createElement('p');
      match.className = 'candidate-match';
      match.textContent = `Known-resource signal: ${Math.round(discovery.match.score * 100)}%`;
      item.append(match);
    }
    const open = () => openCandidate(discovery);
    item.addEventListener('click', open);
    item.addEventListener('keydown', event => { if (event.key === 'Enter') open(); });
    return item;
  }));
}

function addCandidateFact(target, label, value, linkify = false) {
  const text = asText(value);
  if (!text) return;
  const item = document.createElement('div');
  item.className = 'candidate-fact';
  const heading = document.createElement('strong');
  heading.textContent = label;
  const content = document.createElement('div');
  if (linkify) appendLinkifiedValue(content, text);
  else content.textContent = text;
  item.append(heading, content);
  target.append(item);
}

function addCandidateSection(target, title, value) {
  const values = Array.isArray(value) ? value.map(asText).filter(Boolean) : [asText(value)].filter(Boolean);
  if (!values.length) return;
  const section = document.createElement('section');
  section.className = 'candidate-section';
  const heading = document.createElement('h3');
  heading.textContent = title;
  section.append(heading);
  if (Array.isArray(value)) {
    const list = document.createElement('ul');
    for (const entry of values) {
      const item = document.createElement('li');
      item.textContent = entry;
      list.append(item);
    }
    section.append(list);
  } else {
    const paragraph = document.createElement('p');
    paragraph.textContent = values[0];
    section.append(paragraph);
  }
  target.append(section);
}

function renderCandidateProfile(discovery) {
  const candidate = discovery.candidate || {};
  const profile = document.createElement('div');
  profile.className = 'candidate-profile';
  const summaryText = asText(candidate.description || candidate.housingNeed);
  if (summaryText) {
    const summary = document.createElement('div');
    summary.className = 'candidate-summary';
    summary.textContent = summaryText;
    profile.append(summary);
  }
  const facts = document.createElement('div');
  facts.className = 'candidate-facts';
  addCandidateFact(facts, 'Organization', candidate.organization);
  addCandidateFact(facts, 'Program', candidate.program);
  addCandidateFact(facts, 'Type', candidate.resourceType);
  addCandidateFact(facts, 'Area served', candidate.geography);
  addCandidateFact(facts, 'Access timeline', candidate.accessTimeline);
  addCandidateFact(facts, 'Phone', candidate.phone);
  addCandidateFact(facts, 'Address', candidate.address);
  addCandidateFact(facts, 'Website', candidate.website || candidate.url, true);
  if (facts.children.length) profile.append(facts);
  addCandidateSection(profile, 'Housing need', candidate.housingNeed);
  addCandidateSection(profile, 'Eligibility', candidate.eligibility);
  addCandidateSection(profile, 'Barriers and restrictions', candidate.barriers);
  const availability = candidate.availability;
  if (availability) addCandidateSection(profile, 'Availability', typeof availability === 'object'
    ? [availability.status, availability.asOf ? `As of ${availability.asOf}` : '', availability.evidence].filter(Boolean)
    : availability);
  addCandidateSection(profile, 'Pet policy', candidate.petPolicy);
  const experience = candidate.experienceAssessment;
  if (experience) addCandidateSection(profile, 'Lived experience and conditions', typeof experience === 'object'
    ? Object.entries(experience).map(([key, value]) => `${readableCategory(key)}: ${asText(value)}`)
    : experience);
  addCandidateSection(profile, 'Unknowns to pursue', candidate.unknowns);
  addCandidateSection(profile, 'Follow-up branches', candidate.followUpBranches);

  const evidence = Array.isArray(candidate.evidence) ? candidate.evidence : [];
  if (evidence.length) {
    const section = document.createElement('section');
    section.className = 'candidate-section';
    const heading = document.createElement('h3');
    heading.textContent = 'Evidence';
    section.append(heading);
    for (const source of evidence) {
      const card = document.createElement('div');
      card.className = 'evidence-card';
      const href = safeHref(asText(source.url));
      const sourceTitle = asText(source.title || source.url || 'Evidence source');
      if (href) {
        const link = document.createElement('a');
        link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = sourceTitle;
        card.append(link);
      } else {
        const title = document.createElement('strong'); title.textContent = sourceTitle; card.append(title);
      }
      const finding = document.createElement('div');
      finding.textContent = asText(source.finding || source.quoteOrFinding);
      const meta = document.createElement('small');
      meta.textContent = [source.sourceType, source.firsthand ? 'firsthand' : '', source.reliability, source.accessedAt ? `accessed ${source.accessedAt}` : ''].filter(Boolean).join(' · ');
      card.append(finding, meta);
      section.append(card);
    }
    profile.append(section);
  }
  return profile;
}

function openCandidate(discovery) {
  state.currentCandidate = discovery;
  document.querySelector('#candidate-dialog-name').textContent = discovery.name;
  const status = document.querySelector('#candidate-dialog-status');
  status.className = `candidate-status ${discovery.status}`;
  status.textContent = friendlyStatus(discovery.status);
  document.querySelector('#candidate-profile').replaceChildren(renderCandidateProfile(discovery));
  document.querySelector('#review-feedback').value = discovery.reviewFeedback || '';
  document.querySelector('#review-message').textContent = '';
  document.querySelector('#candidate-json').textContent = JSON.stringify(discovery.candidate, null, 2);
  document.querySelector('#candidate-dialog').showModal();
}

function renderLessons() {
  const target = document.querySelector('#lesson-list');
  if (!state.lessons.length) {
    target.replaceChildren(emptyState('No research lessons yet. Add one, or teach the agent while reviewing a candidate.'));
    return;
  }
  target.replaceChildren(...state.lessons.map(lesson => {
    const item = document.createElement('div');
    item.className = 'lesson';
    const head = document.createElement('div');
    head.className = 'lesson-head';
    const info = document.createElement('div');
    const label = document.createElement('small');
    label.textContent = `${lesson.scope === 'general' ? 'General' : 'Housing'} · ${lesson.source}`;
    const status = document.createElement('span');
    status.className = `lesson-status ${lesson.status}`;
    status.textContent = lesson.status;
    info.append(label);
    head.append(info, status);
    const text = document.createElement('p');
    text.textContent = lesson.text;
    item.append(head, text);
    if (lesson.rationale) {
      const rationale = document.createElement('small');
      rationale.textContent = lesson.rationale;
      item.append(rationale);
    }
    const actions = document.createElement('div');
    actions.className = 'lesson-actions';
    if (lesson.status === 'proposed') actions.append(lessonActionButton(lesson, 'active', 'Approve'));
    if (lesson.status !== 'retired') actions.append(lessonActionButton(lesson, 'retired', 'Retire'));
    if (lesson.status === 'retired') actions.append(lessonActionButton(lesson, 'active', 'Restore'));
    item.append(actions);
    return item;
  }));
}

function lessonActionButton(lesson, status, label) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'secondary';
  button.textContent = label;
  button.addEventListener('click', async () => {
    await request(`/api/lessons/${lesson.id}/status`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
    });
    await loadResearchData();
  });
  return button;
}

async function loadResearchData() {
  const [runs, discoveries, lessons] = await Promise.all([
    request('/api/research-runs'), request('/api/discoveries'), request('/api/lessons'),
  ]);
  state.runs = runs.runs;
  state.discoveries = discoveries.discoveries;
  state.lessons = lessons.lessons;
  renderRuns(); renderCandidates(); renderLessons();
  const active = state.runs.some(run => ['queued', 'running'].includes(run.status));
  if (active && !state.pollTimer) {
    state.pollTimer = setTimeout(async () => {
      state.pollTimer = null;
      try { await loadResearchData(); } catch { /* next manual refresh will retry */ }
    }, 2000);
  }
}

async function refresh() {
  const status = await request('/api/status');
  showAgent(status.agent);
  if (!status.latestImport) return;
  showImport(status.latestImport);
  const result = await request('/api/seeds');
  state.seeds = result.seeds;
  renderSeeds();
  await loadResearchData();
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
document.querySelector('#close-candidate').addEventListener('click', () => document.querySelector('#candidate-dialog').close());

document.querySelector('#copy-setup').addEventListener('click', async event => {
  const command = event.currentTarget.dataset.command || 'hermes setup';
  try {
    await navigator.clipboard.writeText(command);
    event.currentTarget.textContent = 'Copied';
    setTimeout(() => { event.currentTarget.textContent = 'Copy setup command'; }, 1500);
  } catch {
    document.querySelector('#research-message').textContent = `Run in Terminal: ${command}`;
  }
});

document.querySelector('#settings-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button');
  button.disabled = true;
  try {
    const payload = { settings: {
      adapter: document.querySelector('#agent-adapter').value,
      profile: document.querySelector('#agent-profile').value.trim(),
      provider: document.querySelector('#agent-provider').value.trim(),
      model: document.querySelector('#agent-model').value.trim(),
      command: document.querySelector('#agent-command').value.trim(),
      timeoutSeconds: Number(document.querySelector('#agent-timeout').value || 900),
    } };
    const result = await request('/api/agent/settings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    showAgent({ ...result.agent, settings: result.settings });
    document.querySelector('#research-message').textContent = 'Connection settings saved.';
  } catch (error) {
    document.querySelector('#research-message').textContent = error.message;
  } finally { button.disabled = false; }
});

document.querySelector('#research-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.querySelector('#start-research');
  const message = document.querySelector('#research-message');
  button.disabled = true;
  message.textContent = 'Giving Hermes the assignment and research context…';
  try {
    const run = await request('/api/research-runs', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        assignment: document.querySelector('#research-assignment').value,
        seedResourceId: document.querySelector('#research-seed').value,
      }),
    });
    message.textContent = `Research run ${run.id} started. You may keep reviewing seeds while Hermes works.`;
    await loadResearchData();
  } catch (error) {
    message.textContent = error.message;
  } finally { button.disabled = !state.agent?.ready; }
});

document.querySelector('#refresh-research').addEventListener('click', () => loadResearchData().catch(error => {
  document.querySelector('#research-message').textContent = error.message;
}));

document.querySelector('#lesson-form').addEventListener('submit', async event => {
  event.preventDefault();
  const text = document.querySelector('#lesson-text').value.trim();
  if (!text) return;
  await request('/api/lessons', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, scope: document.querySelector('#lesson-scope').value }),
  });
  document.querySelector('#lesson-text').value = '';
  await loadResearchData();
});

document.querySelector('#review-actions').addEventListener('click', async event => {
  const button = event.target.closest('button[data-status]');
  if (!button || !state.currentCandidate) return;
  const message = document.querySelector('#review-message');
  const feedback = document.querySelector('#review-feedback').value.trim();
  document.querySelectorAll('#review-actions button').forEach(item => { item.disabled = true; });
  message.textContent = 'Saving your review…';
  try {
    const result = await request(`/api/discoveries/${state.currentCandidate.id}/review`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: button.dataset.status, feedback,
        learn: document.querySelector('#review-learn').checked,
        scope: 'category',
      }),
    });
    message.textContent = result.lesson ? 'Review saved, and your feedback is now an active Housing lesson.' : 'Review saved.';
    state.currentCandidate = result.discovery;
    await loadResearchData();
    const status = document.querySelector('#candidate-dialog-status');
    status.className = `candidate-status ${result.discovery.status}`;
    status.textContent = friendlyStatus(result.discovery.status);
  } catch (error) {
    message.textContent = error.message;
  } finally {
    document.querySelectorAll('#review-actions button').forEach(item => { item.disabled = false; });
  }
});

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
