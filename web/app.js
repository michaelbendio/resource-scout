const state = {
  runs: [], discoveries: [], lessons: [], agent: null, latestImport: null,
  currentCandidate: null, pollTimer: null, researchMode: 'package',
  candidateRunId: null, candidateRunSelectionInitialized: false,
  assignmentDrafts: { package: '', 'standalone-location': '' }, standaloneAutoAssignment: '',
  categories: [], forGroups: [], activeCategoryId: 'housing', categoryAssignmentDrafts: {},
};

const PACKAGE_DEFAULT_ASSIGNMENT = 'Discover realistic ways a person without adequate housing in Utah County could obtain safe temporary or permanent housing. Follow useful relationships rather than stopping at a directory listing: voucher providers to participating motels, organizations to specific programs, and temporary options to longer-term pathways. Investigate practical access and lived experience as well as official claims.';
const CATEGORY_DEFAULT_ASSIGNMENTS = {
  housing: PACKAGE_DEFAULT_ASSIGNMENT,
  food: 'Discover realistic ways a person facing food insecurity in Utah County can obtain meals and groceries. Follow useful relationships from coordinating organizations to the specific meal sites, pantries, benefit programs, delivery services, and specialized providers people can actually access. Verify schedules, boundaries, eligibility, and the practical intake path.',
  employment: 'Discover realistic employment resources for people in Utah County who need work, better work, training, or help overcoming barriers to employment. Follow useful relationships from workforce organizations to specific placement programs, employers, training, credentials, apprenticeships, and supported-employment services. Verify costs, eligibility, schedules, and the practical enrollment path.',
};

const MATCH_ASSESSMENT_LABELS = {
  'same-resource': 'Same resource',
  'same-organization-different-program': 'Same organization, different program',
  'related-distinct': 'Related but distinct',
  'not-related': 'Not related',
};

function agentName(agent = state.agent) {
  if (agent?.displayName) return agent.displayName;
  const key = agent?.adapter || agent?.settings?.adapter || document.querySelector('#agent-adapter')?.value;
  return key === 'dsh' ? 'DeepSeek Harness' : key === 'demo' ? 'Built-in demo' : 'Hermes';
}

