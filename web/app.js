const state = {
  runs: [], discoveries: [], lessons: [], agent: null, latestImport: null,
  currentCandidate: null, pollTimer: null, researchMode: 'package',
  researchMethod: 'manual', activeManualRun: null, manualContributions: [], manualConsolidation: null,
  manualAssignmentRequest: 0, customManualSources: 0,
  candidateRunId: null, candidateRunSelectionInitialized: false,
  assignmentDrafts: { package: '', 'standalone-location': '' }, standaloneAutoAssignment: '',
  categories: [], forGroups: [], activeCategoryId: 'housing', categoryAssignmentDrafts: {},
};

const PACKAGE_DEFAULT_ASSIGNMENT = 'Discover realistic ways a person without adequate housing in Utah County could obtain safe temporary or permanent housing. Follow useful relationships rather than stopping at a directory listing: voucher providers to participating motels, organizations to specific programs, and temporary options to longer-term pathways. Investigate practical access and lived experience as well as official claims.';

function setupResearchPaneResizer() {
  const container = document.querySelector('#research-results');
  const divider = document.querySelector('#research-divider');
  if (!container || !divider) return;
  const storageKey = 'resource-research-agent:runs-pane-ratio';
  const minimumRuns = 280;
  const minimumCandidates = 360;
  let ratio = Number.parseFloat(localStorage.getItem(storageKey) || '0.4');
  if (!Number.isFinite(ratio)) ratio = 0.4;

  function setRunsWidth(requestedWidth, save = false) {
    const total = container.getBoundingClientRect().width;
    if (!total) return;
    const dividerWidth = divider.getBoundingClientRect().width || 16;
    const maximumRuns = Math.max(minimumRuns, total - dividerWidth - minimumCandidates);
    const width = Math.min(maximumRuns, Math.max(minimumRuns, requestedWidth));
    ratio = width / total;
    container.style.setProperty('--runs-pane-width', `${width}px`);
    divider.setAttribute('aria-valuenow', String(Math.round(ratio * 100)));
    if (save) localStorage.setItem(storageKey, String(ratio));
  }

  function setFromPointer(event, save = false) {
    const bounds = container.getBoundingClientRect();
    setRunsWidth(event.clientX - bounds.left, save);
  }

  divider.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    divider.setPointerCapture(event.pointerId);
    divider.classList.add('dragging');
    document.body.classList.add('resizing-research-panes');
    setFromPointer(event);
  });
  divider.addEventListener('pointermove', event => {
    if (!divider.hasPointerCapture(event.pointerId)) return;
    setFromPointer(event);
  });
  divider.addEventListener('pointerup', event => {
    if (divider.hasPointerCapture(event.pointerId)) divider.releasePointerCapture(event.pointerId);
    divider.classList.remove('dragging');
    document.body.classList.remove('resizing-research-panes');
    setFromPointer(event, true);
  });
  divider.addEventListener('pointercancel', () => {
    divider.classList.remove('dragging');
    document.body.classList.remove('resizing-research-panes');
  });
  divider.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const total = container.getBoundingClientRect().width;
    if (event.key === 'Home') setRunsWidth(total * .25, true);
    else if (event.key === 'End') setRunsWidth(total * .7, true);
    else setRunsWidth((total * ratio) + (event.key === 'ArrowRight' ? 32 : -32), true);
  });
  window.addEventListener('resize', () => setRunsWidth(container.getBoundingClientRect().width * ratio));
  setRunsWidth(container.getBoundingClientRect().width * ratio);
}

function agentName(agent = state.agent) {
  if (agent?.displayName) return agent.displayName;
  const key = agent?.adapter || agent?.settings?.adapter || document.querySelector('#agent-adapter')?.value;
  return key === 'dsh' ? 'DSH' : key === 'demo' ? 'Built-in demo' : 'Hermes';
}

function updateAdapterFields() {
  const adapter = document.querySelector('#agent-adapter').value;
  const dshConfiguration = document.querySelector('#dsh-configuration').value;
  document.querySelectorAll('[data-adapter-only]').forEach(field => {
    const adapterMatches = field.dataset.adapterOnly.split(',').includes(adapter);
    const configurationMatches = !field.dataset.dshConfigurationOnly
      || field.dataset.dshConfigurationOnly === dshConfiguration;
    field.hidden = !(adapterMatches && configurationMatches);
  });
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}

function showImport(summary) {
  if (!summary) return;
  const importChanged = state.latestImport?.id !== summary.id;
  state.latestImport = summary;
  document.querySelector('#package-status-name').textContent = summary.sourceName;
  document.querySelector('#package-status').hidden = false;
  document.querySelector('#file-label').textContent = 'Choose a different package…';
  document.querySelector('#package-details').hidden = false;
  document.querySelector('#package-details-copy').textContent = [
    summary.officeName,
    summary.serviceArea,
    `Package ${summary.schema.packageVersion || 'version not recorded'}`,
    `schema ${summary.schema.schemaVersion || 'not recorded'}`,
    `${summary.resourceCount} resources`,
    `${(summary.categories || []).length} categories`,
    `imported ${formatWhen(summary.importedAt)}`,
    `SHA-256 ${summary.sourceSha256}`,
  ].join(' · ');
  state.categories = summary.categories || [];
  state.forGroups = summary.forGroups || [];
  if (importChanged) {
    state.categoryAssignmentDrafts = {};
    state.assignmentDrafts.package = '';
  }
  const supported = state.categories.filter(category => category.supported);
  if (!supported.some(category => category.id === state.activeCategoryId)) {
    state.activeCategoryId = supported.find(category => category.id.toLowerCase() === 'housing')?.id
      || supported[0]?.id || 'housing';
  }
  document.querySelector('#category-panel').hidden = false;
  document.querySelector('#research-panel').hidden = false;
  document.querySelector('#research-results').hidden = false;
  document.querySelector('#package-mode-detail').textContent = 'Default · existing resources provide research context and automatic duplicate checking.';
  if (selectedResearchMode() === 'package') {
    document.querySelector('#research-context-note').textContent = 'Existing resources in the connected package are used as context and will not be returned as new discoveries.';
  }
  renderCategoryChooser();
  updateCategoryCopy();
  if (importChanged && selectedResearchMode() === 'package') {
    document.querySelector('#research-assignment').value = packageDefaultAssignment();
    state.assignmentDrafts.package = packageDefaultAssignment();
  }
  updateStartResearchState();
  if (selectedResearchMethod() === 'manual') refreshManualAssignment();
}

function activeCategory() {
  return state.categories.find(category => category.id === state.activeCategoryId)
    || { id: 'housing', label: 'Housing', types: [], resourceCount: 0, multiCategoryResourceCount: 0, supported: true, defaultAssignment: PACKAGE_DEFAULT_ASSIGNMENT };
}

function packageDefaultAssignment() {
  const category = activeCategory();
  return category.defaultAssignment || `Discover realistic ${category.label.toLowerCase()} resources for people in Utah County. Follow useful relationships from coordinating organizations and broad directories to the specific programs, providers, benefits, and practical services people can actually access. Verify eligibility, costs, schedules, service areas, availability, and the real intake or enrollment path.`;
}

function updateCategoryCopy() {
  const category = activeCategory();
  document.querySelector('#research-heading-title').textContent = `Send a research agent on a ${category.label} assignment`;
  document.querySelector('#category-lesson-option').textContent = `${category.label} lesson`;
  const types = category.types?.length ? category.types.join(', ') : 'None defined in this package';
  const forGroups = state.forGroups.length ? state.forGroups.join(', ') : 'None defined in this package';
  document.querySelector('#category-taxonomy-note').textContent = `Types: ${types} · For: ${forGroups}`;
  if (document.querySelector('input[name="research-method"]:checked')) {
    const manual = selectedResearchMethod() === 'manual';
    document.querySelector('#research-heading-title').textContent = manual
      ? `Collect ${category.label} leads from your chats`
      : `Send a research agent on a ${category.label} assignment`;
  }
}

