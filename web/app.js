const state = {
  runs: [], discoveries: [], latestImport: null,
  currentCandidate: null, pollTimer: null, researchMode: 'package',
  activeManualRun: null, manualContributions: [], manualConsolidation: null,
  manualIdentityDecisionPending: false,
  manualAssignmentRequest: 0, customManualSources: 0,
  candidateRunId: null, candidateRunSelectionInitialized: false,
  runActionMessages: {}, expandedRunIds: new Set(),
  assignmentDrafts: { package: '', 'standalone-location': '' }, standaloneAutoAssignment: '',
  categories: [], forGroups: [], activeCategoryId: 'housing', categoryAssignmentDrafts: {},
  workflowProgress: null, progressPollTimer: null,
};

const PACKAGE_DEFAULT_ASSIGNMENT = 'Choose a category and location to prepare a focused resource-discovery assignment.';

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
  document.querySelector('#file-label').textContent = 'Choose a different package';
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
    state.candidateRunId = null;
    state.candidateRunSelectionInitialized = false;
  }
  document.querySelector('#research-results').hidden = false;
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
  document.querySelector('#research-heading-title').textContent = `Collect ${category.label} leads from your chats`;
  const standalone = selectedResearchMode() === 'standalone-location';
  document.querySelector('#category-guidance').textContent = standalone
    ? 'Choose a category to focus discovery for this location. Scout provides category-aware guidance without using a resource package.'
    : 'Choose a category to focus the discovery. Scout uses existing resources, Types, For groups, and category-aware guidance from the connected package.';
  const forGroups = state.forGroups.length ? state.forGroups.join(', ') : 'None defined in this package';
  document.querySelector('#category-taxonomy-note').textContent = standalone ? '' : `For: ${forGroups}`;
}

