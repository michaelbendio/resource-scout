'use strict';

(function (root) {
  const MATCH_LABELS = {
    'same-resource': 'Same resource',
    'same-organization-different-program': 'Same organization, different program',
    'related-distinct': 'Related but distinct',
    'not-related': 'Not related',
  };

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function asText(value) {
    if (value == null) return '';
    if (Array.isArray(value)) return value.map(asText).filter(Boolean).join('\n');
    if (typeof value === 'object') return value.name || value.label || value.value || JSON.stringify(value);
    return String(value).trim();
  }

  function checklistItems(notes) {
    const items = [];
    String(notes || '').split(/\r?\n/).forEach((line, lineIndex) => {
      const match = line.match(/^\s*[-*]\s+\[([ xX])\]\s+(.*)$/);
      if (match) items.push({ lineIndex, checked: match[1].toLocaleLowerCase() === 'x', text: match[2] });
    });
    return items;
  }

  function toggleChecklistItem(notes, lineIndex, checked) {
    const lines = String(notes || '').split(/\r?\n/);
    if (lineIndex < 0 || lineIndex >= lines.length) return String(notes || '');
    lines[lineIndex] = lines[lineIndex].replace(
      /^(\s*[-*]\s+)\[[ xX]\]/,
      `$1[${checked ? 'x' : ' '}]`,
    );
    return lines.join('\n');
  }

  function friendly(value) {
    return String(value || '').replaceAll('-', ' ');
  }

  function slug(value) {
    return String(value || '').toLocaleLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'resources';
  }

  function categoryLabel(category) {
    return asText(category?.label || category?.name || category?.id) || 'Category';
  }

  function initialTaxonomyDraft(review) {
    const categoryTypes = {};
    (review.sourcePackage?.categorySummaries || []).forEach(category => {
      categoryTypes[String(category.id)] = Array.isArray(category.types)
        ? [...new Set(category.types.map(asText).filter(Boolean))]
        : [];
    });
    return {
      categoryTypes,
      forGroups: [...new Set((review.sourcePackage?.forGroups || []).map(asText).filter(Boolean))],
      modifiedCategoryIds: [],
      updatedAt: null,
    };
  }

  function normalizeTaxonomyDraft(review, value) {
    const fallback = initialTaxonomyDraft(review);
    if (!value || typeof value !== 'object') return fallback;
    const categoryTypes = {};
    Object.keys(fallback.categoryTypes).forEach(id => {
      const values = value.categoryTypes?.[id];
      categoryTypes[id] = Array.isArray(values)
        ? [...new Set(values.map(asText).filter(Boolean))]
        : fallback.categoryTypes[id];
    });
    return {
      categoryTypes,
      forGroups: Array.isArray(value.forGroups)
        ? [...new Set(value.forGroups.map(asText).filter(Boolean))]
        : fallback.forGroups,
      modifiedCategoryIds: Array.isArray(value.modifiedCategoryIds)
        ? [...new Set(value.modifiedCategoryIds.map(String))].filter(id => Object.hasOwn(categoryTypes, id))
        : [],
      updatedAt: asText(value.updatedAt) || null,
    };
  }

  function packageCategories(review, taxonomyDraft, categoryIds, now) {
    const rawCategories = review.sourcePackage?.categories || [];
    return categoryIds.map(id => {
      const raw = rawCategories.find(category => String(category.id) === String(id));
      if (!raw) return null;
      const category = clone(raw);
      category.filters = clone(taxonomyDraft.categoryTypes[String(id)] || []);
      if (taxonomyDraft.modifiedCategoryIds.includes(String(id))) category.lastModified = taxonomyDraft.updatedAt || now;
      return category;
    }).filter(Boolean);
  }

  function initialState(review) {
    const candidates = {};
    review.candidates.forEach(item => {
      candidates[item.id] = {
        packageStatus: 'pending',
        packageHistory: [],
        sourceNotes: asText(item.notes),
        curatorNotes: asText(item.notes),
        matchAssessment: item.matchAssessment || '',
        updatedAt: item.updatedAt || review.exportedAt,
        resourceDraft: item.resourceDraft ? clone(item.resourceDraft) : null,
        pdfAssets: {},
      };
    });
    return {
      curatorWorkSchemaVersion: 1,
      reviewCopySchemaVersion: review.reviewCopySchemaVersion,
      reviewId: review.reviewId,
      sourceSha256: review.sourcePackage?.sourceSha256 || null,
      run: {
        id: review.run.id,
        categoryId: review.run.targetCategoryId,
        categoryLabel: review.run.targetCategoryLabel,
      },
      taxonomyDraft: initialTaxonomyDraft(review),
      packagedCandidateIds: [],
      reviewerName: '',
      updatedAt: review.exportedAt,
      candidates,
    };
  }

  function validateFeedback(review, feedback) {
    if (!feedback || feedback.curatorWorkSchemaVersion !== 1) throw new Error('This is not a supported Curator work file.');
    if (feedback.reviewId !== review.reviewId) throw new Error('This feedback belongs to a different review copy.');
    if ((feedback.sourceSha256 || null) !== (review.sourcePackage?.sourceSha256 || null)) throw new Error('The source package does not match this review copy.');
    const expected = review.candidates.map(item => String(item.id)).sort();
    const received = Object.keys(feedback.candidates || {}).map(String).sort();
    if (JSON.stringify(received) !== JSON.stringify(expected)) {
      throw new Error('The candidate list does not match this review copy.');
    }
    const restored = initialState(review);
    Object.assign(restored, clone(feedback));
    restored.curatorWorkSchemaVersion = 1;
    restored.candidates = initialState(review).candidates;
    const packaged = Array.isArray(feedback.packagedCandidateIds)
      ? [...new Set(feedback.packagedCandidateIds.map(String))].sort()
      : [];
    if (packaged.some(id => !expected.includes(id))) throw new Error('The candidate list does not match this review copy.');
    restored.packagedCandidateIds = packaged;
    restored.taxonomyDraft = normalizeTaxonomyDraft(review, restored.taxonomyDraft);
    review.candidates.forEach(item => {
      const sourceState = feedback.candidates?.[item.id];
      const itemState = restored.candidates[item.id];
      if (sourceState && typeof sourceState === 'object') Object.assign(itemState, clone(sourceState));
      itemState.packageStatus = ['pending', 'ready', 'packaged'].includes(itemState.packageStatus)
        ? itemState.packageStatus
        : 'pending';
      itemState.packageHistory = Array.isArray(itemState.packageHistory) ? itemState.packageHistory : [];
      if (packaged.includes(String(item.id))) itemState.packageStatus = 'packaged';
      if (typeof itemState.curatorNotes !== 'string') {
        itemState.curatorNotes = asText(itemState.sourceNotes || item.notes);
      }
      if (!itemState.pdfAssets || typeof itemState.pdfAssets !== 'object') itemState.pdfAssets = {};
    });
    return restored;
  }

  function validateDraft(review, item, itemState, taxonomyValue = null) {
    const errors = [];
    const resource = itemState.resourceDraft;
    const source = review.sourcePackage;
    if (!resource) return ['The ready candidate does not have a resource draft.'];
    if (!asText(resource.name)) errors.push('Name is required.');
    const taxonomyDraft = normalizeTaxonomyDraft(review, taxonomyValue);
    const summaries = source?.categorySummaries || [];
    const categoryMap = new Map(summaries.map(category => [String(category.id), category]));
    const categories = Array.isArray(resource.categories) ? [...new Set(resource.categories.map(String))] : [];
    if (!categories.length) errors.push('Select at least one category.');
    categories.forEach(id => {
      if (!categoryMap.has(id)) errors.push(`Category “${id}” is not in the source package.`);
    });
    const filters = resource.categoryFilters && typeof resource.categoryFilters === 'object' ? resource.categoryFilters : {};
    Object.entries(filters).forEach(([id, values]) => {
      if (!categories.includes(id)) errors.push(`Types are selected for unassigned category “${id}”.`);
      const allowed = new Set(taxonomyDraft.categoryTypes[id] || []);
      (Array.isArray(values) ? values : []).forEach(value => {
        if (!allowed.has(value)) errors.push(`Type “${value}” is not defined for ${categoryLabel(categoryMap.get(id) || { id })}.`);
      });
    });
    const allowedFor = new Set(taxonomyDraft.forGroups);
    (Array.isArray(resource.forGroups) ? resource.forGroups : []).forEach(value => {
      if (!allowedFor.has(value)) errors.push(`For label “${value}” is not in the source package.`);
    });
    const verified = asText(resource.verifiedOn);
    if (verified && !/^(?:0[1-9]|1[0-2])\/\d{2}$/.test(verified)) errors.push('Verified must use MM/YY or remain blank.');
    if (item.knownResourceMatch && !itemState.matchAssessment) errors.push('Assess the possible relationship to the existing resource.');
    if (itemState.matchAssessment === 'same-resource') errors.push('A candidate marked as the same resource cannot be added as a new resource.');
    return errors;
  }

  function buildResourcePackage(review, state, now = new Date().toISOString()) {
    const errors = [];
    const source = review.sourcePackage;
    if (!source?.packageEligible) errors.push('This review copy cannot create a resource package.');
    const acceptedItems = review.candidates.filter(item => state.candidates?.[item.id]?.packageStatus === 'ready');
    if (!acceptedItems.length) errors.push('Mark at least one candidate Ready for package before downloading a resource package.');
    const taxonomyDraft = normalizeTaxonomyDraft(review, state.taxonomyDraft);
    acceptedItems.forEach(item => {
      validateDraft(review, item, state.candidates[item.id], taxonomyDraft)
        .forEach(error => errors.push(`${item.name}: ${error}`));
    });
    if (errors.length) return { errors, data: null, resources: [] };

    const resources = acceptedItems.map(item => clone(state.candidates[item.id].resourceDraft));
    const categoryIds = [...new Set([
      ...resources.flatMap(resource => resource.categories || []),
      ...taxonomyDraft.modifiedCategoryIds,
    ])];
    const categories = packageCategories(review, taxonomyDraft, categoryIds, now);
    const packageVersionText = String(source.packageVersion ?? 'Unknown');
    const packageVersion = /^\d+$/.test(packageVersionText) ? Number(packageVersionText) : packageVersionText;
    const lastModified = [
      ...resources.map(resource => asText(resource.lastModified)),
      asText(taxonomyDraft.updatedAt),
    ].filter(Boolean).sort().at(-1) || now;
    const referencedPDFs = new Set(resources.flatMap(resource => (resource.pdfs || []).map(pdf => pdf.path).filter(Boolean)));
    const pdfAssets = {};
    acceptedItems.forEach(item => {
      Object.entries(state.candidates[item.id].pdfAssets || {}).forEach(([path, asset]) => {
        if (referencedPDFs.has(path)) pdfAssets[path] = clone(asset);
      });
    });
    return {
      errors: [],
      candidateIds: acceptedItems.map(item => String(item.id)),
      resources,
      pdfAssets,
      data: {
        resourcePackageSchemaVersion: source.resourcePackageSchemaVersion,
        packageVersion,
        packageCreatedAt: now,
        lastModified,
        categories,
        categoryMigrations: [],
        forGroups: clone(taxonomyDraft.forGroups),
        resources,
        changes: [],
        deletionRequests: [],
        deletions: [],
      },
    };
  }

  function archivePackagedCandidates(review, state, built, now = new Date().toISOString()) {
    const knownIds = new Set(review.candidates.map(item => String(item.id)));
    const packaged = new Set((state.packagedCandidateIds || []).map(String));
    let count = 0;
    [...new Set((built.candidateIds || []).map(String))].forEach((id, index) => {
      if (!knownIds.has(id) || !Object.hasOwn(state.candidates || {}, id)) return;
      const itemState = state.candidates[id];
      const resource = built.resources?.[index];
      itemState.packageStatus = 'packaged';
      itemState.packageHistory ||= [];
      itemState.packageHistory.push({
        packagedAt: now,
        resourceId: asText(resource?.id),
        resourceName: asText(resource?.name),
      });
      itemState.updatedAt = now;
      packaged.add(id);
      count += 1;
    });
    state.packagedCandidateIds = [...packaged];
    return count;
  }

  let crcTable;
  function crc32(bytes) {
    if (!crcTable) {
      crcTable = new Uint32Array(256);
      for (let n = 0; n < 256; n += 1) {
        let value = n;
        for (let k = 0; k < 8; k += 1) value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
        crcTable[n] = value >>> 0;
      }
    }
    let crc = 0xffffffff;
    bytes.forEach(byte => { crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8); });
    return (crc ^ 0xffffffff) >>> 0;
  }

  function concatBytes(parts) {
    const result = new Uint8Array(parts.reduce((total, part) => total + part.length, 0));
    let offset = 0;
    parts.forEach(part => { result.set(part, offset); offset += part.length; });
    return result;
  }

  function base64ToBytes(value) {
    const binary = atob(String(value || ''));
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes;
  }

  function zipDate(date = new Date()) {
    const year = Math.max(1980, date.getFullYear());
    return {
      time: (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2),
      date: ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate(),
    };
  }

  function createZipBytes(filename, content, date = new Date()) {
    return createZipArchive([{ name: filename, content }], date);
  }

  function createZipArchive(entries, date = new Date()) {
    const encoder = new TextEncoder();
    const stamp = zipDate(date);
    const locals = []; const centrals = []; let offset = 0;
    entries.forEach(entry => {
      const name = encoder.encode(String(entry.name));
      const bytes = entry.content instanceof Uint8Array ? entry.content : encoder.encode(String(entry.content));
      const checksum = crc32(bytes);
      const local = new Uint8Array(30 + name.length); const localView = new DataView(local.buffer);
      localView.setUint32(0, 0x04034b50, true); localView.setUint16(4, 20, true); localView.setUint16(6, 0x0800, true);
      localView.setUint16(8, 0, true); localView.setUint16(10, stamp.time, true); localView.setUint16(12, stamp.date, true);
      localView.setUint32(14, checksum, true); localView.setUint32(18, bytes.length, true); localView.setUint32(22, bytes.length, true);
      localView.setUint16(26, name.length, true); localView.setUint16(28, 0, true); local.set(name, 30);
      const central = new Uint8Array(46 + name.length); const centralView = new DataView(central.buffer);
      centralView.setUint32(0, 0x02014b50, true); centralView.setUint16(4, 20, true); centralView.setUint16(6, 20, true);
      centralView.setUint16(8, 0x0800, true); centralView.setUint16(10, 0, true); centralView.setUint16(12, stamp.time, true); centralView.setUint16(14, stamp.date, true);
      centralView.setUint32(16, checksum, true); centralView.setUint32(20, bytes.length, true); centralView.setUint32(24, bytes.length, true);
      centralView.setUint16(28, name.length, true); centralView.setUint16(30, 0, true); centralView.setUint16(32, 0, true);
      centralView.setUint16(34, 0, true); centralView.setUint16(36, 0, true); centralView.setUint32(38, 0, true); centralView.setUint32(42, offset, true); central.set(name, 46);
      locals.push(local, bytes); centrals.push(central); offset += local.length + bytes.length;
    });
    const centralBytes = concatBytes(centrals);
    const end = new Uint8Array(22);
    const endView = new DataView(end.buffer);
    endView.setUint32(0, 0x06054b50, true); endView.setUint16(4, 0, true); endView.setUint16(6, 0, true);
    endView.setUint16(8, entries.length, true); endView.setUint16(10, entries.length, true); endView.setUint32(12, centralBytes.length, true);
    endView.setUint32(16, offset, true); endView.setUint16(20, 0, true);
    return concatBytes([...locals, centralBytes, end]);
  }

  const core = { MATCH_LABELS, initialState, validateFeedback, validateDraft, buildResourcePackage, archivePackagedCandidates, createZipBytes, createZipArchive, base64ToBytes, checklistItems, toggleChecklistItem };
  root.ReviewAppCore = core;
  if (typeof document === 'undefined') return;

  const review = JSON.parse(document.querySelector('#review-data').textContent);
  const storageKey = `resource-research-review:${review.reviewId}`;
  const view = { search: '', status: '', currentId: null, dirty: false, persisted: false, notesMode: 'edit', editorTab: 'resource', informationMode: 'preview', openTaxonomyCategoryId: null, topWindow: 10, saveGuidanceSeen: false, packageGuidanceSeen: false };
  let state = initialState(review);

  function formatWhen(value) {
    if (!value) return 'Not recorded';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }

  function safeHref(value) {
    const raw = asText(value);
    if (!raw) return null;
    const candidate = /^[a-z][a-z0-9+.-]*:/i.test(raw) ? raw : `https://${raw}`;
    try { const url = new URL(candidate); return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? url.href : null; } catch { return null; }
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function metric(label, value) {
    const item = element('div', 'metric');
    item.append(element('span', '', label), element('strong', '', asText(value) || 'Not recorded'));
    return item;
  }

  function persist(markDirty = true) {
    state.updatedAt = new Date().toISOString();
    if (markDirty) view.dirty = true;
    try { localStorage.setItem(storageKey, JSON.stringify(state)); view.persisted = true; } catch { view.persisted = false; }
    updateActions();
  }

  function restoreLocal() {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) { state = validateFeedback(review, JSON.parse(saved)); view.persisted = true; }
    } catch { view.persisted = false; }
  }

  function candidateState(item) {
    return state.candidates[item.id];
  }

  function remainingCandidates() {
    const packaged = new Set((state.packagedCandidateIds || []).map(String));
    return review.candidates.filter(item => Object.hasOwn(state.candidates, item.id) && !packaged.has(String(item.id)));
  }

  function decisionText(item) {
    const itemState = candidateState(item);
    if (itemState.packageStatus === 'ready') return 'Ready for package';
    return 'Pending';
  }

  function decisionClass(item) {
    const itemState = candidateState(item);
    if (itemState.packageStatus === 'ready') return 'accepted';
    return 'pending';
  }

  function download(filename, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function feedbackPayload() {
    const payload = clone(state);
    payload.savedAt = new Date().toISOString();
    payload.review = {
      title: review.title,
      exportedAt: review.exportedAt,
      runStatus: review.run.status,
      candidates: review.candidates.map(item => ({
        id: item.id,
        name: item.name,
        origin: item.origin,
        createdAt: item.createdAt,
        candidate: clone(item.candidate),
        knownResourceMatch: clone(item.knownResourceMatch),
        active: !(state.packagedCandidateIds || []).map(String).includes(String(item.id)),
      })),
    };
    return payload;
  }

  function feedbackFilename() {
    return `${slug(review.title)}-run-${review.run.id}-curator-work.json`;
  }

  function saveWork() {
    download(feedbackFilename(), JSON.stringify(feedbackPayload(), null, 2), 'application/json');
    view.dirty = false; updateActions('Work saved.');
    const workspaceState = document.querySelector('#workspace-save-state');
    if (workspaceState) {
      workspaceState.textContent = 'Saved';
      setTimeout(() => { workspaceState.textContent = ''; }, 1800);
    }
  }

  function requestSaveWork() {
    if (view.saveGuidanceSeen) { saveWork(); return; }
    document.querySelector('#save-work-dialog').showModal();
  }

  function saveResourcePackage() {
    const built = buildResourcePackage(review, state);
    if (built.errors.length) {
      updateActions(built.errors.join(' '));
      return;
    }
    const entries = [{ name: 'tso-resources.json', content: JSON.stringify(built.data, null, 2) }];
    Object.entries(built.pdfAssets || {}).forEach(([path, asset]) => {
      if (/^pdfs\/[A-Za-z0-9%._-]+\/[A-Za-z0-9._-]+\.pdf$/i.test(path) && !path.includes('..')) {
        entries.push({ name: path, content: base64ToBytes(asset.data) });
      }
    });
    download(packageFilename(), createZipArchive(entries), 'application/zip');
    const archivedCount = archivePackagedCandidates(review, state, built, built.data.packageCreatedAt);
    view.currentId = null;
    document.querySelector('#candidate-dialog').close();
    persist();
    renderCandidates();
    updateActions(`${built.resources.length}-resource package saved; ${archivedCount} ${archivedCount === 1 ? 'candidate was' : 'candidates were'} archived from the active queue with their work history preserved.`);
    const workspaceState = document.querySelector('#workspace-save-state');
    workspaceState.textContent = 'Package saved';
    setTimeout(() => { workspaceState.textContent = ''; }, 1800);
  }

  function requestSaveResourcePackage() {
    if (view.packageGuidanceSeen) { saveResourcePackage(); return; }
    document.querySelector('#save-package-dialog').showModal();
  }

  function packageFilename() {
    const source = String(review.sourcePackage?.sourceName || 'tso').replace(/(?:-resource-package)?\.zip$/i, '');
    return `${slug(source)}-${slug(review.run.targetCategoryLabel)}-research-run-${review.run.id}-resource-package.zip`;
  }

  function updateActions(message = '') {
    const accepted = remainingCandidates().filter(item => candidateState(item).packageStatus === 'ready').length;
    const packageButton = document.querySelector('#download-package');
    packageButton.textContent = accepted ? `Save a resource package (${accepted})` : 'Save a resource package';
    packageButton.disabled = !review.sourcePackage?.packageEligible || accepted === 0;
    packageButton.title = review.sourcePackage?.packageEligible
      ? ''
      : review.sourcePackage
        ? 'Resource-package download currently requires a source package using schema 3.'
        : 'Standalone research can save feedback but cannot create a resource package.';
    const workspacePackageButton = document.querySelector('#workspace-download-package');
    workspacePackageButton.textContent = accepted ? `Save package (${accepted})` : 'Save package';
    workspacePackageButton.disabled = packageButton.disabled;
    workspacePackageButton.title = packageButton.title;
    document.querySelector('#save-state').textContent = view.persisted
      ? 'Progress is saved in this browser. Save work to move or back up the work.'
      : 'Save work to keep progress and resume later.';
    if (message) document.querySelector('#action-message').textContent = message;
  }

  function renderCandidates() {
    const wanted = view.search.toLocaleLowerCase();
    const remaining = remainingCandidates();
    const candidates = remaining.filter(item => {
      const itemState = candidateState(item);
      const ready = itemState.packageStatus === 'ready';
      if (view.status === 'ready' && !ready) return false;
      if (view.status === 'pending' && ready) return false;
      if (!wanted) return true;
      return [item.name, asText(item.candidate?.organization), asText(item.candidate?.program), asText(item.candidate?.description)]
        .join(' ').toLocaleLowerCase().includes(wanted);
    });
    const ready = remaining.filter(item => candidateState(item).packageStatus === 'ready').length;
    document.querySelector('#candidate-count').textContent = `${candidates.length} of ${remaining.length} candidates shown · ${ready} ready`;
    const target = document.querySelector('#candidate-list');
    if (!candidates.length) { target.replaceChildren(element('div', 'empty', remaining.length ? 'No candidates match this filter.' : 'No candidates remain in Curator.')); return; }
    target.replaceChildren(...candidates.map(item => {
      const button = element('button', 'candidate'); button.type = 'button';
      const head = element('div', 'candidate-head');
      const status = element('span', `status ${decisionClass(item)}`, decisionText(item));
      head.append(element('strong', '', item.name), status);
      const description = asText(item.candidate?.serviceNeed || item.candidate?.housingNeed || item.candidate?.description || item.candidate?.resourceType || 'Pending');
      button.append(head, element('p', 'candidate-description', description));
      const possibleRelationships = item.candidate?.possibleRelatedSubmissions || [];
      if (possibleRelationships.length) button.append(element(
        'p', 'signal-summary',
        `${possibleRelationships.length} possible related submission${possibleRelationships.length === 1 ? '' : 's'} to consider during normal curation`,
      ));
      if (item.knownResourceMatch) button.append(element('p', 'signal-summary', candidateState(item).matchAssessment
        ? `${MATCH_LABELS[candidateState(item).matchAssessment]}: ${item.knownResourceMatch.name}`
        : `Possible relationship: ${item.knownResourceMatch.name}`));
      button.addEventListener('click', () => openCandidate(item.id));
      return button;
    }));
  }

  function renderSourceOnlyRecords() {
    const records = review.manualDiscovery?.sourceOnlyRecords || [];
    const panel = document.querySelector('#source-only-panel');
    panel.hidden = !records.length;
    if (!records.length) return;
    document.querySelector('#source-only-summary').textContent =
      `Show ${records.length} preserved record${records.length === 1 ? '' : 's'}`;
    document.querySelector('#source-only-list').replaceChildren(...records.map(record => {
      const row = element('article', 'source-only-row');
      row.append(
        element('strong', '', asText(record.displayName) || 'Unnamed preserved lead'),
        element('small', '', `${friendly(record.routedRole)} · ${(record.members || []).map(member => asText(member.sourceLabel)).filter(Boolean).join(', ')}`),
      );
      const href = safeHref(asText(record.website));
      if (href) { const link = element('a', '', asText(record.website)); link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer'; row.append(link); }
      return row;
    }));
  }

  function appendFormattedText(target, text) {
    const parts = String(text || '').split(/(\*\*[^*]+\*\*|__[^_]+__)/g).filter(Boolean);
    parts.forEach(part => {
      if (part.startsWith('**') && part.endsWith('**')) target.append(element('strong', '', part.slice(2, -2)));
      else if (part.startsWith('__') && part.endsWith('__')) {
        const underlined = element('span', '', part.slice(2, -2)); underlined.style.textDecoration = 'underline'; target.append(underlined);
      } else target.append(document.createTextNode(part));
    });
  }

  function notesPreview(item, itemState) {
    const preview = element('div', 'notes-preview');
    const lines = String(itemState.curatorNotes || '').split(/\r?\n/);
    let hasContent = false;
    lines.forEach((line, lineIndex) => {
      const checklist = line.match(/^\s*[-*]\s+\[([ xX])\]\s+(.*)$/);
      if (checklist) {
        hasContent = true;
        const label = element('label', 'notes-check'); const input = document.createElement('input'); input.type = 'checkbox'; input.checked = checklist[1].toLocaleLowerCase() === 'x';
        const content = element('span'); appendFormattedText(content, checklist[2]);
        input.addEventListener('change', () => { itemState.curatorNotes = toggleChecklistItem(itemState.curatorNotes, lineIndex, input.checked); persist(); renderNotes(item); });
        label.append(input, content); preview.append(label); return;
      }
      if (/^\s*---\s*$/.test(line)) { hasContent = true; preview.append(document.createElement('hr')); return; }
      const bullet = line.match(/^\s*[-*]\s+(.*)$/);
      if (bullet) {
        hasContent = true;
        const row = element('div', 'notes-bullet'); row.append(element('span', '', '•')); const content = element('span'); appendFormattedText(content, bullet[1]); row.append(content); preview.append(row); return;
      }
      if (line.trim()) { hasContent = true; const paragraph = element('p'); appendFormattedText(paragraph, line); preview.append(paragraph); }
    });
    if (!hasContent) preview.append(element('p', 'notes-empty', 'Notes and checklist items will appear here.'));
    return preview;
  }

  function renderNotes(item) {
    const itemState = candidateState(item);
    const target = document.querySelector('#candidate-notes');
    const toolbar = element('div', 'notes-toolbar');
    const editButton = element('button', view.notesMode === 'edit' ? 'selected' : '', 'Edit'); editButton.type = 'button';
    const previewButton = element('button', view.notesMode === 'preview' ? 'selected' : '', 'Preview'); previewButton.type = 'button';
    editButton.addEventListener('click', () => { view.notesMode = 'edit'; renderNotes(item); });
    previewButton.addEventListener('click', () => { view.notesMode = 'preview'; renderNotes(item); });
    const formattingHelp = element('span', 'notes-format-help', 'Formatting: - [ ] checklist, * bullet, **bold**, __underline__, and --- for a divider.');
    toolbar.append(editButton, previewButton, formattingHelp); target.replaceChildren(toolbar);
    if (view.notesMode === 'preview') target.append(notesPreview(item, itemState));
    else {
      const textarea = element('textarea', 'notes-editor'); textarea.value = itemState.curatorNotes || '';
      textarea.placeholder = 'Interview notes and checklist';
      textarea.addEventListener('input', () => { itemState.curatorNotes = textarea.value; persist(); });
      target.append(textarea);
    }
  }

  function bringWindowToFront(windowElement) {
    view.topWindow += 1; windowElement.style.zIndex = String(view.topWindow);
  }

  function resetWorkspaceLayout() {
    view.topWindow = 10;
    document.querySelectorAll('.work-window').forEach(windowElement => {
      ['left', 'top', 'right', 'bottom', 'width', 'height', 'zIndex'].forEach(property => { windowElement.style[property] = ''; });
    });
  }

  function setupWorkspaceWindows() {
    document.querySelectorAll('.work-window').forEach(windowElement => {
      windowElement.addEventListener('pointerdown', () => bringWindowToFront(windowElement));
      const handles = windowElement.querySelector('.window-resize-handles');
      ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'].forEach(direction => {
        const resizeHandle = element('div', 'window-resize-handle'); resizeHandle.dataset.resize = direction; handles.append(resizeHandle);
        resizeHandle.addEventListener('pointerdown', event => {
          if (event.button !== 0) return;
          event.preventDefault(); event.stopPropagation(); bringWindowToFront(windowElement); resizeHandle.setPointerCapture(event.pointerId);
          const canvas = document.querySelector('#workspace-canvas').getBoundingClientRect();
          const start = windowElement.getBoundingClientRect(); const startX = event.clientX; const startY = event.clientY;
          const startLeft = start.left - canvas.left; const startTop = start.top - canvas.top;
          const startRight = startLeft + start.width; const startBottom = startTop + start.height;
          windowElement.style.right = 'auto'; windowElement.style.bottom = 'auto';
          const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));
          const move = moveEvent => {
            const dx = moveEvent.clientX - startX; const dy = moveEvent.clientY - startY;
            let left = startLeft; let right = startRight; let top = startTop; let bottom = startBottom;
            if (direction.includes('e')) right = clamp(startRight + dx, startLeft + 300, canvas.width);
            if (direction.includes('w')) left = clamp(startLeft + dx, 0, startRight - 300);
            if (direction.includes('s')) bottom = clamp(startBottom + dy, startTop + 60, canvas.height);
            if (direction.includes('n')) top = clamp(startTop + dy, 0, startBottom - 60);
            windowElement.style.left = `${left}px`; windowElement.style.top = `${top}px`;
            windowElement.style.width = `${right - left}px`; windowElement.style.height = `${bottom - top}px`;
          };
          const stop = () => { resizeHandle.removeEventListener('pointermove', move); resizeHandle.removeEventListener('pointerup', stop); resizeHandle.removeEventListener('pointercancel', stop); };
          resizeHandle.addEventListener('pointermove', move); resizeHandle.addEventListener('pointerup', stop); resizeHandle.addEventListener('pointercancel', stop);
        });
      });
      const handle = windowElement.querySelector('.window-titlebar');
      handle.addEventListener('pointerdown', event => {
        if (event.button !== 0) return;
        bringWindowToFront(windowElement); handle.setPointerCapture(event.pointerId);
        const canvas = document.querySelector('#workspace-canvas').getBoundingClientRect();
        const start = windowElement.getBoundingClientRect(); const offsetX = event.clientX - start.left; const offsetY = event.clientY - start.top;
        const move = moveEvent => {
          const left = Math.max(0, Math.min(canvas.width - 80, moveEvent.clientX - canvas.left - offsetX));
          const top = Math.max(0, Math.min(canvas.height - 44, moveEvent.clientY - canvas.top - offsetY));
          windowElement.style.left = `${left}px`; windowElement.style.top = `${top}px`; windowElement.style.right = 'auto'; windowElement.style.bottom = 'auto';
        };
        const stop = () => { handle.removeEventListener('pointermove', move); handle.removeEventListener('pointerup', stop); handle.removeEventListener('pointercancel', stop); };
        handle.addEventListener('pointermove', move); handle.addEventListener('pointerup', stop); handle.addEventListener('pointercancel', stop);
      });
    });
  }

  function inputField(label, field, value, multiline = false) {
    const wrapper = element('label', 'field'); wrapper.append(document.createTextNode(label));
    const input = multiline ? document.createElement('textarea') : document.createElement('input');
    if (multiline) input.rows = field === 'informationText' ? 8 : 3;
    input.value = value || ''; input.dataset.resourceField = field; wrapper.append(input); return wrapper;
  }

  function autoSizeInformation(textarea) {
    textarea.style.height = 'auto';
    const limit = Math.min(512, Math.max(240, window.innerHeight * 0.4));
    textarea.style.height = `${Math.min(textarea.scrollHeight, limit)}px`;
    textarea.style.overflowY = textarea.scrollHeight > limit ? 'auto' : 'hidden';
  }

  function checkbox(label, checked, onChange) {
    const wrapper = element('label', 'choice-check'); const input = document.createElement('input'); input.type = 'checkbox'; input.checked = checked;
    input.addEventListener('change', () => onChange(input.checked)); wrapper.append(input, document.createTextNode(label)); return wrapper;
  }

  function touchResource(resource) {
    resource.lastModified = new Date().toISOString(); persist();
  }

  function safePDFFileName(name) {
    const base = String(name || 'attachment.pdf').split(/[\\/]/).at(-1) || 'attachment.pdf';
    const safe = base.replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'attachment.pdf';
    return /\.pdf$/i.test(safe) ? safe : `${safe}.pdf`;
  }

  function randomId() {
    const bytes = new Uint8Array(16); crypto.getRandomValues(bytes);
    return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.addEventListener('load', () => resolve(String(reader.result || '').split(',', 2)[1] || ''));
      reader.addEventListener('error', () => reject(reader.error || new Error('Unable to read the PDF.')));
      reader.readAsDataURL(file);
    });
  }

  function formattedTextPreview(text) {
    const preview = element('div', 'information-preview notes-preview'); let hasContent = false;
    String(text || '').split(/\r?\n/).forEach(line => {
      if (/^\s*---\s*$/.test(line)) { hasContent = true; preview.append(document.createElement('hr')); return; }
      const bullet = line.match(/^\s*[-*]\s+(.*)$/);
      if (bullet) {
        hasContent = true; const row = element('div', 'notes-bullet'); row.append(element('span', '', '•'));
        const content = element('span'); appendFormattedText(content, bullet[1]); row.append(content); preview.append(row); return;
      }
      if (line.trim()) { hasContent = true; const paragraph = element('p'); appendFormattedText(paragraph, line); preview.append(paragraph); }
    });
    if (!hasContent) preview.append(element('p', 'notes-empty', 'No Information has been entered.'));
    return preview;
  }

  function appendPrintableField(target, label, value) {
    const text = asText(value);
    if (!text) return;
    const row = element('div', 'resource-print-field');
    row.append(element('strong', '', `${label}:`), element('span', '', text));
    target.append(row);
  }

  function printResourceDraft(resource) {
    if (!resource) return;
    const sheet = document.querySelector('#resource-print-sheet');
    const content = element('article', 'resource-print-card');
    content.append(element('h1', '', asText(resource.name) || 'Resource'));
    if (asText(resource.description)) content.append(element('p', 'resource-print-description', asText(resource.description)));
    appendPrintableField(content, 'Phone', resource.phone);
    appendPrintableField(content, 'Address', resource.address);
    appendPrintableField(content, 'Website', resource.website);
    appendPrintableField(content, 'Hours', resource.hours);
    if (asText(resource.informationText)) {
      content.append(element('hr', 'resource-print-separator'), formattedTextPreview(resource.informationText));
    }
    sheet.replaceChildren(content);
    document.body.classList.add('printing-resource');
    try { window.print(); } finally { document.body.classList.remove('printing-resource'); }
  }

  function rerenderCandidate(item) {
    persist();
    openCandidate(item.id);
  }

  function markTaxonomyChanged(categoryId = null) {
    if (categoryId && !state.taxonomyDraft.modifiedCategoryIds.includes(categoryId)) {
      state.taxonomyDraft.modifiedCategoryIds.push(categoryId);
    }
    state.taxonomyDraft.updatedAt = new Date().toISOString();
  }

  function taxonomyAddRow(placeholder, buttonLabel, onAdd) {
    const row = element('div', 'taxonomy-add-row');
    const input = document.createElement('input'); input.placeholder = placeholder;
    const button = element('button', 'secondary', buttonLabel); button.type = 'button';
    const submit = () => {
      const value = input.value.trim();
      if (!value) return;
      if (onAdd(value) !== false) input.value = '';
    };
    button.addEventListener('click', submit);
    input.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); submit(); } });
    row.append(input, button); return row;
  }

  function renderCategoriesEditor(item) {
    const categories = element('div', 'editor-choice-list');
    categories.append(element('p', 'muted', 'Add Types that are not already available within a category. Type deletion remains in TSO Resources.'));
    const grid = element('div', 'taxonomy-category-grid');
    (review.sourcePackage?.categorySummaries || []).forEach(category => {
      const id = String(category.id);
      const expanded = view.openTaxonomyCategoryId === id;
      const option = element('section', `taxonomy-category ${expanded ? 'expanded' : ''}`);
      const heading = element('button', 'taxonomy-category-button', categoryLabel(category));
      heading.type = 'button';
      heading.setAttribute('aria-expanded', String(expanded));
      heading.addEventListener('click', () => {
        view.openTaxonomyCategoryId = expanded ? null : id;
        openCandidate(item.id);
      });
      option.append(heading);
      if (!expanded) { grid.append(option); return; }
      const typeList = element('div', 'taxonomy-value-list');
      const types = state.taxonomyDraft.categoryTypes[id] || [];
      if (!types.length) typeList.append(element('p', 'muted', 'No Types defined.'));
      types.forEach(type => {
        const row = element('div', 'taxonomy-value-row'); row.append(element('span', '', type));
        typeList.append(row);
      });
      option.append(typeList, taxonomyAddRow('New Type', 'New', value => {
        if (types.some(existing => existing.toLocaleLowerCase() === value.toLocaleLowerCase())) return false;
        state.taxonomyDraft.categoryTypes[id] = [...types, value]; markTaxonomyChanged(id); rerenderCandidate(item); return true;
      }));
      grid.append(option);
    });
    categories.append(grid);
    return categories;
  }

  function renderResourceClassifications(item, resource) {
    const section = element('section', 'resource-classification-editor');
    section.append(element('h3', '', 'Categories'));
    const categories = element('div', 'editor-choice-list resource-category-grid');
    (review.sourcePackage?.categorySummaries || []).forEach(category => {
      const id = String(category.id); const selected = (resource.categories || []).includes(id);
      const option = element('div', 'editor-choice-group');
      option.append(checkbox(categoryLabel(category), selected, checked => {
        resource.categories = checked ? [...new Set([...(resource.categories || []), id])] : (resource.categories || []).filter(value => value !== id);
        if (!checked && resource.categoryFilters) delete resource.categoryFilters[id];
        touchResource(resource); openCandidate(item.id);
      }));
      const availableTypes = state.taxonomyDraft.categoryTypes[id] || [];
      if (selected && availableTypes.length) {
        const types = element('div', 'nested-choices');
        availableTypes.forEach(type => types.append(checkbox(type, (resource.categoryFilters?.[id] || []).includes(type), checked => {
          resource.categoryFilters ||= {}; const values = resource.categoryFilters[id] || [];
          resource.categoryFilters[id] = checked ? [...new Set([...values, type])] : values.filter(value => value !== type);
          if (!resource.categoryFilters[id].length) delete resource.categoryFilters[id];
          touchResource(resource);
        })));
        option.append(types);
      }
      categories.append(option);
    });
    const forSection = element('section', 'resource-for-section'); forSection.append(element('h3', '', 'For'));
    const forGroups = element('div', 'nested-choices resource-for-choices');
    if (!state.taxonomyDraft.forGroups.length) forGroups.append(element('p', 'muted', 'No For groups defined.'));
    state.taxonomyDraft.forGroups.forEach(label => forGroups.append(checkbox(label, (resource.forGroups || []).includes(label), checked => {
      const values = resource.forGroups || [];
      resource.forGroups = checked ? [...new Set([...values, label])] : values.filter(value => value !== label);
      touchResource(resource);
    })));
    forSection.append(forGroups); section.append(categories, forSection); return section;
  }

  function renderForEditor(item) {
    const forGroups = element('div', 'editor-choice-list');
    forGroups.append(element('p', 'muted', 'Add For groups that are not already available. For-group deletion remains in TSO Resources.'));
    const list = element('div', 'taxonomy-value-list');
    if (!state.taxonomyDraft.forGroups.length) list.append(element('p', 'muted', 'No For groups defined.'));
    state.taxonomyDraft.forGroups.forEach(label => {
      const row = element('div', 'taxonomy-value-row'); row.append(element('span', '', label));
      list.append(row);
    });
    forGroups.append(list, taxonomyAddRow('New For group', 'Add For group', value => {
      if (state.taxonomyDraft.forGroups.some(existing => existing.toLocaleLowerCase() === value.toLocaleLowerCase())) return false;
      state.taxonomyDraft.forGroups.push(value); markTaxonomyChanged(); rerenderCandidate(item); return true;
    }));
    return forGroups;
  }

  function renderPDFEditor(item, itemState, resource) {
    const section = element('section', 'pdf-editor'); section.append(element('h3', '', 'PDF attachments'));
    const list = element('div', 'pdf-list');
    const pdfs = Array.isArray(resource.pdfs) ? resource.pdfs : [];
    if (!pdfs.length) list.append(element('p', 'muted', 'No PDFs attached.'));
    pdfs.forEach(pdf => {
      const row = element('div', 'pdf-row'); row.append(element('span', '', pdf.name || 'PDF'));
      const remove = element('button', 'secondary', 'Remove PDF'); remove.type = 'button';
      remove.addEventListener('click', () => {
        resource.pdfs = pdfs.filter(existing => existing.id !== pdf.id); delete itemState.pdfAssets[pdf.path];
        touchResource(resource); openCandidate(item.id);
      });
      row.append(remove); list.append(row);
    });
    const picker = document.createElement('input'); picker.type = 'file'; picker.accept = 'application/pdf,.pdf'; picker.multiple = true; picker.hidden = true;
    picker.addEventListener('change', async () => {
      const files = Array.from(picker.files || []).filter(file => file.type === 'application/pdf' || /\.pdf$/i.test(file.name));
      resource.pdfs ||= []; itemState.pdfAssets ||= {};
      for (const file of files) {
        const id = randomId(); const name = safePDFFileName(file.name); const path = `pdfs/${encodeURIComponent(resource.id || 'resource')}/${id}-${name}`;
        resource.pdfs.push({ id, name: file.name || name, path });
        itemState.pdfAssets[path] = { name: file.name || name, type: 'application/pdf', data: await fileToBase64(file) };
      }
      if (files.length) { touchResource(resource); openCandidate(item.id); }
    });
    const attach = element('button', 'secondary', 'Attach PDF'); attach.type = 'button'; attach.addEventListener('click', () => picker.click());
    section.append(list, picker, attach); return section;
  }

  function renderResourceFields(item, itemState, resource) {
    const content = element('div'); const fields = element('div', 'resource-fields');
    fields.append(inputField('Name', 'name', resource.name), inputField('Phone', 'phone', resource.phone), inputField('Address', 'address', resource.address),
      inputField('Website', 'website', resource.website), inputField('Hours', 'hours', resource.hours), inputField('Verified (MM/YY)', 'verifiedOn', resource.verifiedOn),
      inputField('Description', 'description', resource.description, true));
    fields.querySelectorAll('[data-resource-field]').forEach(input => input.addEventListener('input', () => {
      resource[input.dataset.resourceField] = input.value; touchResource(resource);
    }));
    content.append(fields, renderResourceClassifications(item, resource), renderPDFEditor(item, itemState, resource));
    const information = element('section', 'information-editor'); information.append(element('h3', '', 'Information'));
    const tabs = element('div', 'information-tabs');
    const edit = element('button', view.informationMode === 'edit' ? 'selected' : '', 'Edit'); const preview = element('button', view.informationMode === 'preview' ? 'selected' : '', 'Preview');
    edit.type = preview.type = 'button'; edit.addEventListener('click', () => { view.informationMode = 'edit'; openCandidate(item.id); }); preview.addEventListener('click', () => { view.informationMode = 'preview'; openCandidate(item.id); }); tabs.append(edit, preview);
    information.append(tabs, element('p', 'muted', 'Formatting: use * followed by a space for bullets, **bold**, __underline__, and --- on its own line for a divider.'));
    if (view.informationMode === 'preview') information.append(formattedTextPreview(resource.informationText));
    else {
      const input = inputField('Information', 'informationText', resource.informationText, true); const textarea = input.querySelector('textarea');
      textarea.addEventListener('input', event => { resource.informationText = event.target.value; touchResource(resource); autoSizeInformation(textarea); });
      information.append(input); requestAnimationFrame(() => autoSizeInformation(textarea));
    }
    content.append(information); return content;
  }

  function renderResourceEditor(item, itemState) {
    const resource = itemState.resourceDraft;
    const box = element('section', 'resource-editor');
    box.append(element('p', 'section-label', 'Resource draft'), element('h3', '', 'TSO Resources editors'));
    const tabs = element('div', 'resource-editor-tabs');
    [['categories', 'Categories'], ['resource', 'Resource'], ['for', 'For']].forEach(([value, label]) => {
      const button = element('button', view.editorTab === value ? 'selected' : '', label); button.type = 'button';
      button.addEventListener('click', () => { view.editorTab = value; openCandidate(item.id); }); tabs.append(button);
    });
    box.append(
      tabs,
      element('p', 'muted', 'Use Resource for phone, address, website, hours, description, and Information. Use For for the people this resource serves.'),
    );
    if (view.editorTab === 'categories') box.append(renderCategoriesEditor(item));
    else if (view.editorTab === 'for') box.append(renderForEditor(item));
    else box.append(renderResourceFields(item, itemState, resource));
    return box;
  }

  function renderReviewEditor(item) {
    const itemState = candidateState(item);
    const editor = element('section', 'review-editor'); editor.append(element('p', 'section-label', 'Your review'));
    const actions = element('div', 'review-decision-actions');
    const ready = checkbox('Ready for package', itemState.packageStatus === 'ready', checked => {
      const now = new Date().toISOString();
      itemState.packageStatus = checked ? 'ready' : 'pending';
      itemState.reviewedAt = now;
      itemState.updatedAt = now;
      persist(); renderCandidates(); openCandidate(item.id);
    });
    ready.classList.add('ready-toggle');
    const print = element('button', 'secondary resource-print-button', 'Print');
    print.type = 'button'; print.disabled = !itemState.resourceDraft;
    print.title = itemState.resourceDraft ? 'Print the client-facing resource information' : 'No resource draft is available to print';
    print.addEventListener('click', () => printResourceDraft(itemState.resourceDraft));
    actions.append(ready, print); editor.append(actions);
    if (item.knownResourceMatch) {
      const match = element('fieldset', 'match-card'); match.append(element('legend', '', `Relationship to ${item.knownResourceMatch.name}`), element('p', 'muted', 'Choose the best description of the relationship. This similarity warning is not proof of a duplicate.'));
      Object.entries(MATCH_LABELS).forEach(([value, label]) => {
        const wrapper = element('label', 'choice-check'); const input = document.createElement('input'); input.type = 'radio'; input.name = `match-${item.id}`; input.value = value; input.checked = itemState.matchAssessment === value;
        input.addEventListener('change', () => { itemState.matchAssessment = value; persist(); renderCandidates(); if (itemState.packageStatus === 'ready') openCandidate(item.id); });
        wrapper.append(input, document.createTextNode(label)); match.append(wrapper);
      });
      editor.append(match);
    }
    if (review.sourcePackage?.packageEligible && itemState.resourceDraft) editor.append(renderResourceEditor(item, itemState));
    else if (itemState.packageStatus === 'ready') editor.append(element('p', 'standalone-note', review.sourcePackage
      ? 'This source package does not use the supported package schema. The work can be saved, but it cannot create a resource package.'
      : 'This standalone Curator can save work, but it cannot create a resource package.'));
    return editor;
  }

  function openCandidate(id) {
    view.currentId = id;
    const item = remainingCandidates().find(candidate => String(candidate.id) === String(id));
    if (!item) return;
    document.querySelector('#candidate-name').textContent = item.name;
    document.querySelector('#notes-window-title').textContent = `Notes — ${item.name}`;
    const status = document.querySelector('#candidate-status'); status.className = `status ${decisionClass(item)}`; status.textContent = decisionText(item);
    document.querySelector('#candidate-editor').replaceChildren(renderReviewEditor(item));
    renderNotes(item);
    const candidates = remainingCandidates();
    const position = candidates.findIndex(candidate => String(candidate.id) === String(id));
    document.querySelector('#previous-candidate').disabled = position <= 0;
    document.querySelector('#next-candidate').disabled = position < 0 || position >= candidates.length - 1;
    const dialog = document.querySelector('#candidate-dialog'); if (!dialog.open) dialog.showModal();
  }

  function initialize() {
    restoreLocal();
    document.title = `${review.title} · Resource Curator`;
    document.querySelector('#candidate-list-name').textContent = review.run.targetCategoryLabel;
    const packageInfo = review.sourcePackage;
    const filter = document.querySelector('#status-filter');
    document.querySelector('#search').addEventListener('input', event => { view.search = event.target.value; renderCandidates(); });
    filter.addEventListener('change', event => { view.status = event.target.value; renderCandidates(); });
    const reviewer = document.querySelector('#reviewer-name'); reviewer.value = state.reviewerName || ''; reviewer.addEventListener('input', () => { state.reviewerName = reviewer.value; persist(); });
    document.querySelector('#download-feedback').addEventListener('click', requestSaveWork);
    document.querySelector('#workspace-save-work').addEventListener('click', requestSaveWork);
    document.querySelector('#download-package').addEventListener('click', requestSaveResourcePackage);
    document.querySelector('#workspace-download-package').addEventListener('click', requestSaveResourcePackage);
    document.querySelector('#cancel-save-work').addEventListener('click', () => document.querySelector('#save-work-dialog').close());
    document.querySelector('#continue-save-work').addEventListener('click', () => { view.saveGuidanceSeen = true; document.querySelector('#save-work-dialog').close(); saveWork(); });
    document.querySelector('#cancel-save-package').addEventListener('click', () => document.querySelector('#save-package-dialog').close());
    document.querySelector('#continue-save-package').addEventListener('click', () => { view.packageGuidanceSeen = true; document.querySelector('#save-package-dialog').close(); saveResourcePackage(); });
    document.querySelector('#reset-window-layout').addEventListener('click', resetWorkspaceLayout);
    const resume = document.querySelector('#resume-feedback');
    resume.addEventListener('change', async () => {
      const file = resume.files?.[0]; if (!file) return;
      try {
        state = validateFeedback(review, JSON.parse(await file.text())); persist(false); view.dirty = false; reviewer.value = state.reviewerName || ''; renderCandidates();
        if (view.currentId && Object.hasOwn(state.candidates, view.currentId)) openCandidate(view.currentId);
        else { view.currentId = null; document.querySelector('#candidate-dialog').close(); }
        updateActions('Saved work opened.');
      }
      catch (error) { updateActions(error.message); }
      finally { resume.value = ''; }
    });
    document.querySelector('#close-dialog').addEventListener('click', () => document.querySelector('#candidate-dialog').close());
    document.querySelector('#previous-candidate').addEventListener('click', () => {
      const candidates = remainingCandidates();
      const position = candidates.findIndex(candidate => String(candidate.id) === String(view.currentId));
      if (position > 0) openCandidate(candidates[position - 1].id);
    });
    document.querySelector('#next-candidate').addEventListener('click', () => {
      const candidates = remainingCandidates();
      const position = candidates.findIndex(candidate => String(candidate.id) === String(view.currentId));
      if (position >= 0 && position < candidates.length - 1) openCandidate(candidates[position + 1].id);
    });
    document.querySelector('#candidate-dialog').addEventListener('click', event => { if (event.target === event.currentTarget) event.currentTarget.close(); });
    window.addEventListener('beforeunload', event => { if (view.dirty && !view.persisted) { event.preventDefault(); event.returnValue = ''; } });
    setupWorkspaceWindows(); renderSourceOnlyRecords(); renderCandidates(); updateActions();
    const packageText = packageInfo ? `${packageInfo.sourceName}; schema ${packageInfo.schemaVersion}; package ${packageInfo.packageVersion}` : `Standalone location research; ${review.run.targetLocation || 'location not recorded'}`;
    document.querySelector('#footer').textContent = `Resource Curator v0.37.4 · Exported ${formatWhen(review.exportedAt)} · ${packageText} · Curator schema ${review.reviewCopySchemaVersion}`;
  }

  initialize();
}(globalThis));