function renderCategoryChooser() {
  const target = document.querySelector('#category-grid');
  const supportedCount = state.categories.filter(category => category.supported).length;
  document.querySelector('#category-supported-count').textContent = `${supportedCount} categories`;
  target.replaceChildren(...state.categories.map(category => {
    const label = document.createElement('label');
    label.className = `category-choice${category.supported ? '' : ' disabled'}`;
    const input = document.createElement('input');
    input.type = 'radio'; input.name = 'research-category'; input.value = category.id;
    input.checked = category.id === state.activeCategoryId;
    input.disabled = !category.supported;
    const copy = document.createElement('span');
    const title = document.createElement('strong'); title.textContent = category.label;
    const detail = document.createElement('small');
    detail.textContent = category.supported
      ? `${category.resourceCount} existing · ${category.types?.length || 0} Type${category.types?.length === 1 ? '' : 's'}`
      : 'Unavailable';
    copy.append(title, detail); label.append(input, copy);
    if (category.supported) input.addEventListener('change', () => {
      selectCategory(category.id).catch(error => {
        document.querySelector('#research-message').textContent = error.message;
      });
    });
    return label;
  }));
}

async function selectCategory(categoryId) {
  const prior = activeCategory();
  if (selectedResearchMode() === 'package') {
    state.categoryAssignmentDrafts[prior.id] = document.querySelector('#research-assignment').value;
  }
  state.activeCategoryId = categoryId;
  renderCategoryChooser();
  updateCategoryCopy();
  const category = activeCategory();
  if (selectedResearchMode() === 'package') {
    document.querySelector('#research-assignment').value = state.categoryAssignmentDrafts[category.id]
      || packageDefaultAssignment();
  }
  updateStartResearchState();
  if (selectedResearchMethod() === 'manual') refreshManualAssignment();
}

function showAccess(access) {
  const panel = document.querySelector('#private-access');
  const url = access?.privateUrl || '';
  panel.hidden = !url;
  document.querySelector('main').classList.toggle('private-access-active', Boolean(url));
  if (!url) return;
  const link = document.querySelector('#private-access-url');
  link.href = url;
  link.textContent = url;
  const requester = access.requester;
  const connectedRemotely = Boolean(requester?.name || requester?.login);
  document.querySelector('#private-access-title').textContent = connectedRemotely
    ? 'Connected privately through Tailscale'
    : 'Private access is ready';
  document.querySelector('#private-access-detail').textContent = connectedRemotely
    ? `Signed in as ${requester.name || requester.login}.`
    : 'Open this address on an iPad connected to your Tailscale network.';
  link.hidden = connectedRemotely;
  const copyButton = document.querySelector('#copy-private-url');
  copyButton.hidden = connectedRemotely;
  copyButton.dataset.url = url;
}

function showAgent(agent) {
  state.agent = agent;
  const card = document.querySelector('#agent-state');
  const name = agentName(agent);
  card.classList.toggle('ready', Boolean(agent?.ready));
  card.classList.toggle('attention', Boolean(agent?.installed && !agent?.ready));
  document.querySelector('#agent-state-title').textContent = agent?.ready ? `${name} ready` : agent?.installed ? `${name} needs setup` : `${name} not installed`;
  document.querySelector('#agent-state-detail').textContent = agent?.message || agent?.version || '';
  document.querySelector('#agent-setup').hidden = selectedResearchMethod() !== 'agent'
    || Boolean(agent?.ready || agent?.adapter === 'demo');
  document.querySelector('#agent-setup-title').textContent = agent?.installed ? `Finish ${name} setup` : `Install ${name}`;
  document.querySelector('#agent-setup-detail').textContent = agent?.message || 'Complete the connection setup, then refresh this page.';
  document.querySelector('#copy-setup').dataset.command = agent?.setupCommand || 'hermes setup';
  const settings = agent?.settings || {};
  document.querySelector('#agent-adapter').value = settings.adapter || 'dsh';
  document.querySelector('#hermes-profile').value = settings.hermesProfile || settings.profile || '';
  document.querySelector('#hermes-provider').value = settings.hermesProvider || settings.provider || '';
  document.querySelector('#hermes-model').value = settings.hermesModel || settings.model || '';
  document.querySelector('#hermes-command').value = settings.hermesCommand || settings.command || '';
  document.querySelector('#dsh-configuration option[value="trace-qwen"]').hidden = settings.dshConfiguration !== 'trace-qwen';
  document.querySelector('#dsh-configuration').value = settings.dshConfiguration || 'local-qwen';
  document.querySelector('#dsh-model').value = settings.dshModel || '';
  document.querySelector('#dsh-command').value = settings.dshCommand || '';
  document.querySelector('#agent-timeout').value = settings.timeoutSeconds || 900;
  updateAdapterFields();
  updateStartResearchState();
}

function selectedResearchMode() {
  return document.querySelector('input[name="research-mode"]:checked')?.value || 'package';
}

function selectedResearchMethod() {
  return document.querySelector('input[name="research-method"]:checked')?.value || 'manual';
}

function standaloneDefaultAssignment(location) {
  const place = location.trim() || 'the selected location';
  return `Discover realistic ways a person without adequate housing in ${place} could obtain safe temporary or permanent housing. Follow useful relationships rather than stopping at a directory listing: voucher providers to participating motels, organizations to specific programs, and temporary options to longer-term pathways. Investigate practical access and lived experience as well as official claims.`;
}

function updateStartResearchState() {
  const mode = selectedResearchMode();
  const contextReady = mode === 'package'
    ? Boolean(state.latestImport && activeCategory().supported)
    : Boolean(document.querySelector('#target-location')?.value.trim());
  const button = document.querySelector('#start-research');
  const methodReady = selectedResearchMethod() === 'manual' || Boolean(state.agent?.ready);
  if (button) button.disabled = !methodReady || !contextReady;
}

function manualAssignmentPayload() {
  const mode = selectedResearchMode();
  return {
    researchMode: mode,
    sourceImportId: mode === 'package' ? state.latestImport?.id : null,
    categoryId: mode === 'package' ? state.activeCategoryId : 'housing',
    categoryLabel: mode === 'package' ? activeCategory().label : 'Housing',
    targetLocation: mode === 'standalone-location' ? document.querySelector('#target-location').value.trim() : '',
    regionalScope: mode === 'standalone-location' ? document.querySelector('#regional-scope').value.trim() : '',
  };
}