function renderCategoryChooser() {
  const target = document.querySelector('#category-grid');
  const supportedCount = state.categories.filter(category => category.supported).length;
  document.querySelector('#category-supported-count').textContent = `${supportedCount} categories`;
  target.replaceChildren(...state.categories.map(category => {
    const row = document.createElement('div');
    row.className = `category-row${category.supported ? '' : ' disabled'}`;
    const label = document.createElement('label');
    label.className = 'category-select';
    const input = document.createElement('input');
    input.type = 'radio'; input.name = 'research-category'; input.value = category.id;
    input.checked = category.id === state.activeCategoryId;
    input.disabled = !category.supported;
    input.setAttribute('aria-label', `Select ${category.label}`);
    label.append(input);
    const types = document.createElement('details');
    types.className = 'category-types';
    const typesSummary = document.createElement('summary');
    const title = document.createElement('strong'); title.textContent = category.label;
    typesSummary.append(title);
    const typesCopy = document.createElement('p');
    typesCopy.textContent = category.types?.length
      ? category.types.join(', ')
      : 'No types defined in this package.';
    types.append(typesSummary, typesCopy);
    row.append(label, types);
    if (category.supported) input.addEventListener('change', () => {
      selectCategory(category.id).catch(error => {
        document.querySelector('#research-message').textContent = error.message;
      });
    });
    return row;
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
  refreshManualAssignment();
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
}

function friendlyProgressPhase(value) {
  const labels = {
    research: 'Research',
    'ready-for-curation': 'Ready for curation',
    'curation-start': 'Curation',
    'category-assigned': 'Curation',
    'category-completed': 'Curation',
    'curation-heartbeat': 'Curation',
    'curation-completed': 'Curation complete',
    curation: 'Curation',
    'review-file': 'Review file',
    'review-file-built': 'Review file created',
    'waiting-for-feedback': 'Waiting for feedback',
  };
  return labels[value] || String(value || 'Scout progress').replaceAll('-', ' ');
}

function renderScoutProgress(progress) {
  state.workflowProgress = progress;
  const location = progress.locationName || progress.officeName || 'Current office';
  const phaseLabel = friendlyProgressPhase(progress.phase);
  document.querySelector('#scout-progress-title').textContent = `Current work: ${location} — ${phaseLabel}`;
  document.querySelector('#scout-progress-phase').textContent = phaseLabel;
  document.querySelector('#scout-progress-message').textContent = progress.message;
  const metrics = document.querySelector('#scout-progress-metrics');
  metrics.hidden = false;
  document.querySelector('#scout-research-progress').textContent = `${progress.research.completed} of ${progress.research.total} categories`;
  const curationFailures = Number(progress.curation.failed || 0);
  document.querySelector('#scout-curation-progress').textContent = `${progress.curation.completed} of ${progress.curation.total} categories${curationFailures ? ` · ${curationFailures} need attention` : ''}`;

  const next = progress.nextChatgpt;
  const nextPanel = document.querySelector('#next-chatgpt');
  nextPanel.hidden = !next;
  if (next) {
    const category = next.categoryLabel || next.categoryId || 'Next category';
    document.querySelector('#next-chatgpt-category').textContent = `Next ChatGPT research: ${category}`;
    document.querySelector('#next-chatgpt-delay').textContent = `${next.delayMinutes} minute${Number(next.delayMinutes) === 1 ? '' : 's'}`;
    document.querySelector('#next-chatgpt-time').textContent = formatWhen(next.scheduledAt);
    const reason = document.querySelector('#next-chatgpt-reason');
    reason.textContent = next.reason || '';
    reason.hidden = !next.reason;
  }

  const updated = document.querySelector('#scout-progress-updated');
  updated.hidden = !progress.updatedAt;
  updated.textContent = progress.updatedAt ? `Latest update: ${formatWhen(progress.updatedAt)}` : '';

  const review = progress.reviewFile;
  const reviewPanel = document.querySelector('#review-file-ready');
  reviewPanel.hidden = !review;
  if (review) {
    document.querySelector('#review-file-title').textContent = review.status === 'created'
      ? `${review.filename} created`
      : `${review.filename} is ready`;
    const created = review.createdAt ? ` · created ${formatWhen(review.createdAt)}` : '';
    document.querySelector('#review-file-detail').textContent = `${review.categoryCount} curated categories · ${review.resourceCount} proposed resources${created}`;
    const download = document.querySelector('#review-file-download');
    download.href = review.downloadUrl;
    download.download = review.filename;
    download.textContent = `Download ${review.filename}`;
  }
}

async function loadScoutProgress() {
  if (!state.latestImport) return;
  const progress = await request(`/api/scout-progress?importId=${state.latestImport.id}`);
  renderScoutProgress(progress);
}

function selectedResearchMode() {
  return document.querySelector('#standalone-mode')?.checked
    ? 'standalone-location'
    : 'package';
}

function standaloneDefaultAssignment(location) {
  const place = location.trim() || 'the selected location';
  const category = activeCategory();
  return `Discover credible ${category.label} resource leads that a Resource Specialist should investigate for ${place}. Prioritize distinct providers, named programs, and actionable access points. Prefer an official website and state uncertainty rather than inventing missing facts.`;
}

function updateStartResearchState() {
  const mode = selectedResearchMode();
  const contextReady = mode === 'package'
    ? Boolean(state.latestImport && activeCategory().supported)
    : Boolean(document.querySelector('#target-location')?.value.trim());
  const button = document.querySelector('#start-research');
  if (button) button.disabled = !contextReady;
}

function manualAssignmentPayload() {
  const mode = selectedResearchMode();
  return {
    researchMode: mode,
    sourceImportId: mode === 'package' ? state.latestImport?.id : null,
    categoryId: state.activeCategoryId,
    categoryLabel: activeCategory().label,
    targetLocation: mode === 'standalone-location' ? document.querySelector('#target-location').value.trim() : '',
    regionalScope: mode === 'standalone-location' ? document.querySelector('#regional-scope').value.trim() : '',
  };
}

async function refreshManualAssignment() {
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
    if (requestNumber !== state.manualAssignmentRequest) return;
    document.querySelector('#research-assignment').value = result.assignment;
    message.textContent = `${result.context.knownResources.length} existing ${result.context.categoryLabel} resource${result.context.knownResources.length === 1 ? '' : 's'} included as the do-not-repeat list.`;
  } catch (error) {
    if (requestNumber === state.manualAssignmentRequest) message.textContent = error.message;
  }
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
  refreshManualAssignment();
}

function switchResearchMode() {
  const nextMode = selectedResearchMode();
  const assignment = document.querySelector('#research-assignment');
  state.assignmentDrafts[state.researchMode] = assignment.value;
  state.researchMode = nextMode;
  document.querySelector('#standalone-research-fields').hidden = nextMode !== 'standalone-location';
  const locationButton = document.querySelector('#research-location-mode');
  locationButton.textContent = nextMode === 'standalone-location'
    ? 'Use a resource package'
    : 'Research a location';
  locationButton.setAttribute('aria-pressed', String(nextMode === 'standalone-location'));
  if (nextMode === 'package') {
    assignment.value = state.categoryAssignmentDrafts[state.activeCategoryId]
      || state.assignmentDrafts.package || packageDefaultAssignment();
  } else {
    state.standaloneAutoAssignment = standaloneDefaultAssignment(document.querySelector('#target-location').value);
    assignment.value = state.assignmentDrafts['standalone-location'] || state.standaloneAutoAssignment;
  }
  updateCategoryCopy();
  updateStartResearchState();
  refreshManualAssignment();
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
  return `${category} discovery · ${runPlace(run)}`;
}

function candidateCountForRun(runId) {
  return state.discoveries.filter(
    discovery => discovery.runId === runId && !['unavailable', 'unreachable'].includes(discovery.status),
  ).length;
}

function effectiveRunPackageContentSha256(run) {
  return run.reconciliation?.targetPackage?.contentSha256 || run.sourcePackageContentSha256 || '';
}

function hasNewPackageForRun(run) {
  return Boolean(
    run.status === 'completed'
    && run.researchMode === 'package'
    && state.latestImport?.contentSha256
    && state.latestImport.contentSha256 !== effectiveRunPackageContentSha256(run),
  );
}

function missingWebsiteCandidatesForRun(runId) {
  return state.discoveries.filter(discovery => {
    if (discovery.runId !== runId || ['unavailable', 'unreachable'].includes(discovery.status)) return false;
    const candidate = discovery.candidate || {};
    return !asText(candidate.website || candidate.url) && !candidate.contactLookup;
  });
}

function excludedLeadsForRun(runId) {
  return state.discoveries.filter(
    discovery => discovery.runId === runId && ['unavailable', 'unreachable'].includes(discovery.status),
  );
}

function renderExcludedLeads(runId) {
  const excluded = excludedLeadsForRun(runId);
  if (!excluded.length) return null;
  const details = document.createElement('details');
  details.className = 'excluded-leads';
  const summary = document.createElement('summary');
  summary.textContent = `${excluded.length} excluded lead${excluded.length === 1 ? '' : 's'} retained in Scout`;
  const list = document.createElement('ul');
  excluded.forEach(discovery => {
    const item = document.createElement('li');
    const name = document.createElement('strong');
    name.textContent = discovery.candidate?.presentationName || discovery.name;
    const lookup = discovery.candidate?.contactLookup || {};
    const note = document.createElement('span');
    const outcome = discovery.status === 'unreachable' ? 'Unreachable' : 'Confirmed closed or ended';
    note.textContent = `${outcome}: ${lookup.note || 'Documented during website lookup.'}`;
    item.append(name, note);
    const href = safeHref(asText(lookup.sourceUrl));
    if (href) {
      const link = document.createElement('a');
      link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer';
      link.textContent = 'View source';
      item.append(link);
    }
    list.append(item);
  });
  details.append(summary, list);
  return details;
}

function manualRunActionLabel(run) {
  return run.manualProgress?.contributionCount
    ? 'Review responses and leads'
    : 'Collect responses';
}

function selectCandidateRun(runId, { scroll = false } = {}) {
  state.candidateRunId = runId;
  state.candidateRunSelectionInitialized = true;
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
    const item = document.createElement('details');
    item.className = 'run';
    item.open = run.status === 'running' || state.expandedRunIds.has(run.id);
    item.addEventListener('toggle', () => {
      if (item.open) state.expandedRunIds.add(run.id);
      else state.expandedRunIds.delete(run.id);
    });
    const summary = document.createElement('summary');
    summary.className = 'run-summary';
    const title = document.createElement('strong');
    title.textContent = run.targetCategoryLabel || 'Resource';
    const separator = document.createElement('span');
    separator.className = 'run-summary-separator';
    separator.textContent = '·';
    separator.setAttribute('aria-hidden', 'true');
    const status = document.createElement('span');
    status.className = `run-summary-status ${run.status}`;
    status.textContent = friendlyStatus(run.status);
    summary.append(title, separator, status);
    const body = document.createElement('div');
    body.className = 'run-body';
    const time = document.createElement('small');
    const duration = formatDuration(run);
    time.textContent = `${formatWhen(run.createdAt)}${duration ? ` · Duration ${duration}` : ''} · chat sources · ${run.researchMode === 'standalone-location' ? 'standalone location' : 'package-backed'}`;
    body.append(time);
    const progress = document.createElement('div');
    progress.className = 'run-progress';
    const received = run.manualProgress?.contributionCount || 0;
    const leads = run.manualProgress?.leadCount || 0;
    const errors = run.manualProgress?.errorContributionCount || 0;
    progress.textContent = `${received} response${received === 1 ? '' : 's'} received · ${leads} parsed lead${leads === 1 ? '' : 's'}${errors ? ` · ${errors} needs correction` : ''}`;
    body.append(progress);
    if (run.reconciliation) {
      const reconciliation = document.createElement('div');
      reconciliation.className = 'run-reconciliation';
      const result = run.reconciliation.result;
      reconciliation.textContent = `Compared with ${run.reconciliation.targetPackage.sourceName}: ${result.knownCategoryResourceCount} existing ${run.targetCategoryLabel || 'category'} resource${result.knownCategoryResourceCount === 1 ? '' : 's'} · ${result.alreadyKnownCount} likely already included · ${result.possibleRelationshipCount} possible relationship${result.possibleRelationshipCount === 1 ? '' : 's'}.`;
      body.append(reconciliation);
    }
    const actions = document.createElement('div');
    actions.className = 'run-actions';
    const actionStatus = document.createElement('span');
    actionStatus.className = 'run-action-status';
    actionStatus.setAttribute('aria-live', 'polite');
    const savedActionMessage = state.runActionMessages[run.id];
    if (savedActionMessage) {
      actionStatus.textContent = savedActionMessage.text;
      actionStatus.classList.toggle('error', savedActionMessage.kind === 'error');
    }
    const showActionMessage = (text, kind = '') => {
      state.runActionMessages[run.id] = { text, kind };
      actionStatus.textContent = text;
      actionStatus.classList.toggle('error', kind === 'error');
    };
    if (run.status === 'running') {
      const openManual = document.createElement('button');
      openManual.type = 'button';
      openManual.className = 'secondary view-manual-run';
      openManual.textContent = manualRunActionLabel(run);
      openManual.addEventListener('click', () => openManualDiscoveryRun(run.id));
      actions.append(openManual);
    }
    if (run.status === 'completed') {
        const missingWebsites = missingWebsiteCandidatesForRun(run.id);
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
        actions.append(viewCandidates);
        const hasNewPackage = hasNewPackageForRun(run);
        if (hasNewPackage && missingWebsites.length && !savedActionMessage) {
          actionStatus.textContent = `${missingWebsites.length} candidate${missingWebsites.length === 1 ? '' : 's'} need website lookup before Scout compares this discovery with the newly connected package.`;
        }
        if (missingWebsites.length) {
          const lookupLink = document.createElement('a');
          lookupLink.className = 'review-export';
          lookupLink.href = `/api/research-runs/${run.id}/contact-lookup`;
          lookupLink.download = '';
          lookupLink.textContent = `Export website lookup (${missingWebsites.length})`;
          actions.append(lookupLink);
          const importLookup = document.createElement('button');
          importLookup.type = 'button';
          importLookup.className = 'secondary';
          importLookup.textContent = 'Import website results';
          const importFile = document.createElement('input');
          importFile.type = 'file';
          importFile.accept = '.json,application/json';
          importFile.hidden = true;
          importLookup.addEventListener('click', () => importFile.click());
          importFile.addEventListener('change', async () => {
            const file = importFile.files?.[0];
            if (!file) return;
            importLookup.disabled = true;
            importLookup.textContent = 'Importing…';
            showActionMessage(`Checking ${file.name}…`);
            try {
              const payload = JSON.parse(await file.text());
              const result = await request(`/api/research-runs/${run.id}/contact-lookup`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
              });
              showActionMessage(`${file.name} applied: ${result.verifiedContactCount} updated, ${result.unavailableCount} closed or ended, ${result.unreachableCount} unreachable, ${result.unresolvedCount} unresolved.`);
              await loadResearchData();
            } catch (error) {
              showActionMessage(`${file.name} was not imported: ${error.message}`, 'error');
              importLookup.disabled = false;
              importLookup.textContent = 'Import website results';
            } finally {
              importFile.value = '';
            }
          });
          actions.append(importLookup, importFile);
        }
        if (hasNewPackage && !missingWebsites.length) {
          const reconcile = document.createElement('button');
          reconcile.type = 'button';
          reconcile.className = 'secondary';
          reconcile.textContent = 'Reconcile with current package';
          reconcile.addEventListener('click', async () => {
            reconcile.disabled = true;
            reconcile.textContent = 'Reconciling…';
            showActionMessage(`Comparing candidates with ${state.latestImport.sourceName}…`);
            try {
              const result = await request(`/api/research-runs/${run.id}/reconcile`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ importId: state.latestImport.id }),
              });
              showActionMessage(`Compared ${result.candidateCount} candidates: ${result.alreadyKnownCount} likely already included, ${result.possibleRelationshipCount} possible relationships, ${result.unmatchedCount} unmatched. Export a new Resource Curator.`);
              await loadResearchData();
            } catch (error) {
              showActionMessage(`Reconciliation failed: ${error.message}`, 'error');
              reconcile.disabled = false;
              reconcile.textContent = 'Reconcile with current package';
            }
          });
          actions.append(reconcile);
        }
        actions.append(exportLink);
    }
    body.append(actions, actionStatus);
    const excluded = renderExcludedLeads(run.id);
    if (excluded) body.append(excluded);
    item.append(summary, body);
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
      const response = {
        sourceLabel: source,
        rawText: textarea.value,
        filename: textarea.dataset.filename || contribution?.filename || '',
      };
      if (run.id) {
        await request(`/api/manual-discovery-runs/${run.id}/contributions`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(response),
        });
        await openManualDiscoveryRun(run.id);
      } else {
        const result = await request('/api/manual-discovery-runs/initial-contribution', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...run.setupPayload, initialContribution: response }),
        });
        await loadResearchData();
        await openManualDiscoveryRun(result.run.id);
      }
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
    const locked = state.activeManualRun.status !== 'running';
    const pendingSuggestions = consolidation.suggestions.filter(item => item.status === 'pending');
    const reviewedSuggestions = consolidation.suggestions.filter(item => item.status !== 'pending');
    const heading = document.createElement('div');
    heading.className = 'manual-suggestion-intro';
    const title = document.createElement('h4');
    title.textContent = locked
      ? `Possible relationships retained · ${pendingSuggestions.length}`
      : `Identity review · ${pendingSuggestions.length} pending`;
    const copy = document.createElement('p');
    copy.textContent = locked
      ? 'Scout kept these leads separate and included the possible relationships in Curator. No further action is required here.'
      : 'Optional: merge a pair only when the submitted identity is clear. Unreviewed pairs stay separate and travel to Curator as possible-related context.';
    heading.append(title, copy);
    if (!locked && pendingSuggestions.length > 1) {
      const leaveAll = document.createElement('button');
      leaveAll.type = 'button';
      leaveAll.className = 'secondary';
      leaveAll.textContent = `Leave all ${pendingSuggestions.length} pending pairs unresolved`;
      leaveAll.disabled = state.activeManualRun.status !== 'running' || state.manualIdentityDecisionPending;
      leaveAll.addEventListener('click', async () => {
        if (state.manualIdentityDecisionPending) return;
        if (!window.confirm('Keep every pending pair separate and mark the identity relationship unresolved? You can still revise individual decisions before finishing discovery.')) return;
        state.manualIdentityDecisionPending = true;
        suggestionsTarget.querySelectorAll('button').forEach(item => { item.disabled = true; });
        leaveAll.textContent = 'Saving unresolved choices…';
        document.querySelector('#manual-discovery-message').textContent = 'Saving unresolved identity choices…';
        try {
          state.manualConsolidation = await request(`/api/manual-discovery-runs/${state.activeManualRun.id}/leave-pending-unresolved`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
          });
          state.manualIdentityDecisionPending = false;
          renderManualDiscoveryWorkspace();
          document.querySelector('#manual-discovery-message').textContent = 'All remaining identity pairs were saved as unresolved.';
        } catch (error) {
          state.manualIdentityDecisionPending = false;
          document.querySelector('#manual-discovery-message').textContent = error.message;
          renderManualDiscoveryWorkspace();
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
      if (!locked) {
        for (const [decision, label] of [['same', 'Same identity'], ['separate', 'Keep separate'], ['unresolved', 'Leave unresolved']]) {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'secondary';
          button.textContent = label;
          button.setAttribute('aria-pressed', String(suggestion.status === decision));
          button.disabled = state.manualIdentityDecisionPending;
          button.addEventListener('click', async () => {
          if (state.manualIdentityDecisionPending) return;
          state.manualIdentityDecisionPending = true;
          suggestionsTarget.querySelectorAll('button').forEach(item => { item.disabled = true; });
          actions.querySelectorAll('button').forEach(item => {
            item.setAttribute('aria-pressed', String(item === button));
          });
          const saving = document.createElement('span');
          saving.className = 'manual-choice-status';
          saving.setAttribute('role', 'status');
          saving.textContent = `Saving “${label}”…`;
          actions.append(saving);
          document.querySelector('#manual-discovery-message').textContent = 'Saving identity choice…';
          try {
            state.manualConsolidation = await request(`/api/manual-discovery-runs/${state.activeManualRun.id}/identity-decision`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                leftKey: suggestion.leftKey,
                rightKey: suggestion.rightKey,
                decision,
              }),
            });
            state.manualIdentityDecisionPending = false;
            renderManualDiscoveryWorkspace();
            const remaining = state.manualConsolidation.funnel.pendingIdentityDecisions;
            document.querySelector('#manual-discovery-message').textContent = `Choice saved. ${remaining} identity pair${remaining === 1 ? '' : 's'} remain.`;
          } catch (error) {
            state.manualIdentityDecisionPending = false;
            document.querySelector('#manual-discovery-message').textContent = error.message;
            renderManualDiscoveryWorkspace();
          }
          });
          actions.append(button);
        }
      }
      card.append(pair, reason);
      if (!locked) card.append(actions);
      return card;
    };
    const pendingCards = pendingSuggestions.map(renderSuggestion);
    const children = [heading];
    if (!pendingCards.length) children.push(emptyState('No identity pairs are waiting for a decision.'));
    if (locked && pendingCards.length) {
      const retained = document.createElement('details');
      retained.className = 'manual-reviewed-identities';
      const summary = document.createElement('summary');
      summary.textContent = `Inspect ${pendingCards.length} possible relationship${pendingCards.length === 1 ? '' : 's'}`;
      retained.append(summary, ...pendingCards);
      children.push(retained);
    } else {
      children.push(...pendingCards);
    }
    if (reviewedSuggestions.length) {
      const reviewed = document.createElement('details');
      reviewed.className = 'manual-reviewed-identities';
      const summary = document.createElement('summary');
      summary.textContent = locked
        ? `Inspect ${reviewedSuggestions.length} recorded identity decision${reviewedSuggestions.length === 1 ? '' : 's'}`
        : `Review or change ${reviewedSuggestions.length} recorded identity decision${reviewedSuggestions.length === 1 ? '' : 's'}`;
      reviewed.append(summary, ...reviewedSuggestions.map(renderSuggestion));
      children.push(reviewed);
    }
    suggestionsTarget.replaceChildren(...children);
  }
  document.querySelector('#manual-group-summary').textContent = `Inspect ${consolidation.groups.length} consolidated identity group${consolidation.groups.length === 1 ? '' : 's'}`;
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
  const nextStep = document.querySelector('#manual-next-step');
  if (locked) {
    nextStep.textContent = 'Discovery is finished. Close this view, then export its Resource Curator from Recent runs.';
  } else if (progress.errorContributionCount) {
    nextStep.textContent = 'Next: Correct or remove the response marked as needing attention.';
  } else if (state.manualConsolidation) {
    nextStep.textContent = 'Next: Optionally review the possible relationships, then select Finish discovery.';
  } else if ((progress.contributionCount || 0) >= 4) {
    nextStep.textContent = 'Next: Select Consolidate leads. Scout will combine repeated leads and flag possible relationships.';
  } else if (progress.contributionCount) {
    nextStep.textContent = 'Next: Add another response, or select Consolidate leads if you have enough sources.';
  } else {
    nextStep.textContent = 'Next: Paste a chat response into a source card and select Validate and save.';
  }
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
  finish.disabled = !state.manualConsolidation || Boolean(progress.errorContributionCount);
}

