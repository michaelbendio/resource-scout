'use strict';

(function (root) {
  const DECISIONS = ['accepted', 'research-further', 'already-known', 'wrong-category', 'rejected'];
  const DECISION_LABELS = {
    accepted: 'Ready for package',
    'research-further': 'In progress',
    'already-known': 'Already known',
    'wrong-category': 'Wrong category',
    rejected: 'Reject',
  };
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

  function normalizeDecision(value) {
    return DECISIONS.includes(value) ? value : '';
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
        decision: normalizeDecision(item.status),
        feedback: asText(item.reviewFeedback || item.notes),
        sourceNotes: asText(item.notes),
        curatorNotes: asText(item.notes),
        originalReviewFeedback: asText(item.reviewFeedback),
        useForFutureResearch: Boolean(item.useForFutureResearch),
        matchAssessment: item.matchAssessment || '',
        reviewedAt: item.reviewedAt || null,
        updatedAt: item.updatedAt || review.exportedAt,
        resourceDraft: item.resourceDraft ? clone(item.resourceDraft) : null,
        pdfAssets: {},
      };
    });
    return {
      reviewFeedbackSchemaVersion: 1,
      reviewCopySchemaVersion: review.reviewCopySchemaVersion,
      reviewId: review.reviewId,
      sourceSha256: review.sourcePackage?.sourceSha256 || null,
      run: {
        id: review.run.id,
        categoryId: review.run.targetCategoryId,
        categoryLabel: review.run.targetCategoryLabel,
      },
      taxonomyDraft: initialTaxonomyDraft(review),
      reviewerName: '',
      updatedAt: review.exportedAt,
      candidates,
    };
  }

  function validateFeedback(review, feedback) {
    if (!feedback || feedback.reviewFeedbackSchemaVersion !== 1) throw new Error('This is not a supported review-feedback file.');
    if (feedback.reviewId !== review.reviewId) throw new Error('This feedback belongs to a different review copy.');
    if ((feedback.sourceSha256 || null) !== (review.sourcePackage?.sourceSha256 || null)) throw new Error('The source package does not match this review copy.');
    const expected = review.candidates.map(item => String(item.id)).sort();
    const received = Object.keys(feedback.candidates || {}).map(String).sort();
    if (JSON.stringify(expected) !== JSON.stringify(received)) throw new Error('The candidate list does not match this review copy.');
    const restored = clone(feedback);
    restored.taxonomyDraft = normalizeTaxonomyDraft(review, restored.taxonomyDraft);
    review.candidates.forEach(item => {
      const itemState = restored.candidates[item.id];
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
    const acceptedItems = review.candidates.filter(item => state.candidates?.[item.id]?.decision === 'accepted');
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

  const core = { DECISIONS, DECISION_LABELS, MATCH_LABELS, initialState, validateFeedback, validateDraft, buildResourcePackage, createZipBytes, createZipArchive, base64ToBytes, checklistItems, toggleChecklistItem };
  root.ReviewAppCore = core;
  if (typeof document === 'undefined') return;

  const review = JSON.parse(document.querySelector('#review-data').textContent);
  const storageKey = `resource-research-review:${review.reviewId}`;
  const view = { search: '', status: '', currentId: null, dirty: false, persisted: false, notesMode: 'edit', editorTab: 'resource', informationMode: 'preview', topWindow: 10 };
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

  function decisionText(item) {
    return DECISION_LABELS[candidateState(item).decision] || 'Not reviewed';
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
    updateActions(`${built.resources.length}-resource package saved.${review.run.status === 'partial' ? ' This run was incomplete; review the stage warning before use.' : ''}`);
    const workspaceState = document.querySelector('#workspace-save-state');
    workspaceState.textContent = 'Package saved';
    setTimeout(() => { workspaceState.textContent = ''; }, 1800);
  }

  function packageFilename() {
    const source = String(review.sourcePackage?.sourceName || 'tso').replace(/(?:-resource-package)?\.zip$/i, '');
    return `${slug(source)}-${slug(review.run.targetCategoryLabel)}-research-run-${review.run.id}-resource-package.zip`;
  }

  function updateActions(message = '') {
    const accepted = review.candidates.filter(item => candidateState(item).decision === 'accepted').length;
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
    const candidates = review.candidates.filter(item => {
      const itemState = candidateState(item);
      if (view.status && itemState.decision !== view.status) return false;
      if (!wanted) return true;
      return [item.name, asText(item.candidate?.organization), asText(item.candidate?.program), asText(item.candidate?.description), itemState.feedback]
        .join(' ').toLocaleLowerCase().includes(wanted);
    });
    document.querySelector('#candidate-count').textContent = `${candidates.length} of ${review.candidates.length} candidates shown`;
    const target = document.querySelector('#candidate-list');
    if (!candidates.length) { target.replaceChildren(element('div', 'empty', 'No candidates match this filter.')); return; }
    target.replaceChildren(...candidates.map(item => {
      const button = element('button', 'candidate'); button.type = 'button';
      const head = element('div', 'candidate-head');
      const status = element('span', `status ${candidateState(item).decision || 'unreviewed'}`, decisionText(item));
      head.append(element('strong', '', item.name), status);
      const description = asText(item.candidate?.serviceNeed || item.candidate?.housingNeed || item.candidate?.description || item.candidate?.resourceType || 'Awaiting review');
      button.append(head, element('p', 'candidate-description', description));
      if (item.knownResourceMatch) button.append(element('p', 'signal-summary', candidateState(item).matchAssessment
        ? `${MATCH_LABELS[candidateState(item).matchAssessment]}: ${item.knownResourceMatch.name}`
        : `Possible relationship: ${item.knownResourceMatch.name}`));
      button.addEventListener('click', () => openCandidate(item.id));
      return button;
    }));
  }

  function section(target, title, value) {
    const values = Array.isArray(value) ? value.map(asText).filter(Boolean) : [asText(value)].filter(Boolean);
    if (!values.length) return;
    const wrapper = element('section', 'candidate-section'); wrapper.append(element('h3', '', title));
    if (Array.isArray(value)) { const list = element('ul'); values.forEach(entry => list.append(element('li', '', entry))); wrapper.append(list); }
    else wrapper.append(element('p', '', values[0]));
    target.append(wrapper);
  }

  function fact(target, label, value, link = false) {
    const text = asText(value); if (!text) return;
    const item = element('div', 'candidate-fact'); item.append(element('strong', '', label));
    const href = link ? safeHref(text) : null;
    if (href) { const anchor = element('a', '', text); anchor.href = href; anchor.target = '_blank'; anchor.rel = 'noopener noreferrer'; item.append(anchor); }
    else item.append(element('div', '', text));
    target.append(item);
  }

  function candidateDetails(item) {
    const candidate = item.candidate || {};
    const wrapper = element('div', 'candidate-details');
    const summary = asText(candidate.description || candidate.serviceNeed || candidate.housingNeed);
    if (summary) wrapper.append(element('div', 'candidate-summary', summary));
    const facts = element('div', 'candidate-facts');
    fact(facts, 'Organization', candidate.organization); fact(facts, 'Program', candidate.program); fact(facts, 'Type', candidate.resourceType);
    fact(facts, 'Area served', candidate.geography); fact(facts, 'Access timeline', candidate.accessTimeline); fact(facts, 'Phone', candidate.phone);
    fact(facts, 'Other phone numbers', candidate.additionalPhoneNumbers); fact(facts, 'Address', candidate.address);
    fact(facts, 'Other addresses', candidate.additionalAddresses); fact(facts, 'Hours', candidate.hours); fact(facts, 'Website', candidate.website || candidate.url, true);
    if (facts.children.length) wrapper.append(facts);
    section(wrapper, `${review.run.targetCategoryLabel || 'Resource'} need`, candidate.serviceNeed || candidate.housingNeed);
    section(wrapper, 'Services provided', candidate.servicesProvided);
    section(wrapper, 'Suggested Types', candidate.recommendedTypes); section(wrapper, 'Suggested For', candidate.recommendedFor);
    section(wrapper, 'Classification rationale', candidate.classificationRationale); section(wrapper, 'Eligibility requirements', candidate.eligibility);
    section(wrapper, 'What to expect', candidate.whatToExpect); section(wrapper, 'How to best connect', candidate.howToBestConnect);
    section(wrapper, 'Additional notes', candidate.additionalNotes); section(wrapper, 'Barriers and restrictions', candidate.barriers);
    section(wrapper, 'Unknowns to pursue', candidate.unknowns); section(wrapper, 'Follow-up branches', candidate.followUpBranches);
    const evidence = Array.isArray(candidate.evidence) ? candidate.evidence : [];
    if (evidence.length) {
      const evidenceSection = element('section', 'candidate-section'); evidenceSection.append(element('h3', '', 'Evidence'));
      evidence.forEach(source => {
        const card = element('div', 'evidence-card'); const title = asText(source.title || source.url || 'Evidence source'); const href = safeHref(source.url);
        if (href) { const anchor = element('a', '', title); anchor.href = href; anchor.target = '_blank'; anchor.rel = 'noopener noreferrer'; card.append(anchor); }
        else card.append(element('strong', '', title));
        card.append(element('div', '', asText(source.finding || source.quoteOrFinding)));
        evidenceSection.append(card);
      });
      wrapper.append(evidenceSection);
    }
    return wrapper;
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

  function setupWorkspaceWindows() {
    document.querySelectorAll('.work-window').forEach(windowElement => {
      windowElement.addEventListener('pointerdown', () => bringWindowToFront(windowElement));
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
    (review.sourcePackage?.categorySummaries || []).forEach(category => {
      const id = String(category.id);
      const option = element('div', 'editor-choice-group');
      option.append(element('strong', 'taxonomy-heading', categoryLabel(category)));
      const typeList = element('div', 'taxonomy-value-list');
      const types = state.taxonomyDraft.categoryTypes[id] || [];
      if (!types.length) typeList.append(element('p', 'muted', 'No Types defined.'));
      types.forEach(type => {
        const row = element('div', 'taxonomy-value-row'); row.append(element('span', '', type));
        typeList.append(row);
      });
      option.append(typeList, taxonomyAddRow('New Type', 'Add Type', value => {
        if (types.some(existing => existing.toLocaleLowerCase() === value.toLocaleLowerCase())) return false;
        state.taxonomyDraft.categoryTypes[id] = [...types, value]; markTaxonomyChanged(id); rerenderCandidate(item); return true;
      }));
      categories.append(option);
    });
    return categories;
  }

  function renderResourceClassifications(item, resource) {
    const section = element('section', 'resource-classification-editor');
    section.append(element('h3', '', 'Categories, Types, and For'));
    const categories = element('div', 'editor-choice-list');
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
        const types = element('div', 'nested-choices'); types.append(element('strong', '', `${categoryLabel(category)} Types`));
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
    const forGroups = element('div', 'nested-choices resource-for-choices');
    forGroups.append(element('strong', '', 'For'));
    if (!state.taxonomyDraft.forGroups.length) forGroups.append(element('p', 'muted', 'No For groups defined.'));
    state.taxonomyDraft.forGroups.forEach(label => forGroups.append(checkbox(label, (resource.forGroups || []).includes(label), checked => {
      const values = resource.forGroups || [];
      resource.forGroups = checked ? [...new Set([...values, label])] : values.filter(value => value !== label);
      touchResource(resource);
    })));
    section.append(categories, forGroups); return section;
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
      const input = inputField('Information', 'informationText', resource.informationText, true); input.querySelector('textarea').addEventListener('input', event => { resource.informationText = event.target.value; touchResource(resource); }); information.append(input);
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
    box.append(tabs);
    if (view.editorTab === 'categories') box.append(renderCategoriesEditor(item));
    else if (view.editorTab === 'for') box.append(renderForEditor(item));
    else box.append(renderResourceFields(item, itemState, resource));
    return box;
  }

  function renderReviewEditor(item) {
    const itemState = candidateState(item);
    const editor = element('section', 'review-editor'); editor.append(element('p', 'section-label', 'Your review'), element('h3', '', 'Decision and feedback'));
    const decisions = element('div', 'decision-grid');
    DECISIONS.forEach(value => {
      const button = element('button', `decision ${value === itemState.decision ? 'selected' : ''}`, DECISION_LABELS[value]); button.type = 'button';
      button.addEventListener('click', () => { itemState.decision = value; itemState.reviewedAt = new Date().toISOString(); persist(); renderCandidates(); openCandidate(item.id); });
      decisions.append(button);
    });
    editor.append(decisions);
    if (item.knownResourceMatch) {
      const match = element('fieldset', 'match-card'); match.append(element('legend', '', `Relationship to ${item.knownResourceMatch.name}`), element('p', 'muted', 'Choose the best description of the relationship. This similarity warning is not proof of a duplicate.'));
      Object.entries(MATCH_LABELS).forEach(([value, label]) => {
        const wrapper = element('label', 'choice-check'); const input = document.createElement('input'); input.type = 'radio'; input.name = `match-${item.id}`; input.value = value; input.checked = itemState.matchAssessment === value;
        input.addEventListener('change', () => { itemState.matchAssessment = value; persist(); renderCandidates(); if (itemState.decision === 'accepted') openCandidate(item.id); });
        wrapper.append(input, document.createTextNode(label)); match.append(wrapper);
      });
      editor.append(match);
    }
    const feedback = inputField('Feedback for future research', 'feedback', itemState.feedback, true); feedback.classList.add('feedback-field');
    const textarea = feedback.querySelector('textarea'); textarea.removeAttribute('data-resource-field'); textarea.placeholder = 'Why? What should the researcher notice next time?';
    textarea.addEventListener('input', () => { itemState.feedback = textarea.value; persist(); }); editor.append(feedback);
    editor.append(checkbox('Use this feedback in future research', itemState.useForFutureResearch, checked => { itemState.useForFutureResearch = checked; persist(); }));
    if (review.sourcePackage?.packageEligible && itemState.resourceDraft) editor.append(renderResourceEditor(item, itemState));
    else if (itemState.decision === 'accepted') editor.append(element('p', 'standalone-note', review.sourcePackage
      ? 'This source package does not use the supported package schema. The work and decision can be saved, but it cannot create a resource package.'
      : 'This standalone Curator can save work and decisions, but it cannot create a resource package.'));
    return editor;
  }

  function openCandidate(id) {
    view.currentId = id;
    const item = review.candidates.find(candidate => String(candidate.id) === String(id));
    document.querySelector('#candidate-name').textContent = item.name;
    document.querySelector('#notes-window-title').textContent = `Notes — ${item.name}`;
    const status = document.querySelector('#candidate-status'); status.className = `status ${candidateState(item).decision || 'unreviewed'}`; status.textContent = decisionText(item);
    document.querySelector('#candidate-research').replaceChildren(candidateDetails(item));
    document.querySelector('#candidate-editor').replaceChildren(renderReviewEditor(item));
    renderNotes(item);
    const position = review.candidates.findIndex(candidate => String(candidate.id) === String(id));
    document.querySelector('#previous-candidate').disabled = position <= 0;
    document.querySelector('#next-candidate').disabled = position < 0 || position >= review.candidates.length - 1;
    const dialog = document.querySelector('#candidate-dialog'); if (!dialog.open) dialog.showModal();
  }

  function renderLessons() {
    if (!review.lessons?.length) return;
    document.querySelector('#lessons-panel').hidden = false;
    document.querySelector('#lesson-list').replaceChildren(...review.lessons.map(lesson => {
      const item = element('div', 'lesson'); item.append(element('small', '', `${friendly(lesson.scope)} · ${friendly(lesson.source)}`), element('p', '', lesson.text)); return item;
    }));
  }

  function initialize() {
    restoreLocal();
    document.title = `${review.title} · Resource Curator`; document.querySelector('#title').textContent = review.title;
    document.querySelector('#notice').textContent = review.notice; document.querySelector('#summary').textContent = review.run.summary || 'No summary was provided.';
    document.querySelector('#assignment').textContent = review.run.assignment;
    const packageInfo = review.sourcePackage; const standalone = review.run.researchMode === 'standalone-location';
    document.querySelector('#metadata').replaceChildren(metric('Completed', formatWhen(review.run.completedAt)), metric('Run status', friendly(review.run.status)),
      metric('Research agent', friendly(review.run.adapter)), metric('Candidates', review.run.candidateCount), metric('Category', review.run.targetCategoryLabel),
      metric('Research scope', standalone ? review.run.targetLocation : 'Connected package'), metric('Source package', packageInfo ? `${packageInfo.sourceName} · package ${packageInfo.packageVersion}` : 'None'));
    renderLessons();
    const filter = document.querySelector('#status-filter'); DECISIONS.forEach(value => { const option = document.createElement('option'); option.value = value; option.textContent = DECISION_LABELS[value]; filter.append(option); });
    document.querySelector('#search').addEventListener('input', event => { view.search = event.target.value; renderCandidates(); });
    filter.addEventListener('change', event => { view.status = event.target.value; renderCandidates(); });
    const reviewer = document.querySelector('#reviewer-name'); reviewer.value = state.reviewerName || ''; reviewer.addEventListener('input', () => { state.reviewerName = reviewer.value; persist(); });
    document.querySelector('#download-feedback').addEventListener('click', saveWork);
    document.querySelector('#workspace-save-work').addEventListener('click', saveWork);
    document.querySelector('#download-package').addEventListener('click', saveResourcePackage);
    document.querySelector('#workspace-download-package').addEventListener('click', saveResourcePackage);
    const resume = document.querySelector('#resume-feedback');
    resume.addEventListener('change', async () => {
      const file = resume.files?.[0]; if (!file) return;
      try { state = validateFeedback(review, JSON.parse(await file.text())); persist(false); view.dirty = false; reviewer.value = state.reviewerName || ''; renderCandidates(); if (view.currentId) openCandidate(view.currentId); updateActions('Saved work opened.'); }
      catch (error) { updateActions(error.message); }
      finally { resume.value = ''; }
    });
    document.querySelector('#close-dialog').addEventListener('click', () => document.querySelector('#candidate-dialog').close());
    document.querySelector('#previous-candidate').addEventListener('click', () => {
      const position = review.candidates.findIndex(candidate => String(candidate.id) === String(view.currentId));
      if (position > 0) openCandidate(review.candidates[position - 1].id);
    });
    document.querySelector('#next-candidate').addEventListener('click', () => {
      const position = review.candidates.findIndex(candidate => String(candidate.id) === String(view.currentId));
      if (position >= 0 && position < review.candidates.length - 1) openCandidate(review.candidates[position + 1].id);
    });
    document.querySelector('#candidate-dialog').addEventListener('click', event => { if (event.target === event.currentTarget) event.currentTarget.close(); });
    window.addEventListener('beforeunload', event => { if (view.dirty && !view.persisted) { event.preventDefault(); event.returnValue = ''; } });
    setupWorkspaceWindows(); renderCandidates(); updateActions();
    const packageText = packageInfo ? `${packageInfo.sourceName}; schema ${packageInfo.schemaVersion}; package ${packageInfo.packageVersion}` : `Standalone location research; ${review.run.targetLocation || 'location not recorded'}`;
    document.querySelector('#footer').textContent = `Resource Curator v0.19.0 · Exported ${formatWhen(review.exportedAt)} · ${packageText} · Curator schema ${review.reviewCopySchemaVersion}`;
  }

  initialize();
}(globalThis));