async function refreshManualAssignment() {
  if (selectedResearchMethod() !== 'manual') return;
  const payload = manualAssignmentPayload();
  if ((payload.researchMode === 'package' && !payload.sourceImportId)
      || (payload.researchMode === 'standalone-location' && !payload.targetLocation)) return;
  const requestNumber = ++state.manualAssignmentRequest;
  const message = document.querySelector('#research-message');
  message.textContent = 'Preparing the copyable discovery assignment…';
  try {
    const result = await request('/api/manual-discovery-assignment', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    if (requestNumber !== state.manualAssignmentRequest || selectedResearchMethod() !== 'manual') return;
    document.querySelector('#research-assignment').value = result.assignment;
    message.textContent = `${result.context.knownResources.length} existing ${result.context.categoryLabel} resource${result.context.knownResources.length === 1 ? '' : 's'} included as the do-not-repeat list.`;
  } catch (error) {
    if (requestNumber === state.manualAssignmentRequest) message.textContent = error.message;
  }
}

function switchResearchMethod() {
  state.researchMethod = selectedResearchMethod();
  const manual = state.researchMethod === 'manual';
  document.querySelectorAll('[data-agent-only]').forEach(element => {
    if (manual) element.hidden = true;
    else if (element.id === 'agent-setup') element.hidden = Boolean(state.agent?.ready || state.agent?.adapter === 'demo');
    else element.hidden = false;
  });
  document.querySelector('#research-heading-title').textContent = manual
    ? `Collect ${activeCategory().label} leads from your chats`
    : `Send a research agent on a ${activeCategory().label} assignment`;
  document.querySelector('#research-heading-detail').textContent = manual
    ? 'Copy one focused assignment into the chats you choose, then bring their responses back to Scout. No chat API or paid fallback is used.'
    : 'Your selected agent researches the public web in bounded stages. Existing DeepSeek, local Qwen, Hermes, and demo behavior remains available.';
  document.querySelector('#start-research').textContent = manual ? 'Start manual discovery' : 'Start agent research';
  updateStartResearchState();
  if (manual) refreshManualAssignment();
  else switchResearchMode();
}

function updateStandaloneAutoAssignment() {
  const next = standaloneDefaultAssignment(document.querySelector('#target-location').value);
  const assignment = document.querySelector('#research-assignment');
  if (selectedResearchMode() === 'standalone-location'
      && (!assignment.value.trim() || assignment.value === state.standaloneAutoAssignment)) {
    assignment.value = next;
  }
  state.standaloneAutoAssignment = next;
  state.assignmentDrafts['standalone-location'] = assignment.value;
  updateStartResearchState();
  if (selectedResearchMethod() === 'manual') refreshManualAssignment();
}

function switchResearchMode() {
  const nextMode = selectedResearchMode();
  const assignment = document.querySelector('#research-assignment');
  state.assignmentDrafts[state.researchMode] = assignment.value;
  state.researchMode = nextMode;
  document.querySelector('#standalone-research-fields').hidden = nextMode !== 'standalone-location';
  if (nextMode === 'package') {
    assignment.value = state.categoryAssignmentDrafts[state.activeCategoryId]
      || state.assignmentDrafts.package || packageDefaultAssignment();
    document.querySelector('#research-context-note').textContent = state.latestImport
      ? 'Existing resources in the connected package are used as context and will not be returned as new discoveries.'
      : 'Package-backed research is the default. Import a resource package above before starting.';
  } else {
    state.standaloneAutoAssignment = standaloneDefaultAssignment(document.querySelector('#target-location').value);
    assignment.value = state.assignmentDrafts['standalone-location'] || state.standaloneAutoAssignment;
    document.querySelector('#research-context-note').textContent = 'This exploratory run will not compare candidates with a connected package or claim to be an official TSO Resources inventory.';
  }
  updateStartResearchState();
  if (selectedResearchMethod() === 'manual') refreshManualAssignment();
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

function readableCategory(category) {
  const raw = asText(category);
  return raw.split(/[-_]/).map(word => word.toUpperCase() === 'ID' ? 'ID' : word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function friendlyStatus(value) {
  return String(value || '').replaceAll('-', ' ');
}

function formatWhen(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatDuration(run) {
  if (!run.startedAt) return '';
  const start = new Date(run.startedAt).getTime();
  const end = new Date(run.completedAt || Date.now()).getTime();
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return '';
  const totalSeconds = Math.max(0, Math.round((end - start) / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours) return `${hours} hr ${minutes} min`;
  if (minutes) return `${minutes} min ${seconds} sec`;
  return `${seconds} sec`;
}

function runPlace(run) {
  return run.researchMode === 'standalone-location'
    ? run.targetLocation
    : run.sourceOfficeName || run.sourceServiceArea || 'Connected package';
}

function emptyState(text) {
  const element = document.createElement('div');
  element.className = 'empty-state';
  element.textContent = text;
  return element;
}

function researchRunTitle(run) {
  const category = run.targetCategoryLabel || 'Housing';
  if (run.runKind === 'manual-discovery') return `${category} manual discovery · ${runPlace(run)}`;
  const research = run.seedResourceId
      ? `${category} research from ${run.prompt?.selectedSeed?.name || run.seedResourceId}`
      : `${category} research`;
  return `${research} · ${runPlace(run)}`;
}

function candidateCountForRun(runId) {
  return state.discoveries.filter(discovery => discovery.runId === runId).length;
}

function selectCandidateRun(runId, { scroll = false } = {}) {
  state.candidateRunId = runId;
  state.candidateRunSelectionInitialized = true;
  renderRuns();
  renderCandidates();
  if (scroll) {
    document.querySelector('.candidates-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function appendLabeledSummaryText(target, text) {
  const match = String(text || '').match(/^([^:]{2,40}):\s*(.*)$/s);
  if (!match || !/^(key findings?|major caution|caution|typical first step|first step|gap identified|strongest gap found)$/i.test(match[1].replace(/^the\s+/i, ''))) {
    target.textContent = text;
    return;
  }
  const label = document.createElement('strong');
  label.textContent = `${match[1]}: `;
  target.append(label, document.createTextNode(match[2]));
}

function renderLegacySummary(text) {
  const content = document.createElement('div');
  content.className = 'stage-summary-content';
  const normalized = String(text || '')
    .replace(/\s+The typical first step is(?: to)?\s+([a-z])/gi, (_, firstLetter) => `\n\nTypical first step: ${firstLetter.toUpperCase()}`)
    .replace(/\s+(?=(?:Key findings?|Major caution|Caution|(?:The\s+)?Typical first step|Gap identified|The strongest gap found):)/gi, '\n\n')
    .replace(/\s+\((\d+)\)\s+/g, '\n\n($1) ')
    .replace(/\s+(?=(?:Most |Known resources|Prior-stage candidates|Also surfaced a lead|None of these|Phones are left blank))/g, '\n\n');
  const blocks = normalized.split(/\n{2,}/).map(value => value.trim()).filter(Boolean);
  let list = null;
  blocks.forEach(block => {
    const numbered = block.match(/^\((\d+)\)\s+([\s\S]+)$/);
    if (numbered) {
      if (!list) {
        list = document.createElement('ol');
        content.append(list);
      }
      const item = document.createElement('li');
      item.textContent = numbered[2];
      list.append(item);
      return;
    }
    list = null;
    const paragraph = document.createElement('p');
    appendLabeledSummaryText(paragraph, block);
    content.append(paragraph);
  });
  return content;
}

function appendSummarySection(target, title, items, className, { ordered = false } = {}) {
  if (!Array.isArray(items) || !items.length) return;
  const section = document.createElement('section');
  section.className = `summary-section ${className}`;
  const heading = document.createElement('h5');
  heading.textContent = title;
  const list = document.createElement(ordered ? 'ol' : 'ul');
  items.forEach(value => {
    const item = document.createElement('li');
    item.textContent = value;
    list.append(item);
  });
  section.append(heading, list);
  target.append(section);
}

function renderStageSummary(stage) {
  const card = document.createElement('section');
  card.className = 'stage-summary-card';
  const heading = document.createElement('h4');
  heading.textContent = stage.title || 'Research stage';
  card.append(heading);
  const sections = stage.summarySections;
  const hasStructuredSummary = sections && typeof sections === 'object' && (
    sections.overview
    || sections.keyFindings?.length
    || sections.cautions?.length
    || sections.accessSteps?.length
    || sections.gaps?.length
  );
  if (!hasStructuredSummary) {
    card.append(renderLegacySummary(stage.summary));
    return card;
  }
  if (sections.overview) {
    const overview = document.createElement('p');
    overview.className = 'stage-overview';
    overview.textContent = sections.overview;
    card.append(overview);
  }
  appendSummarySection(card, 'Key findings', sections.keyFindings, 'key-findings', { ordered: true });
  appendSummarySection(card, 'Cautions', sections.cautions, 'cautions');
  appendSummarySection(card, 'Practical access', sections.accessSteps, 'access-steps');
  appendSummarySection(card, 'Gaps and unanswered questions', sections.gaps, 'gaps');
  return card;
}

function renderRunFindings(run) {
  const summaries = Array.isArray(run.result?.stageSummaries) ? run.result.stageSummaries : [];
  const details = document.createElement('details');
  details.className = 'run-findings';
  const toggle = document.createElement('summary');
  toggle.textContent = summaries.length
    ? `Show full findings (${summaries.length} stage${summaries.length === 1 ? '' : 's'})`
    : 'Show full findings';
  const content = document.createElement('div');
  content.className = 'run-findings-content';
  if (summaries.length) {
    summaries.forEach((stage, index) => {
      const card = renderStageSummary(stage);
      card.querySelector('h4').textContent = `${index + 1}. ${card.querySelector('h4').textContent}`;
      content.append(card);
    });
  } else {
    content.append(renderLegacySummary(run.result?.summary));
  }
  details.append(toggle, content);
  return details;
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
    title.textContent = researchRunTitle(run);
    const status = document.createElement('span');
    status.className = `run-status ${run.status}`;
    status.textContent = friendlyStatus(run.status);
    head.append(title, status);
    const time = document.createElement('small');
    const duration = formatDuration(run);
    const method = run.runKind === 'manual-discovery' ? 'manual chats' : run.adapter;
    time.textContent = `${formatWhen(run.createdAt)}${duration ? ` · Duration ${duration}` : ''} · ${method} · ${run.researchMode === 'standalone-location' ? 'standalone location' : 'package-backed'}`;
    item.append(head, time);
    if (run.runKind === 'manual-discovery') {
      const progress = document.createElement('div');
      progress.className = 'run-progress';
      const received = run.manualProgress?.contributionCount || 0;
      const leads = run.manualProgress?.leadCount || 0;
      const errors = run.manualProgress?.errorContributionCount || 0;
      progress.textContent = `${received} response${received === 1 ? '' : 's'} received · ${leads} parsed lead${leads === 1 ? '' : 's'}${errors ? ` · ${errors} needs correction` : ''}`;
      item.append(progress);
    }
    if (run.progress?.total) {
      const progress = document.createElement('div');
      progress.className = 'run-progress';
      progress.textContent = `${run.progress.completed} of ${run.progress.total} research stages completed`;
      item.append(progress);
      const stages = document.createElement('details');
      stages.className = 'run-stages';
      const summary = document.createElement('summary');
      summary.textContent = 'View stage progress';
      const list = document.createElement('ol');
      (run.stages || []).forEach(stage => {
        const entry = document.createElement('li');
        const stageTitle = document.createElement('span');
        stageTitle.textContent = stage.title;
        const stageStatus = document.createElement('small');
        stageStatus.className = `stage-status ${stage.status}`;
        stageStatus.textContent = friendlyStatus(stage.status);
        entry.append(stageTitle, stageStatus);
        if (stage.error) {
          const error = document.createElement('div');
          error.className = 'stage-error';
          error.textContent = stage.error;
          entry.append(error);
        }
        list.append(entry);
      });
      stages.append(summary, list);
      item.append(stages);
    }
    const actions = document.createElement('div');
    actions.className = 'run-actions';
    if (run.runKind === 'manual-discovery') {
      const openManual = document.createElement('button');
      openManual.type = 'button';
      openManual.className = 'secondary view-manual-run';
      openManual.textContent = run.status === 'running' ? 'Continue collecting responses' : 'View responses';
      openManual.addEventListener('click', () => openManualDiscoveryRun(run.id));
      actions.append(openManual);
      if (run.status === 'completed') {
        const viewCandidates = document.createElement('button');
        viewCandidates.type = 'button';
        viewCandidates.className = 'secondary view-candidates';
        viewCandidates.setAttribute('aria-pressed', String(state.candidateRunId === run.id));
        viewCandidates.textContent = `View candidates (${candidateCountForRun(run.id)})`;
        viewCandidates.addEventListener('click', () => selectCandidateRun(run.id, { scroll: true }));
        const exportLink = document.createElement('a');
        exportLink.className = 'review-export';
        exportLink.href = `/api/research-runs/${run.id}/review-copy`;
        exportLink.download = '';
        exportLink.textContent = 'Export Resource Curator';
        actions.append(viewCandidates, exportLink);
      }
      item.append(actions);
      if (run.result?.summary) item.append(renderRunFindings(run));
      return item;
    }
    const viewCandidates = document.createElement('button');
    viewCandidates.type = 'button';
    viewCandidates.className = 'secondary view-candidates';
    viewCandidates.setAttribute('aria-pressed', String(state.candidateRunId === run.id));
    viewCandidates.textContent = `View candidates (${candidateCountForRun(run.id)})`;
    viewCandidates.addEventListener('click', () => selectCandidateRun(run.id, { scroll: true }));
    actions.append(viewCandidates);
    if (['completed', 'partial'].includes(run.status)) {
      const exportLink = document.createElement('a');
      exportLink.className = 'review-export';
      exportLink.href = `/api/research-runs/${run.id}/review-copy`;
      exportLink.download = '';
      exportLink.textContent = 'Export Resource Curator';
      const detail = document.createElement('small');
      detail.textContent = 'This run only · portable vetting and package workspace';
      actions.append(exportLink, detail);
      if (run.status === 'partial') {
        const resume = document.createElement('button');
        resume.type = 'button';
        resume.className = 'secondary resume-run';
        resume.textContent = 'Resume research';
        resume.addEventListener('click', () => resumeResearchRun(run, resume));
        actions.append(resume);
      }
    }
    if (run.status === 'failed') {
      const resume = document.createElement('button');
      resume.type = 'button';
      resume.className = 'secondary resume-run';
      resume.textContent = run.progress?.total ? 'Retry failed stage' : 'Retry as staged research';
      resume.addEventListener('click', () => resumeResearchRun(run, resume));
      actions.append(resume);
    }
    item.append(actions);
    if (run.result?.summary || run.result?.stageSummaries?.length) item.append(renderRunFindings(run));
    if (run.error) {
      const error = document.createElement('div');
      error.className = 'run-error';
      error.textContent = run.error;
      item.append(error);
    }
    return item;
  }));
}

async function copyText(text, button, originalLabel) {
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = 'Copied';
    setTimeout(() => { button.textContent = originalLabel; }, 1500);
    return true;
  } catch {
    button.textContent = 'Select and copy the text';
    setTimeout(() => { button.textContent = originalLabel; }, 2200);
    return false;
  }
}

function manualContributionSummary(contribution) {
  const box = document.createElement('div');
  box.className = `manual-validation ${contribution.parseStatus}`;
  if (contribution.parseStatus === 'error') {
    const error = document.createElement('strong');
    error.textContent = `Needs correction: ${contribution.error}`;
    box.append(error);
    return box;
  }
  const counts = new Map();
  let blankWebsites = 0;
  let warningCount = contribution.warnings.length;
  contribution.leads.forEach(lead => {
    counts.set(lead.leadType || 'unclassified', (counts.get(lead.leadType || 'unclassified') || 0) + 1);
    if (!lead.website) blankWebsites += 1;
    warningCount += lead.warnings.length;
  });
  const summary = document.createElement('strong');
  const types = [...counts].map(([type, count]) => `${count} ${friendlyStatus(type)}`).join(', ');
  summary.textContent = `${contribution.leads.length} lead${contribution.leads.length === 1 ? '' : 's'} parsed${types ? ` · ${types}` : ''}`;
  const details = document.createElement('small');
  details.textContent = `${blankWebsites} blank website${blankWebsites === 1 ? '' : 's'} · ${warningCount} parser warning${warningCount === 1 ? '' : 's'}${contribution.trailingText.trim() ? ' · trailing source text preserved' : ''}`;
  box.append(summary, details);
  return box;
}

function createManualSourceCard(label, contribution = null, custom = false) {
  const run = state.activeManualRun;
  const locked = run.status !== 'running';
  const card = document.createElement('article');
  card.className = 'manual-source-card';
  if (contribution) card.dataset.contributionId = String(contribution.id);
  const heading = document.createElement('div');
  heading.className = 'manual-source-heading';
  const sourceLabel = document.createElement('input');
  sourceLabel.className = 'manual-source-label';
  sourceLabel.value = contribution?.sourceLabel || label;
  sourceLabel.readOnly = !custom || locked;
  sourceLabel.setAttribute('aria-label', 'Chat source label');
  const stateLabel = document.createElement('span');
  stateLabel.className = contribution ? `manual-source-state ${contribution.parseStatus}` : 'manual-source-state';
  stateLabel.textContent = contribution ? (contribution.parseStatus === 'parsed' ? 'Saved' : 'Check response') : 'Waiting';
  heading.append(sourceLabel, stateLabel);
  const textarea = document.createElement('textarea');
  textarea.rows = 10;
  textarea.placeholder = `Paste ${label || 'this source'}'s complete response here…`;
  textarea.value = contribution?.rawText || '';
  textarea.disabled = locked;
  const uploadRow = document.createElement('div');
  uploadRow.className = 'manual-upload-row';
  const uploadLabel = document.createElement('label');
  uploadLabel.className = 'manual-file-button';
  uploadLabel.textContent = 'Choose text or JSON file';
  const upload = document.createElement('input');
  upload.type = 'file';
  upload.accept = '.txt,.json,text/plain,application/json';
  upload.disabled = locked;
  uploadLabel.append(upload);
  const filename = document.createElement('span');
  filename.className = 'muted';
  filename.textContent = contribution?.filename || 'No file selected';
  uploadRow.append(uploadLabel, filename);
  const feedback = document.createElement('div');
  feedback.className = 'manual-card-feedback';
  if (contribution) feedback.append(manualContributionSummary(contribution));
  const actions = document.createElement('div');
  actions.className = 'manual-card-actions';
  const save = document.createElement('button');
  save.type = 'button';
  save.textContent = contribution ? 'Replace saved response' : 'Validate and save';
  save.disabled = locked;
  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'secondary';
  remove.textContent = 'Delete';
  remove.hidden = locked || (!contribution && !custom);
  actions.append(save, remove);
  upload.addEventListener('change', async () => {
    const file = upload.files[0];
    if (!file) return;
    try {
      textarea.value = await file.text();
      textarea.dataset.filename = file.name;
      filename.textContent = file.name;
      feedback.textContent = 'File loaded. Choose Validate and save.';
    } catch {
      feedback.textContent = 'Scout could not read that file.';
    }
  });
  save.addEventListener('click', async () => {
    const source = sourceLabel.value.trim();
    if (!source || !textarea.value.trim()) {
      feedback.textContent = 'Enter a source label and paste or choose a response.';
      return;
    }
    save.disabled = true;
    feedback.textContent = 'Validating and preserving the response…';
    try {
      await request(`/api/manual-discovery-runs/${run.id}/contributions`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sourceLabel: source,
          rawText: textarea.value,
          filename: textarea.dataset.filename || contribution?.filename || '',
        }),
      });
      await openManualDiscoveryRun(run.id);
      document.querySelector('#manual-discovery-message').textContent = `${source} response saved with its original text and source label.`;
    } catch (error) {
      feedback.textContent = error.message;
      save.disabled = false;
    }
  });
  remove.addEventListener('click', async () => {
    if (!contribution) {
      card.remove();
      return;
    }
    if (!window.confirm(`Delete the saved ${contribution.sourceLabel} response from this unfinished run?`)) return;
    try {
      await request(`/api/manual-discovery-runs/${run.id}/contributions/${contribution.id}`, { method: 'DELETE' });
      await openManualDiscoveryRun(run.id);
      document.querySelector('#manual-discovery-message').textContent = `${contribution.sourceLabel} response deleted.`;
    } catch (error) {
      feedback.textContent = error.message;
    }
  });
  const raw = document.createElement('details');
  raw.className = 'manual-raw-response';
  const rawSummary = document.createElement('summary');
  rawSummary.textContent = contribution ? 'View preserved response and source notes' : 'Response details';
  const rawText = document.createElement('pre');
  rawText.textContent = contribution?.rawText || 'The exact response will be preserved after saving.';
  raw.append(rawSummary, rawText);
  if (contribution?.trailingText.trim()) {
    const trailingTitle = document.createElement('strong');
    trailingTitle.textContent = 'Preserved trailing source text';
    const trailing = document.createElement('pre');
    trailing.textContent = contribution.trailingText;
    raw.append(trailingTitle, trailing);
  }
  card.append(heading, textarea, uploadRow, feedback, actions, raw);
  return card;
}

function renderManualConsolidation() {
  const section = document.querySelector('#manual-consolidation');
  const consolidation = state.manualConsolidation;
  section.hidden = !consolidation;
  if (!consolidation) return;
  const funnel = consolidation.funnel;
  const funnelItems = [
    ['Submitted rows', funnel.submittedRows],
    ['Parsed leads', funnel.parsedLeads],
    ['Repeated rows collapsed', funnel.exactDuplicateRows],
    ['Consolidated identities', funnel.consolidatedIdentities],
    ['Provider/program candidates', funnel.providerProgramIdentities],
    ['Access-point candidates', funnel.accessPointIdentities],
    ['Routing sources/directories', funnel.routingDirectoryIdentities],
    ['Limited initiatives', funnel.outreachInitiatives],
    ['Unresolved roles', funnel.unresolvedIdentities],
    ['Possible package duplicates', funnel.possiblePackageDuplicates],
  ];
  document.querySelector('#manual-funnel').replaceChildren(...funnelItems.map(([label, value]) => {
    const item = document.createElement('div');
    const count = document.createElement('strong');
    count.textContent = value;
    const name = document.createElement('span');
    name.textContent = label;
    item.append(count, name);
    return item;
  }));
  const suggestionsTarget = document.querySelector('#manual-identity-suggestions');
  if (!consolidation.suggestions.length) {
    suggestionsTarget.replaceChildren(emptyState('No ambiguous identity pairs need review.'));
  } else {
    const pendingSuggestions = consolidation.suggestions.filter(item => item.status === 'pending');
    const reviewedSuggestions = consolidation.suggestions.filter(item => item.status !== 'pending');
    const heading = document.createElement('div');
    heading.className = 'manual-suggestion-intro';
    const title = document.createElement('h4');
    title.textContent = `Identity review · ${pendingSuggestions.length} pending`;
    const copy = document.createElement('p');
    copy.textContent = 'Decide only whether each pair is the same service identity. This is not a quality or acceptance decision, and no written reason is required.';
    heading.append(title, copy);
    if (pendingSuggestions.length > 1) {
      const leaveAll = document.createElement('button');
      leaveAll.type = 'button';
      leaveAll.className = 'secondary';
      leaveAll.textContent = `Leave all ${pendingSuggestions.length} pending pairs unresolved`;
      leaveAll.disabled = state.activeManualRun.status !== 'running';
      leaveAll.addEventListener('click', async () => {
        if (!window.confirm('Keep every pending pair separate and mark the identity relationship unresolved? You can still revise individual decisions before finishing discovery.')) return;
        leaveAll.disabled = true;
        try {
          state.manualConsolidation = await request(`/api/manual-discovery-runs/${state.activeManualRun.id}/leave-pending-unresolved`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
          });
          renderManualDiscoveryWorkspace();
        } catch (error) {
          document.querySelector('#manual-discovery-message').textContent = error.message;
          leaveAll.disabled = false;
        }
      });
      heading.append(leaveAll);
    }
    const renderSuggestion = suggestion => {
      const card = document.createElement('article');
      card.className = `manual-identity-suggestion ${suggestion.status}`;
      const pair = document.createElement('div');
      pair.className = 'manual-identity-pair';
      for (const side of [suggestion.left, suggestion.right]) {
        const identity = document.createElement('div');
        const name = document.createElement('strong');
        name.textContent = side.displayName || 'Unnamed identity';
        const detail = document.createElement('small');
        detail.textContent = `${side.organization || 'Organization not supplied'}${side.program ? ` · ${side.program}` : ''} · ${side.sources.join(', ')}`;
        identity.append(name, detail);
        pair.append(identity);
      }
      const reason = document.createElement('p');
      reason.textContent = suggestion.reason;
      const actions = document.createElement('div');
      actions.className = 'manual-identity-actions';
      for (const [decision, label] of [['same', 'Same identity'], ['separate', 'Keep separate'], ['unresolved', 'Leave unresolved']]) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'secondary';
        button.textContent = label;
        button.setAttribute('aria-pressed', String(suggestion.status === decision));
        button.disabled = state.activeManualRun.status !== 'running';
        button.addEventListener('click', async () => {
          actions.querySelectorAll('button').forEach(item => { item.disabled = true; });
          try {
            state.manualConsolidation = await request(`/api/manual-discovery-runs/${state.activeManualRun.id}/identity-decision`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                leftKey: suggestion.leftKey,
                rightKey: suggestion.rightKey,
                decision,
              }),
            });
            renderManualDiscoveryWorkspace();
          } catch (error) {
            document.querySelector('#manual-discovery-message').textContent = error.message;
            actions.querySelectorAll('button').forEach(item => { item.disabled = false; });
          }
        });
        actions.append(button);
      }
      card.append(pair, reason, actions);
      return card;
    };
    const pendingCards = pendingSuggestions.map(renderSuggestion);
    const children = [heading];
    if (!pendingCards.length) children.push(emptyState('No identity pairs are waiting for a decision.'));
    children.push(...pendingCards);
    if (reviewedSuggestions.length) {
      const reviewed = document.createElement('details');
      reviewed.className = 'manual-reviewed-identities';
      const summary = document.createElement('summary');
      summary.textContent = `Review or change ${reviewedSuggestions.length} recorded identity decision${reviewedSuggestions.length === 1 ? '' : 's'}`;
      reviewed.append(summary, ...reviewedSuggestions.map(renderSuggestion));
      children.push(reviewed);
    }
    suggestionsTarget.replaceChildren(...children);
  }
  document.querySelector('#manual-group-summary').textContent = `View ${consolidation.groups.length} consolidated identity group${consolidation.groups.length === 1 ? '' : 's'}`;
  document.querySelector('#manual-group-list').replaceChildren(...consolidation.groups.map(group => {
    const item = document.createElement('article');
    item.className = 'manual-group';
    const head = document.createElement('div');
    const name = document.createElement('strong');
    name.textContent = group.displayName;
    const role = document.createElement('span');
    role.textContent = friendlyStatus(group.routedRole);
    head.append(name, role);
    const sources = document.createElement('small');
    sources.textContent = `${group.members.length} submitted row${group.members.length === 1 ? '' : 's'} · ${[...new Set(group.members.map(member => member.sourceLabel))].join(', ')}`;
    item.append(head, sources);
    if (group.duplicateMatches.length) {
      const duplicate = document.createElement('p');
      duplicate.textContent = `Possible package relationship: ${group.duplicateMatches[0].name} (${group.duplicateMatches[0].classification})`;
      item.append(duplicate);
    }
    return item;
  }));
}