async function openManualDiscoveryRun(runId) {
  const result = await request(`/api/manual-discovery-runs/${runId}/contributions`);
  state.activeManualRun = result.run;
  state.manualContributions = result.contributions;
  state.manualConsolidation = result.consolidation;
  renderManualDiscoveryWorkspace();
  const dialog = document.querySelector('#manual-discovery-dialog');
  if (!dialog.open) dialog.showModal();
  if (result.consolidation) {
    requestAnimationFrame(() => document.querySelector('#manual-consolidation').scrollIntoView({ block: 'start' }));
  }
}

function openManualDiscoverySetup(payload) {
  state.activeManualRun = {
    id: null,
    status: 'running',
    assignment: payload.assignment,
    researchMode: payload.researchMode,
    targetLocation: payload.targetLocation,
    sourceOfficeName: state.latestImport?.officeName || '',
    sourceServiceArea: state.latestImport?.serviceArea || '',
    targetCategoryId: payload.categoryId,
    targetCategoryLabel: payload.categoryLabel,
    manualProgress: { contributionCount: 0, leadCount: 0, errorContributionCount: 0 },
    setupPayload: payload,
  };
  state.manualContributions = [];
  state.manualConsolidation = null;
  renderManualDiscoveryWorkspace();
  document.querySelector('#manual-discovery-dialog').showModal();
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
  const activeDiscoveries = state.discoveries.filter(
    discovery => !['unavailable', 'unreachable'].includes(discovery.status),
  );
  all.textContent = `All resource candidates (${activeDiscoveries.length})`;
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
    ? activeDiscoveries.filter(discovery => discovery.runId === selectedRun.id)
    : activeDiscoveries;
  document.querySelector('#candidate-count').textContent = discoveries.length;
  document.querySelector('#candidate-inbox-title').textContent = selectedRun
    ? `Resource candidates · ${researchRunTitle(selectedRun)}`
    : `Resource candidates · ${state.latestImport?.officeName || 'current package'}`;
  document.querySelector('#candidate-inbox-context').textContent = selectedRun
    ? `Showing resource candidates from ${researchRunTitle(selectedRun)}.`
    : `Showing resource candidates from every research run for ${state.latestImport?.sourceName || 'the current package'}.`;
  if (!discoveries.length) {
    target.replaceChildren(emptyState(selectedRun
      ? 'No resource candidates have been saved for this research run yet.'
      : 'Resource candidates will appear here after Scout finishes a category.'));
    return;
  }
  target.replaceChildren(...discoveries.map(discovery => {
    const item = document.createElement('div');
    item.className = 'candidate';
    item.tabIndex = 0;
    const head = document.createElement('div');
    head.className = 'candidate-head';
    const name = document.createElement('strong');
    name.textContent = discovery.candidate?.presentationName || discovery.name;
    const status = document.createElement('span');
    status.className = 'candidate-status';
    status.textContent = 'Resource candidate';
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
  if (candidate.contactLookup?.status === 'unresolved') {
    addCandidateSection(
      profile,
      'Contact lookup remains unresolved',
      [candidate.contactLookup.note, ...(candidate.contactLookup.suggestedNextSteps || [])],
    );
  }

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
  document.querySelector('#candidate-dialog-name').textContent = discovery.candidate?.presentationName || discovery.name;
  const status = document.querySelector('#candidate-dialog-status');
  status.className = 'candidate-status';
  status.textContent = 'Resource candidate';
  document.querySelector('#candidate-profile').replaceChildren(renderCandidateProfile(discovery));
  document.querySelector('#candidate-json').textContent = JSON.stringify(discovery.candidate, null, 2);
  document.querySelector('#candidate-dialog').showModal();
}

async function loadResearchData() {
  if (!state.latestImport) {
    state.runs = [];
    state.discoveries = [];
    renderCandidates();
    return;
  }
  const scope = `?importId=${state.latestImport.id}`;
  const [runs, discoveries] = await Promise.all([
    request(`/api/research-runs${scope}`), request(`/api/discoveries${scope}`),
  ]);
  state.runs = runs.runs;
  state.discoveries = discoveries.discoveries;
  if (!state.candidateRunSelectionInitialized) {
    const latestWithCandidates = state.runs.find(run => candidateCountForRun(run.id) > 0);
    state.candidateRunId = latestWithCandidates?.id ?? null;
    state.candidateRunSelectionInitialized = true;
  } else if (state.candidateRunId != null && !state.runs.some(run => run.id === state.candidateRunId)) {
    state.candidateRunId = null;
  }
  renderCandidates();
}

async function refresh() {
  const status = await request('/api/status');
  if (status.version) document.querySelector('#app-version').textContent = `v${status.version}`;
  showAccess(status.access);
  if (status.latestImport) {
    showImport(status.latestImport);
  } else {
    state.latestImport = null;
  }
  await Promise.all([loadResearchData(), loadScoutProgress()]);
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
    await Promise.all([loadResearchData(), loadScoutProgress()]);
    message.textContent = `${result.import.sourceName} connected. Scout read a private copy and did not change your ZIP.`;
  } catch (error) {
    message.className = 'message error';
    message.textContent = error.message;
    document.querySelector('#file-label').textContent = state.latestImport
      ? 'Choose a different package' : 'Choose resource package';
  } finally {
    chooser.classList.remove('busy');
    input.value = '';
  }
}

document.querySelector('#package-input').addEventListener('change', () => {
  importSelectedPackage();
});

document.querySelector('#import-form').addEventListener('submit', event => event.preventDefault());

document.querySelector('#close-candidate').addEventListener('click', () => document.querySelector('#candidate-dialog').close());
document.querySelector('#close-manual-discovery').addEventListener('click', () => {
  document.querySelector('#manual-discovery-dialog').close();
  if (!state.activeManualRun?.id) {
    state.activeManualRun = null;
    state.manualContributions = [];
    state.manualConsolidation = null;
    document.querySelector('#scout-progress-message').textContent = 'Discovery setup closed. No discovery was started.';
  }
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
      ? `Consolidation ready. ${state.manualConsolidation.funnel.pendingIdentityDecisions} possible relationship${state.manualConsolidation.funnel.pendingIdentityDecisions === 1 ? '' : 's'} will remain separate and travel to Curator unless you optionally review them.`
      : 'Consolidation ready. No ambiguous identity pairs remain.';
  } catch (error) {
    message.textContent = error.message;
    event.currentTarget.disabled = false;
  }
});

document.querySelector('#finish-manual-discovery').addEventListener('click', async event => {
  const run = state.activeManualRun;
  if (!run) return;
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
    document.querySelector('#manual-discovery-dialog').close();
    state.activeManualRun = null;
    state.manualContributions = [];
    state.manualConsolidation = null;
    document.querySelector('#scout-progress-message').textContent = 'Discovery finished. Its resource candidates are available in section 03.';
  } catch (error) {
    message.textContent = error.message;
    event.currentTarget.disabled = false;
  }
});

document.querySelector('#candidate-run-filter').addEventListener('change', event => {
  selectCandidateRun(event.target.value ? Number(event.target.value) : null);
});

refresh().catch(error => { document.querySelector('#import-message').textContent = error.message; });
state.progressPollTimer = window.setInterval(() => {
  loadScoutProgress().catch(error => {
    document.querySelector('#scout-progress-message').textContent = error.message;
  });
}, 15000);