function updateAdapterFields() {
  const adapter = document.querySelector('#agent-adapter').value;
  document.querySelectorAll('[data-adapter-only]').forEach(field => {
    field.hidden = !field.dataset.adapterOnly.split(',').includes(adapter);
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
  state.latestImport = summary;
  document.querySelector('#package-status-name').textContent = summary.sourceName;
  document.querySelector('#package-status').hidden = false;
  document.querySelector('#file-label').textContent = 'Choose a different package…';
  document.querySelector('#package-details').hidden = false;
  document.querySelector('#package-details-copy').textContent = [
    `Package ${summary.schema.packageVersion || 'version not recorded'}`,
    `schema ${summary.schema.schemaVersion || 'not recorded'}`,
    `${summary.resourceCount} resources`,
    `${(summary.categories || []).length} categories`,
    `imported ${formatWhen(summary.importedAt)}`,
    `SHA-256 ${summary.sourceSha256}`,
  ].join(' · ');
  state.categories = summary.categories || [];
  state.forGroups = summary.forGroups || [];
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
  updateStartResearchState();
}

function activeCategory() {
  return state.categories.find(category => category.id === state.activeCategoryId)
    || { id: 'housing', label: 'Housing', types: [], resourceCount: 0, multiCategoryResourceCount: 0, supported: true };
}

function categoryKey(category = activeCategory()) {
  const id = String(category.id || '').toLowerCase();
  const label = String(category.label || '').toLowerCase();
  return CATEGORY_DEFAULT_ASSIGNMENTS[id] ? id : CATEGORY_DEFAULT_ASSIGNMENTS[label] ? label : id;
}

function packageDefaultAssignment() {
  const category = activeCategory();
  return CATEGORY_DEFAULT_ASSIGNMENTS[categoryKey()] || `Discover realistic ${category.label.toLowerCase()} resources for people in Utah County. Follow useful relationships from coordinating organizations and broad directories to the specific programs, providers, benefits, and practical services people can actually access. Verify eligibility, costs, schedules, service areas, availability, and the real intake or enrollment path.`;
}

function updateCategoryCopy() {
  const category = activeCategory();
  document.querySelector('#research-heading-title').textContent = `Send a research agent on a ${category.label} assignment`;
  document.querySelector('#category-lesson-option').textContent = `${category.label} lesson`;
  const types = category.types?.length ? category.types.join(', ') : 'None defined in this package';
  const forGroups = state.forGroups.length ? state.forGroups.join(', ') : 'None defined in this package';
  document.querySelector('#category-taxonomy-note').textContent = `Types: ${types} · For: ${forGroups}`;
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
  document.querySelector('#agent-setup').hidden = Boolean(agent?.ready || agent?.adapter === 'demo');
  document.querySelector('#agent-setup-title').textContent = agent?.installed ? `Finish ${name} setup` : `Install ${name}`;
  document.querySelector('#agent-setup-detail').textContent = agent?.message || 'Complete the connection setup, then refresh this page.';
  document.querySelector('#copy-setup').dataset.command = agent?.setupCommand || 'hermes setup';
  const settings = agent?.settings || {};
  document.querySelector('#agent-adapter').value = settings.adapter || 'hermes';
  document.querySelector('#hermes-profile').value = settings.hermesProfile || settings.profile || '';
  document.querySelector('#hermes-provider').value = settings.hermesProvider || settings.provider || '';
  document.querySelector('#hermes-model').value = settings.hermesModel || settings.model || '';
  document.querySelector('#hermes-command').value = settings.hermesCommand || settings.command || '';
  document.querySelector('#dsh-model').value = settings.dshModel || '';
  document.querySelector('#dsh-command').value = settings.dshCommand || '';
  document.querySelector('#agent-timeout').value = settings.timeoutSeconds || 900;
  updateAdapterFields();
  updateStartResearchState();
}

function selectedResearchMode() {
  return document.querySelector('input[name="research-mode"]:checked')?.value || 'package';
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
  if (button) button.disabled = !state.agent?.ready || !contextReady;
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

function emptyState(text) {
  const element = document.createElement('div');
  element.className = 'empty-state';
  element.textContent = text;
  return element;
}

function researchRunTitle(run) {
  const category = run.targetCategoryLabel || 'Housing';
  return run.researchMode === 'standalone-location'
    ? `${category} research · ${run.targetLocation}`
    : run.seedResourceId
      ? `${category} research from ${run.prompt?.selectedSeed?.name || run.seedResourceId}`
      : `${category} research`;
}

function candidateCountForRun(runId) {
  return state.discoveries.filter(discovery => discovery.runId === runId).length;
}

function acceptedResourceCountForRun(runId) {
  return state.discoveries.filter(discovery => (
    discovery.runId === runId
    && discovery.status === 'accepted'
    && discovery.generatedResource
  )).length;
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
    time.textContent = `${formatWhen(run.createdAt)} · ${run.adapter} · ${run.researchMode === 'standalone-location' ? 'standalone location' : 'package-backed'}`;
    item.append(head, time);
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
    const viewCandidates = document.createElement('button');
    viewCandidates.type = 'button';
    viewCandidates.className = 'secondary view-candidates';
    viewCandidates.setAttribute('aria-pressed', String(state.candidateRunId === run.id));
    viewCandidates.textContent = `View candidates (${candidateCountForRun(run.id)})`;
    viewCandidates.addEventListener('click', () => selectCandidateRun(run.id, { scroll: true }));
    actions.append(viewCandidates);
    const acceptedResourceCount = acceptedResourceCountForRun(run.id);
    if (run.researchMode === 'package' && acceptedResourceCount) {
      const packageLink = document.createElement('a');
      packageLink.className = 'review-export';
      packageLink.href = `/api/research-runs/${run.id}/resource-package`;
      packageLink.download = '';
      packageLink.textContent = `Export resource package (${acceptedResourceCount})`;
      const packageDetail = document.createElement('small');
      packageDetail.textContent = 'Accepted resources only · no imported resources or PDFs';
      actions.append(packageLink, packageDetail);
    }
    if (['completed', 'partial'].includes(run.status)) {
      const exportLink = document.createElement('a');
      exportLink.className = 'review-export';
      exportLink.href = `/api/research-runs/${run.id}/review-copy`;
      exportLink.download = '';
      exportLink.textContent = 'Export review copy';
      const detail = document.createElement('small');
      detail.textContent = 'This run only · standalone, read-only HTML';
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
  return asText(candidate.serviceNeed || candidate.housingNeed || candidate.description || candidate.resourceType || 'Awaiting review');
}

function matchFieldLabel(value) {
  const field = String(value || 'field').replace(/^relationship:/, '');
  return readableCategory(field).toLowerCase();
}

function primaryMatchExplanation(match) {
  const signal = match?.signals?.[0];
  if (!signal) return `The candidate resembles ${match?.name || 'an imported resource'}.`;
  const percentage = Math.round(signal.strength * 100);
  const candidateField = String(signal.candidateField || '');
  if (['name', 'alias', 'name_variant', 'organization_name', 'program_name'].includes(candidateField)) {
    return `Similar name: ${match.name}. The compared names are ${percentage}% similar.`;
  }
  if (candidateField === 'website') {
    return `Similar website: ${match.name}. The website signal is ${percentage}%.`;
  }
  if (candidateField === 'address') {
    return `Similar address: ${match.name}. The address signal is ${percentage}%.`;
  }
  return `Similar ${matchFieldLabel(candidateField)}: ${match.name}. The signal is ${percentage}%.`;
}

function candidateMatchSummary(discovery) {
  const match = discovery.matchDetails;
  if (!match) return '';
  const assessment = discovery.matchAssessment;
  if (assessment === 'not-related') return `Match reviewed: not related to ${match.name}`;
  if (assessment) return `${MATCH_ASSESSMENT_LABELS[assessment]}: ${match.name}`;
  return `Possible related resource: ${match.name}`;
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
    ? `Candidate inbox · ${researchRunTitle(selectedRun)}`
    : 'Candidate inbox · All runs';
  document.querySelector('#candidate-inbox-context').textContent = selectedRun
    ? selectedRun.researchMode === 'package'
      ? `Showing only candidates associated with research run ${selectedRun.id}. Use its run card to export accepted resources or a review copy for this run.`
      : `Showing only candidates associated with research run ${selectedRun.id}. Use its run card to export a review copy containing this run’s results.`
    : 'Showing candidates from every research run. Choose one run to review or export its results separately.';
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
    status.className = `candidate-status ${discovery.status}`;
    status.textContent = friendlyStatus(discovery.status);
    head.append(name, status);
    const description = document.createElement('p');
    description.textContent = candidateDescription(discovery);
    const run = state.runs.find(entry => entry.id === discovery.runId);
    if (run) {
      const context = document.createElement('small');
      context.className = 'candidate-context';
      context.textContent = run.researchMode === 'standalone-location'
        ? `${run.targetCategoryLabel || 'Housing'} · Standalone research · ${run.targetLocation}`
        : `${run.targetCategoryLabel || 'Housing'} · Package-backed research`;
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
  addCandidateFact(facts, 'Address', candidate.address);
  addCandidateFact(facts, 'Hours', candidate.hours);
  addCandidateFact(facts, 'Website', candidate.website || candidate.url, true);
  if (facts.children.length) profile.append(facts);
  const run = state.runs.find(entry => entry.id === discovery.runId);
  addCandidateSection(
    profile,
    `${run?.targetCategoryLabel || 'Resource'} need`,
    candidate.serviceNeed || candidate.housingNeed,
  );
  addCandidateSection(profile, 'Suggested Types', candidate.recommendedTypes);
  addCandidateSection(profile, 'Suggested For', candidate.recommendedFor);
  addCandidateSection(profile, 'Classification rationale', candidate.classificationRationale);
  addCandidateSection(profile, 'Possible new Types for human review', candidate.suggestedNewTypes);
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

function renderMatchReview(discovery) {
  const panel = document.querySelector('#match-review-panel');
  const match = discovery.matchDetails;
  panel.hidden = !match;
  if (!match) return;
  const assessment = discovery.matchAssessment;
  document.querySelector('#match-review-heading').textContent = assessment
    ? `Relationship recorded: ${MATCH_ASSESSMENT_LABELS[assessment]}`
    : 'Possible relationship to an existing resource';
  document.querySelector('#match-review-detail').textContent = primaryMatchExplanation(match);
  const signals = document.querySelector('#match-review-signals');
  signals.replaceChildren(...(match.signals || []).map(signal => {
    const item = document.createElement('div');
    item.textContent = `Candidate ${matchFieldLabel(signal.candidateField)} “${signal.candidateValue}” compared with imported ${matchFieldLabel(signal.knownField)} “${signal.knownValue}”.`;
    return item;
  }));
  document.querySelectorAll('input[name="match-assessment"]').forEach(input => {
    input.checked = input.value === assessment;
  });
  document.querySelector('#match-assessment-message').textContent = assessment
    ? 'Relationship assessment saved.'
    : '';
}

function renderGeneratedTaxonomy(discovery, resource) {
  const target = document.querySelector('#generated-taxonomy');
  const taxonomy = discovery.taxonomy || { categories: [], forGroups: [], warnings: [] };
  const selectedCategories = new Set(resource.categories || []);
  const selectedTypes = resource.categoryFilters || {};
  const categoryNodes = taxonomy.categories.map(category => {
    const block = document.createElement('div');
    block.className = 'taxonomy-category';
    const categoryLabel = document.createElement('label');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox'; checkbox.dataset.taxonomyCategory = category.id;
    checkbox.checked = selectedCategories.has(category.id);
    const name = document.createElement('strong'); name.textContent = category.label;
    categoryLabel.append(checkbox, name); block.append(categoryLabel);
    if (category.types?.length) {
      const options = document.createElement('div'); options.className = 'taxonomy-options';
      category.types.forEach(type => {
        const option = document.createElement('label');
        const input = document.createElement('input');
        input.type = 'checkbox'; input.dataset.taxonomyTypeCategory = category.id;
        input.value = type; input.checked = (selectedTypes[category.id] || []).includes(type);
        input.disabled = !checkbox.checked;
        option.append(input, document.createTextNode(type)); options.append(option);
      });
      options.hidden = !checkbox.checked;
      checkbox.addEventListener('change', () => {
        options.hidden = !checkbox.checked;
        options.querySelectorAll('input').forEach(input => { input.disabled = !checkbox.checked; });
      });
      block.append(options);
    }
    return block;
  });
  const forHeading = document.createElement('p');
  forHeading.className = 'taxonomy-subheading'; forHeading.textContent = 'For';
  const forOptions = document.createElement('div'); forOptions.className = 'taxonomy-options';
  (taxonomy.forGroups || []).forEach(group => {
    const label = document.createElement('label');
    const input = document.createElement('input');
    input.type = 'checkbox'; input.dataset.taxonomyFor = group;
    input.checked = (resource.forGroups || []).includes(group);
    label.append(input, document.createTextNode(group)); forOptions.append(label);
  });
  target.replaceChildren(...categoryNodes, forHeading, forOptions);
  const warning = document.querySelector('#generated-taxonomy-warning');
  warning.hidden = !(taxonomy.warnings || []).length;
  warning.textContent = (taxonomy.warnings || []).length
    ? `Needs human mapping: ${taxonomy.warnings.join(' ')}` : '';
}

function collectGeneratedTaxonomy() {
  const categories = [...document.querySelectorAll('[data-taxonomy-category]:checked')]
    .map(input => input.dataset.taxonomyCategory);
  const categoryFilters = {};
  categories.forEach(categoryId => {
    const selected = [...document.querySelectorAll(`[data-taxonomy-type-category="${CSS.escape(categoryId)}"]:checked`)]
      .map(input => input.value);
    if (selected.length) categoryFilters[categoryId] = selected;
  });
  const forGroups = [...document.querySelectorAll('[data-taxonomy-for]:checked')]
    .map(input => input.dataset.taxonomyFor);
  return { categories, categoryFilters, forGroups };
}

function renderGeneratedResource(discovery, { open = false } = {}) {
  const panel = document.querySelector('#generated-resource-panel');
  const generated = discovery.generatedResource;
  panel.hidden = !generated;
  if (!generated) {
    panel.open = false;
    return;
  }
  const resource = generated.resource || {};
  document.querySelector('#generated-name').value = resource.name || '';
  document.querySelector('#generated-phone').value = resource.phone || '';
  document.querySelector('#generated-address').value = resource.address || '';
  document.querySelector('#generated-website').value = resource.website || '';
  document.querySelector('#generated-hours').value = resource.hours || '';
  document.querySelector('#generated-verified').value = resource.verifiedOn || '';
  document.querySelector('#generated-description').value = resource.description || '';
  document.querySelector('#generated-information').value = resource.informationText || '';
  const run = state.runs.find(entry => entry.id === discovery.runId);
  document.querySelector('#generated-category-badge').textContent = `${run?.targetCategoryLabel || 'Resource'} · additions package`;
  renderGeneratedTaxonomy(discovery, resource);
  document.querySelector('#generated-resource-message').textContent = discovery.status === 'accepted'
    ? 'Included in this run’s cumulative additions package.'
    : 'Draft retained, but excluded from the package unless this candidate is accepted.';
  if (open) panel.open = true;
}

function openCandidate(discovery) {
  state.currentCandidate = discovery;
  document.querySelector('#candidate-dialog-name').textContent = discovery.name;
  const status = document.querySelector('#candidate-dialog-status');
  status.className = `candidate-status ${discovery.status}`;
  status.textContent = friendlyStatus(discovery.status);
  document.querySelector('#candidate-profile').replaceChildren(renderCandidateProfile(discovery));
  renderGeneratedResource(discovery);
  renderMatchReview(discovery);
  document.querySelector('#review-feedback').value = discovery.reviewFeedback || '';
  const run = state.runs.find(entry => entry.id === discovery.runId);
  document.querySelector('#review-learn-label').textContent = `Save this feedback as an active ${run?.targetCategoryLabel || 'Housing'} research lesson`;
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
document.querySelector('#target-location').addEventListener('input', updateStandaloneAutoAssignment);
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
    state.currentCandidate = result.discovery;
    await loadResearchData();
    if (button.dataset.status === 'accepted' && result.discovery.generatedResource) {
      message.textContent = result.lesson
        ? `Accepted. A TSO Resources draft was created, and your feedback is now an active ${result.discovery.taxonomy ? (state.runs.find(run => run.id === result.discovery.runId)?.targetCategoryLabel || 'Housing') : 'Housing'} lesson.`
        : 'Accepted. A TSO Resources draft was created and added to this run’s cumulative package.';
    } else {
      message.textContent = result.lesson
        ? `Review saved, and your feedback is now an active ${state.runs.find(run => run.id === result.discovery.runId)?.targetCategoryLabel || 'Housing'} lesson.`
        : 'Review saved.';
    }
    const status = document.querySelector('#candidate-dialog-status');
    status.className = `candidate-status ${result.discovery.status}`;
    status.textContent = friendlyStatus(result.discovery.status);
    renderGeneratedResource(result.discovery, { open: button.dataset.status === 'accepted' });
  } catch (error) {
    message.textContent = error.message;
  } finally {
    document.querySelectorAll('#review-actions button').forEach(item => { item.disabled = false; });
  }
});

document.querySelector('#generated-resource-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!state.currentCandidate?.generatedResource) return;
  const button = event.currentTarget.querySelector('button[type="submit"]');
  const message = document.querySelector('#generated-resource-message');
  button.disabled = true;
  message.textContent = 'Saving the generated resource…';
  try {
    const result = await request(`/api/discoveries/${state.currentCandidate.id}/generated-resource`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resource: {
        name: document.querySelector('#generated-name').value,
        phone: document.querySelector('#generated-phone').value,
        address: document.querySelector('#generated-address').value,
        website: document.querySelector('#generated-website').value,
        hours: document.querySelector('#generated-hours').value,
        verifiedOn: document.querySelector('#generated-verified').value,
        description: document.querySelector('#generated-description').value,
        informationText: document.querySelector('#generated-information').value,
        ...collectGeneratedTaxonomy(),
      } }),
    });
    state.currentCandidate = result.discovery;
    await loadResearchData();
    renderGeneratedResource(result.discovery, { open: true });
    document.querySelector('#generated-resource-message').textContent = result.discovery.status === 'accepted'
      ? 'Saved. The updated resource is in this run’s cumulative additions package.'
      : 'Saved as a draft. It will be included only if this candidate is accepted.';
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

document.querySelector('#save-match-assessment').addEventListener('click', async () => {
  if (!state.currentCandidate?.matchDetails) return;
  const selected = document.querySelector('input[name="match-assessment"]:checked');
  const message = document.querySelector('#match-assessment-message');
  if (!selected) {
    message.textContent = 'Choose the relationship that best fits before saving.';
    return;
  }
  const button = document.querySelector('#save-match-assessment');
  button.disabled = true;
  message.textContent = 'Saving the relationship assessment…';
  try {
    const result = await request(`/api/discoveries/${state.currentCandidate.id}/match-assessment`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assessment: selected.value }),
    });
    state.currentCandidate = result.discovery;
    await loadResearchData();
    renderMatchReview(result.discovery);
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

state.assignmentDrafts.package = document.querySelector('#research-assignment').value;
switchResearchMode();
refresh().catch(error => { document.querySelector('#import-message').textContent = error.message; });