function renderManualDiscoveryWorkspace() {
  const run = state.activeManualRun;
  if (!run) return;
  const locked = run.status !== 'running';
  document.querySelector('#manual-discovery-title').textContent = `${run.targetCategoryLabel} · ${locked ? 'Finished responses' : 'Collect chat responses'}`;
  document.querySelector('#manual-discovery-context').textContent = `${runPlace(run)} · ${locked ? 'This snapshot is locked.' : 'A run may finish with fewer than four responses.'}`;
  document.querySelector('#manual-assignment-text').textContent = run.assignment;
  const progress = run.manualProgress || {};
  document.querySelector('#manual-progress').textContent = `${progress.contributionCount || 0} response${progress.contributionCount === 1 ? '' : 's'} received · ${progress.leadCount || 0} parsed lead${progress.leadCount === 1 ? '' : 's'}${progress.errorContributionCount ? ` · ${progress.errorContributionCount} response needs correction` : ''}`;
  renderManualConsolidation();
  const byLabel = new Map(state.manualContributions.map(item => [item.sourceLabel.toLowerCase(), item]));
  const defaults = ['ChatGPT', 'Grok', 'Claude', 'Perplexity'];
  const cards = defaults.map(label => createManualSourceCard(label, byLabel.get(label.toLowerCase()) || null));
  const defaultKeys = new Set(defaults.map(label => label.toLowerCase()));
  state.manualContributions
    .filter(item => !defaultKeys.has(item.sourceLabel.toLowerCase()))
    .forEach(item => cards.push(createManualSourceCard(item.sourceLabel, item, true)));
  document.querySelector('#manual-source-list').replaceChildren(...cards);
  document.querySelector('#add-manual-source').hidden = locked;
  const consolidate = document.querySelector('#consolidate-manual-discovery');
  consolidate.hidden = locked;
  consolidate.disabled = !progress.contributionCount || Boolean(progress.errorContributionCount);
  consolidate.textContent = state.manualConsolidation ? 'Re-consolidate leads' : 'Consolidate leads';
  const finish = document.querySelector('#finish-manual-discovery');
  finish.hidden = locked;
  finish.disabled = !state.manualConsolidation
    || Boolean(progress.errorContributionCount)
    || Boolean(state.manualConsolidation?.funnel.pendingIdentityDecisions);
}

async function openManualDiscoveryRun(runId) {
  const result = await request(`/api/manual-discovery-runs/${runId}/contributions`);
  state.activeManualRun = result.run;
  state.manualContributions = result.contributions;
  state.manualConsolidation = result.consolidation;
  renderManualDiscoveryWorkspace();
  const dialog = document.querySelector('#manual-discovery-dialog');
  if (!dialog.open) dialog.showModal();
}

async function resumeResearchRun(run, button) {
  const message = document.querySelector('#research-message');
  button.disabled = true;
  state.candidateRunId = run.id;
  state.candidateRunSelectionInitialized = true;
  message.textContent = `Resuming ${run.targetLocation ? `${run.targetLocation} ` : ''}research from the first unfinished stage…`;
  try {
    await request(`/api/research-runs/${run.id}/resume`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    message.textContent = `Research run ${run.id} resumed. Completed stages will not be repeated.`;
    await loadResearchData();
  } catch (error) {
    message.textContent = error.message;
    button.disabled = false;
  }
}

function candidateDescription(discovery) {
  const candidate = discovery.candidate || {};
  return asText(candidate.serviceNeed || candidate.housingNeed || candidate.description || candidate.resourceType || 'Research candidate');
}

function candidateMatchSummary(discovery) {
  const match = discovery.matchDetails;
  if (!match) return '';
  return `Possible relationship to existing resource: ${match.name}`;
}

function renderCandidates() {
  const target = document.querySelector('#candidate-list');
  const filter = document.querySelector('#candidate-run-filter');
  const all = document.createElement('option');
  all.value = '';
  all.textContent = `All candidates (${state.discoveries.length})`;
  const options = state.runs.map(run => {
    const option = document.createElement('option');
    option.value = String(run.id);
    option.textContent = `${researchRunTitle(run)} · ${candidateCountForRun(run.id)}`;
    return option;
  });
  filter.replaceChildren(all, ...options);
  filter.value = state.candidateRunId == null ? '' : String(state.candidateRunId);

  const selectedRun = state.runs.find(run => run.id === state.candidateRunId);
  const discoveries = selectedRun
    ? state.discoveries.filter(discovery => discovery.runId === selectedRun.id)
    : state.discoveries;
  document.querySelector('#candidate-count').textContent = discoveries.length;
  document.querySelector('#candidate-inbox-title').textContent = selectedRun
    ? `Research candidates · ${researchRunTitle(selectedRun)}`
    : 'Research candidates · All runs';
  document.querySelector('#candidate-inbox-context').textContent = selectedRun
    ? `Showing only candidates associated with research run ${selectedRun.id}. Use its run card to export a Resource Curator for human vetting, optional outcomes, resource editing, and package preparation.`
    : 'Showing candidates from every research run. Choose one run to inspect or export its Resource Curator.';
  if (!discoveries.length) {
    target.replaceChildren(emptyState(selectedRun
      ? 'No candidates have been saved for this research run yet.'
      : 'Research candidates will appear here after an agent run.'));
    return;
  }
  target.replaceChildren(...discoveries.map(discovery => {
    const item = document.createElement('div');
    item.className = 'candidate';
    item.tabIndex = 0;
    const head = document.createElement('div');
    head.className = 'candidate-head';
    const name = document.createElement('strong');
    name.textContent = discovery.name;
    const status = document.createElement('span');
    status.className = 'candidate-status';
    status.textContent = 'Candidate';
    head.append(name, status);
    const description = document.createElement('p');
    description.textContent = candidateDescription(discovery);
    const run = state.runs.find(entry => entry.id === discovery.runId);
    if (run) {
      const context = document.createElement('small');
      context.className = 'candidate-context';
      context.textContent = run.researchMode === 'standalone-location'
        ? `${run.targetCategoryLabel || 'Housing'} · Standalone research · ${run.targetLocation}`
        : `${run.targetCategoryLabel || 'Housing'} · Package-backed research · ${run.sourceOfficeName || run.sourceServiceArea || 'Connected package'}`;
      item.append(head, context, description);
    } else {
      item.append(head, description);
    }
    if (discovery.matchDetails) {
      const match = document.createElement('p');
      match.className = 'candidate-match';
      match.textContent = candidateMatchSummary(discovery);
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
  const summaryText = asText(candidate.description || candidate.serviceNeed || candidate.housingNeed);
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
  addCandidateFact(facts, 'Other phone numbers', candidate.additionalPhoneNumbers);
  addCandidateFact(facts, 'Address', candidate.address);
  addCandidateFact(facts, 'Other addresses', candidate.additionalAddresses);
  addCandidateFact(facts, 'Hours', candidate.hours);
  addCandidateFact(facts, 'Website', candidate.website || candidate.url, true);
  if (facts.children.length) profile.append(facts);
  const run = state.runs.find(entry => entry.id === discovery.runId);
  addCandidateSection(
    profile,
    `${run?.targetCategoryLabel || 'Resource'} need`,
    candidate.serviceNeed || candidate.housingNeed,
  );
  addCandidateSection(profile, 'Services provided', candidate.servicesProvided);
  addCandidateSection(profile, 'Suggested Types', candidate.recommendedTypes);
  addCandidateSection(profile, 'Suggested For', candidate.recommendedFor);
  addCandidateSection(profile, 'Classification rationale', candidate.classificationRationale);
  addCandidateSection(profile, 'Possible new Types for human review', candidate.suggestedNewTypes);
  addCandidateSection(profile, 'Eligibility requirements', candidate.eligibility);
  addCandidateSection(profile, 'What to expect', candidate.whatToExpect);
  addCandidateSection(profile, 'How to best connect', candidate.howToBestConnect);
  addCandidateSection(profile, 'Additional notes', candidate.additionalNotes);
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
  status.className = 'candidate-status';
  status.textContent = 'Research candidate';
  document.querySelector('#candidate-profile').replaceChildren(renderCandidateProfile(discovery));
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
    const context = lesson.researchMode === 'standalone-location'
      ? lesson.targetLocation
      : 'Package-backed';
    label.textContent = `${context} · ${lesson.scope === 'general' ? 'General' : (lesson.targetCategoryLabel || 'Housing')} · ${lesson.source}`;
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
  if (!state.candidateRunSelectionInitialized) {
    const latestWithCandidates = state.runs.find(run => candidateCountForRun(run.id) > 0);
    state.candidateRunId = latestWithCandidates?.id ?? null;
    state.candidateRunSelectionInitialized = true;
  } else if (state.candidateRunId != null && !state.runs.some(run => run.id === state.candidateRunId)) {
    state.candidateRunId = null;
  }
  renderRuns(); renderCandidates(); renderLessons();
  const active = state.runs.some(run => run.runKind !== 'manual-discovery'
    && ['queued', 'running'].includes(run.status));
  if (active && !state.pollTimer) {
    state.pollTimer = setTimeout(async () => {
      state.pollTimer = null;
      try { await loadResearchData(); } catch { /* next manual refresh will retry */ }
    }, 2000);
  }
}

async function refresh() {
  const status = await request('/api/status');
  if (status.version) document.querySelector('#app-version').textContent = `v${status.version}`;
  showAccess(status.access);
  showAgent(status.agent);
  if (status.latestImport) {
    showImport(status.latestImport);
  } else {
    state.latestImport = null;
    updateStartResearchState();
  }
  await loadResearchData();
}

async function importSelectedPackage() {
  const form = document.querySelector('#import-form');
  const input = document.querySelector('#package-input');
  if (!input.files[0]) return;
  const chooser = form.querySelector('.package-button');
  const message = document.querySelector('#import-message');
  chooser.classList.add('busy');
  message.className = 'message';
  document.querySelector('#file-label').textContent = 'Reading package…';
  message.textContent = 'Reading the package and building the known-resource index…';
  try {
    const result = await request('/api/import', { method: 'POST', body: new FormData(form) });
    showImport(result.import);
    switchResearchMode();
    message.textContent = `${result.import.sourceName} connected. The source ZIP was not changed.`;
  } catch (error) {
    message.className = 'message error';
    message.textContent = error.message;
    document.querySelector('#file-label').textContent = state.latestImport
      ? 'Choose a different package…' : 'Choose resource package…';
  } finally {
    chooser.classList.remove('busy');
    input.value = '';
  }
}

document.querySelector('#package-input').addEventListener('change', () => {
  importSelectedPackage();
});

document.querySelector('#import-form').addEventListener('submit', event => event.preventDefault());

document.querySelectorAll('input[name="research-mode"]').forEach(input => input.addEventListener('change', switchResearchMode));
document.querySelectorAll('input[name="research-method"]').forEach(input => input.addEventListener('change', switchResearchMethod));
document.querySelector('#target-location').addEventListener('input', updateStandaloneAutoAssignment);
document.querySelector('#regional-scope').addEventListener('input', () => {
  if (selectedResearchMethod() === 'manual') refreshManualAssignment();
});
document.querySelector('#close-candidate').addEventListener('click', () => document.querySelector('#candidate-dialog').close());
document.querySelector('#close-manual-discovery').addEventListener('click', () => document.querySelector('#manual-discovery-dialog').close());

document.querySelector('#copy-assignment').addEventListener('click', event => {
  copyText(document.querySelector('#research-assignment').value, event.currentTarget, 'Copy assignment');
});

document.querySelector('#copy-manual-assignment').addEventListener('click', event => {
  copyText(state.activeManualRun?.assignment || '', event.currentTarget, 'Copy assignment');
});

document.querySelector('#add-manual-source').addEventListener('click', () => {
  state.customManualSources += 1;
  const card = createManualSourceCard(`Other source ${state.customManualSources}`, null, true);
  document.querySelector('#manual-source-list').append(card);
  card.querySelector('.manual-source-label').focus();
  card.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

document.querySelector('#consolidate-manual-discovery').addEventListener('click', async event => {
  const run = state.activeManualRun;
  if (!run) return;
  event.currentTarget.disabled = true;
  const message = document.querySelector('#manual-discovery-message');
  message.textContent = 'Collapsing exact repeats and routing lead roles…';
  try {
    state.manualConsolidation = await request(`/api/manual-discovery-runs/${run.id}/consolidate`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    renderManualDiscoveryWorkspace();
    message.textContent = state.manualConsolidation.funnel.pendingIdentityDecisions
      ? `Consolidation ready. Review ${state.manualConsolidation.funnel.pendingIdentityDecisions} ambiguous identity pair${state.manualConsolidation.funnel.pendingIdentityDecisions === 1 ? '' : 's'}.`
      : 'Consolidation ready. No ambiguous identity pairs remain.';
  } catch (error) {
    message.textContent = error.message;
    event.currentTarget.disabled = false;
  }
});

document.querySelector('#finish-manual-discovery').addEventListener('click', async event => {
  const run = state.activeManualRun;
  if (!run || !window.confirm('Finish discovery and lock these source responses?')) return;
  event.currentTarget.disabled = true;
  const message = document.querySelector('#manual-discovery-message');
  message.textContent = 'Finishing the immutable response snapshot…';
  try {
    await request(`/api/manual-discovery-runs/${run.id}/finish`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    state.candidateRunId = run.id;
    state.candidateRunSelectionInitialized = true;
    await loadResearchData();
    await openManualDiscoveryRun(run.id);
    message.textContent = 'Discovery responses finished and locked.';
  } catch (error) {
    message.textContent = error.message;
    event.currentTarget.disabled = false;
  }
});

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

document.querySelector('#copy-private-url').addEventListener('click', async event => {
  const button = event.currentTarget;
  const url = button.dataset.url || '';
  try {
    await navigator.clipboard.writeText(url);
    button.textContent = 'Address copied';
    setTimeout(() => { button.textContent = 'Copy private address'; }, 1500);
  } catch {
    button.textContent = 'Press and hold the address to copy';
  }
});

document.querySelector('#agent-adapter').addEventListener('change', updateAdapterFields);
document.querySelector('#dsh-configuration').addEventListener('change', updateAdapterFields);

document.querySelector('#settings-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button');
  button.disabled = true;
  try {
    const payload = { settings: {
      adapter: document.querySelector('#agent-adapter').value,
      hermesProfile: document.querySelector('#hermes-profile').value.trim(),
      hermesProvider: document.querySelector('#hermes-provider').value.trim(),
      hermesModel: document.querySelector('#hermes-model').value.trim(),
      hermesCommand: document.querySelector('#hermes-command').value.trim(),
      dshConfiguration: document.querySelector('#dsh-configuration').value,
      dshModel: document.querySelector('#dsh-model').value.trim(),
      dshCommand: document.querySelector('#dsh-command').value.trim(),
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
  const name = agentName();
  const researchMode = selectedResearchMode();
  const targetLocation = document.querySelector('#target-location').value.trim();
  if (selectedResearchMethod() === 'manual') {
    message.textContent = 'Opening a manual discovery workspace…';
    try {
      const run = await request('/api/manual-discovery-runs', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...manualAssignmentPayload(),
          assignment: document.querySelector('#research-assignment').value,
        }),
      });
      message.textContent = `Manual discovery run ${run.id} opened. Copy the assignment into each chat and save the responses as they arrive.`;
      await loadResearchData();
      await openManualDiscoveryRun(run.id);
    } catch (error) {
      message.textContent = error.message;
    } finally { updateStartResearchState(); }
    return;
  }
  message.textContent = `Giving ${name} the assignment and research context…`;
  try {
    const run = await request('/api/research-runs', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        assignment: document.querySelector('#research-assignment').value,
        researchMode,
        seedResourceId: '',
        categoryId: researchMode === 'package' ? state.activeCategoryId : 'housing',
        targetLocation: researchMode === 'standalone-location' ? targetLocation : '',
        regionalScope: researchMode === 'standalone-location' ? document.querySelector('#regional-scope').value.trim() : '',
      }),
    });
    state.candidateRunId = run.id;
    state.candidateRunSelectionInitialized = true;
    message.textContent = researchMode === 'standalone-location'
      ? `Research run ${run.id} started for ${targetLocation}. Candidates will appear as each stage finishes and remain separate from the imported package.`
      : `Research run ${run.id} started. Candidates will appear as each stage finishes while ${name} works.`;
    await loadResearchData();
  } catch (error) {
    message.textContent = error.message;
  } finally { updateStartResearchState(); }
});

document.querySelector('#refresh-research').addEventListener('click', () => loadResearchData().catch(error => {
  document.querySelector('#research-message').textContent = error.message;
}));

document.querySelector('#candidate-run-filter').addEventListener('change', event => {
  selectCandidateRun(event.target.value ? Number(event.target.value) : null);
});

document.querySelector('#lesson-form').addEventListener('submit', async event => {
  event.preventDefault();
  const text = document.querySelector('#lesson-text').value.trim();
  if (!text) return;
  const researchMode = selectedResearchMode();
  const targetLocation = document.querySelector('#target-location').value.trim();
  if (researchMode === 'standalone-location' && !targetLocation) {
    document.querySelector('#research-message').textContent = 'Enter the standalone research location before adding a location-specific lesson.';
    return;
  }
  try {
    await request('/api/lessons', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        scope: document.querySelector('#lesson-scope').value,
        researchMode,
        targetLocation: researchMode === 'standalone-location' ? targetLocation : '',
        categoryId: researchMode === 'package' ? state.activeCategoryId : 'housing',
        categoryLabel: researchMode === 'package' ? activeCategory().label : 'Housing',
      }),
    });
    document.querySelector('#lesson-text').value = '';
    await loadResearchData();
  } catch (error) {
    document.querySelector('#research-message').textContent = error.message;
  }
});

state.assignmentDrafts.package = document.querySelector('#research-assignment').value;
setupResearchPaneResizer();
switchResearchMode();
switchResearchMethod();
refresh().catch(error => { document.querySelector('#import-message').textContent = error.message; });
