// ============================================================
// SHARED RESOURCES PROTOTYPE: LAYER (runs after the app)
// ============================================================
// Everything the app needs for shared resources, and nothing else:
// - an office chooser, since this one page holds every office;
// - a restriction, said in words on the card;
// - Coverage and restriction in the resource editor, after Categories, with the
//   offices that see the resource and the other offices' copies of it;
// - a Coverage tab in admin: counties down the side, shared resources across.
// Any office may edit any resource its missionaries see (Elder Bendio, 24 October
// 2026); the app only ever holds what the chosen office sees, so that rule holds.
(function(){
  const SR = window.SR;
  const COVERAGE_TAB = "coverage";
  const VIEW_ONLY = ["coverage", "coverageReasons"];
  const STATES = [...new Set(SR.OFFICES.map(o => o.state))].sort();
  const countyLabel = c => c.replace(/^(\w\w):(.*)$/, "$2, $1");

  document.head.insertAdjacentHTML("beforeend", `<style>
    .sr-office { margin-left:12px; font-size:14px; font-weight:normal; }
    .sr-title { display:flex; align-items:center; flex-wrap:wrap; justify-self:start; }
    /* Categories in the middle of the screen; Print, Help and Admin on the right. */
    .topbar { grid-template-columns:minmax(0, 1fr) auto minmax(0, 1fr); }
    .topbar .tabs { justify-self:end; }
    #tabFavorites, .favorite-toggle { display:none !important; }
    .sr-office select { font:inherit; margin-left:4px; }
    .sr-restriction { color:#8a4b00; font-size:.9em; margin-top:2px; }
    .sr-warning { color:#aa0000; margin:6px 0; }
    .sr-checks label { display:inline-block; margin:2px 12px 2px 2px; }
    .sr-table { border-collapse:collapse; font-size:13px; margin-top:8px; }
    .sr-table th, .sr-table td { border:1px solid #ccc; padding:4px 6px; text-align:left; vertical-align:top; }
    .sr-table td.sr-gap { background:#ffe3e0; }
    .sr-table td.sr-yes { text-align:center; }
    .sr-scroll { overflow-x:auto; }
    .sr-coverage { min-width:0; } /* a flex item: without this, a wide table widens the page */
  </style>`);

  // ---- Writing the app's changes back ----
  const stripped = record => {
    const copy = {...record};
    VIEW_ONLY.forEach(key => delete copy[key]);
    return copy;
  };
  let baseline, viewIds, vocabularyBaseline;
  const vocabularyOf = d => JSON.stringify({categories:d.categories, forGroups:d.forGroups, forGroupDefinitions:d.forGroupDefinitions || {}});
  function takeBaseline(){
    baseline = new Map(data.resources.map(r => [r.id, JSON.stringify(stripped(r))]));
    viewIds = new Set(data.resources.map(r => r.id));
    vocabularyBaseline = vocabularyOf(data);
  }
  takeBaseline();

  function setGroup(id, value){ SR.overlay.shared[id] = value; }
  function removeFromGroup(resourceId){
    const g = SR.groupOf(resourceId);
    if(!g) return;
    const members = g.members.filter(m => m !== resourceId);
    if(!members.length){ setGroup(g.id, null); return; }
    setGroup(g.id, {...SR.group(g.id), members, keeper: g.keeper === resourceId ? members[0] : g.keeper});
  }

  function syncFromView(){
    const officeId = SR.office().id;
    const present = new Set();
    data.resources.forEach(r => {
      if(!r || !r.id || newResourceIds.has(r.id)) return;
      present.add(r.id);
      const record = stripped(r);
      if(!record.office) record.office = officeId;
      const json = JSON.stringify(record);
      if(baseline.get(r.id) !== json){
        SR.overlay.resources[r.id] = record;
        baseline.set(r.id, json);
      }
      const g = SR.groupOf(r.id);
      if(g && g.keeper === r.id && r.coverage){
        const was = SR.group(g.id);
        if(JSON.stringify([was.coverage, was.reasons || {}]) !== JSON.stringify([r.coverage, r.coverageReasons || {}])){
          setGroup(g.id, {...was, coverage:r.coverage, reasons:r.coverageReasons || {}});
        }
      }
    });
    viewIds.forEach(id => {
      if(present.has(id)) return;
      SR.overlay.resources[id] = null;
      removeFromGroup(id);
      baseline.delete(id);
    });
    viewIds = present;
    if(vocabularyOf(data) !== vocabularyBaseline){
      SR.overlay.vocabulary = JSON.parse(vocabularyOf(data));
      vocabularyBaseline = vocabularyOf(data);
    }
    const known = new Set(SR.overlay.changes.map(c => c.id));
    (data.changes || []).forEach(c => { if(!known.has(c.id)) SR.overlay.changes.push(c); });
    SR.overlay.deletionRequests[officeId] = data.deletionRequests || [];
    SR.saveOverlay();
  }

  const appPersist = persist;
  persist = function(){
    appPersist();
    syncFromView();
  };

  // Reload the app's data from the shared store, after a change to sharing itself.
  function reloadView(selectId){
    data = processResourcePackageData(SR.buildView(SR.office().id), { sourceName:"Shared resources" }).data;
    takeBaseline();
    appPersist();
    editing = null;
    editorSnapshot = "";
    selectedResourceId = selectId || "";
    adminResourceEditMode = !!selectId && getResourceIndexById(selectId) !== -1;
    adminTab = "resources";
    safeRenderAdmin();
  }

  // ---- The office ----
  getTsoName = () => SR.office().label;
  const officePicker = document.createElement("label");
  officePicker.className = "sr-office";
  officePicker.innerHTML = `Office<select>${SR.OFFICES.map(o => `<option value="${escapeHTML(o.id)}">${escapeHTML(o.label)}</option>`).join("")}</select>`;
  const officeSelect = officePicker.querySelector("select");
  officeSelect.value = SR.office().id;
  officeSelect.onchange = () => {
    if(!commitPendingEditsIfChanged()){
      officeSelect.value = SR.office().id;
      return;
    }
    SR.setOffice(officeSelect.value);
    location.reload();
  };
  officePicker.onclick = event => event.stopPropagation();
  // The title and the office share the title's place in the top bar.
  const titleCell = document.createElement("div");
  titleCell.className = "sr-title";
  const appTitleElement = document.getElementById("appTitle");
  appTitleElement.before(titleCell);
  titleCell.append(appTitleElement, officePicker);
  refreshAppTitle();

  // ---- No favourites (Elder Bendio, 25 October 2026) ----
  const appCreateResourceActionButtons = createResourceActionButtons;
  createResourceActionButtons = function(resource, options = {}){
    return appCreateResourceActionButtons(resource, {...options, showFavoriteToggle:false});
  };
  const appCreateTip = createTip;
  createTip = function(tipId){
    const tip = appCreateTip(tipId);
    const text = tip && tipId === "user" ? tip.querySelector(".red-tip-text") : null;
    if(text){
      text.textContent = "";
      text.append("Choose a category under “Browse by need,” or select “Find resources for” and choose one or more groups. Click a resource for details. Click ");
      const printer = createInterfaceIcon("printer");
      printer.classList.add("tip-inline-icon", "tip-printer-icon");
      text.append(printer, " to select it for printing.");
    }
    return tip;
  };
  if(view === "favorites") view = "categories";

  // Changes say which office made them.
  const appAddChangeEntry = addChangeEntry;
  addChangeEntry = function(entry){
    if(entry){
      entry.office = SR.office().id;
      entry.description = `${SR.office().label}: ${entry.description || ""}`.replace(/: $/, "");
    }
    appAddChangeEntry(entry);
  };

  // ---- Missionaries: the restriction on the card ----
  const restrictionText = r => [r.missionariesOnly ? "Missionaries only: not to be given out" : "", r.restriction || ""].filter(Boolean).join("; ");
  const appBuildResourceCard = buildResourceCard;
  buildResourceCard = function(res, options){
    const card = appBuildResourceCard(res, options);
    const text = restrictionText(res);
    const name = card.querySelector(".resource-main > strong");
    if(text && name){
      const line = document.createElement("div");
      line.className = "sr-restriction";
      line.textContent = text;
      name.after(line);
    }
    return card;
  };

  const appTogglePrintSelection = togglePrintSelection;
  togglePrintSelection = function(id, options){
    const r = data.resources.find(x => x.id === id);
    if(r && r.missionariesOnly && !isSelectedForPrinting(id)){
      alert("This resource is for missionaries only, so it is not printed.");
      return;
    }
    return appTogglePrintSelection(id, options);
  };

  // ---- Vetters: the resource list says which resources are shared ----
  const appPopulateResourceBrowseOptions = populateResourceBrowseOptions;
  populateResourceBrowseOptions = function(sel, preferredResourceId){
    appPopulateResourceBrowseOptions(sel, preferredResourceId);
    if(!sel) return;
    sel.querySelectorAll(".resource-listbox-option").forEach(btn => {
      const r = SR.resource(btn.dataset.resourceId);
      const g = SR.groupOf(btn.dataset.resourceId);
      if(g && g.keeper === btn.dataset.resourceId){
        btn.textContent += r && r.office !== SR.office().id ? ` — shared, ${SR.OFFICE[r.office].label}'s text` : " — shared";
      }
    });
  };

  // ---- Vetters: Coverage and restriction in the editor ----
  function servesText(s){
    if(!s) return "unknown";
    if(s.level === "national") return "nationwide";
    if(s.level === "state") return "statewide, " + s.state;
    return (s.counties || []).join(", ") + (s.state ? ", " + s.state : "");
  }
  const servesCounties = r => r.serves && r.serves.level === "local" && r.serves.state
    ? (r.serves.counties || []).map(c => r.serves.state + ":" + c) : [];
  // Counties a coverage reaches beyond where the resource serves: allowed, with a warning.
  function outsideServes(coverage, r){
    if(!coverage || coverage.level !== "county" || !r.serves || r.serves.level === "national") return [];
    if(r.serves.level === "state") return (coverage.counties || []).filter(c => !c.startsWith(r.serves.state + ":"));
    return (coverage.counties || []).filter(c => !servesCounties(r).includes(c));
  }

  function coverageControlsHTML(res, coverage){
    const counties = [...new Set([...SR.OFFICES.flatMap(SR.officeCounties), ...(coverage.counties || []), ...servesCounties(res)])].sort();
    const seeing = SR.officesSeeing(coverage).map(o => o.label);
    const lost = SR.officesSeeing(res.coverage).filter(o => !SR.covers(coverage, o)).map(o => o.label);
    const outside = outsideServes(coverage, res);
    const newOutside = outside.filter(c => !(res.coverageReasons || {})[c]);
    return `
      <div class="sr-checks">${[["national", "Nationwide"], ["state", "States"], ["county", "Counties"]].map(([value, label]) => `
        <label><input type="radio" name="sr_level" value="${value}" ${coverage.level === value ? "checked" : ""}> ${label}</label>`).join("")}</div>
      ${coverage.level === "state" ? `<div class="sr-checks">${STATES.map(st => `
        <label><input type="checkbox" class="srState" value="${st}" ${(coverage.states || []).includes(st) ? "checked" : ""}> ${st}</label>`).join("")}</div>` : ""}
      ${coverage.level === "county" ? STATES.map(st => [st, counties.filter(c => c.startsWith(st + ":"))]).filter(x => x[1].length).map(([st, cs]) => `
        <div class="sr-checks"><strong>${st}</strong> ${cs.map(c => `
          <label><input type="checkbox" class="srCounty" value="${escapeHTML(c)}" ${(coverage.counties || []).includes(c) ? "checked" : ""}> ${escapeHTML(c.split(":")[1])}</label>`).join("")}</div>`).join("") : ""}
      <div class="admin-note">Serves (reader's draft): ${escapeHTML(servesText(res.serves))}</div>
      <div><strong>Shown in:</strong> ${escapeHTML(seeing.join(", ") || "no office")}</div>
      ${lost.length ? `<div class="sr-warning">No longer shown in ${escapeHTML(lost.join(", "))}: their missionaries will not see it.</div>` : ""}
      ${outside.length ? `<div class="sr-warning">It does not serve ${escapeHTML(outside.map(countyLabel).join("; "))}, so missionaries there will see a resource outside its own area. That is allowed.</div>` : ""}
      ${Object.entries(res.coverageReasons || {}).filter(([c]) => (coverage.counties || []).includes(c)).map(([c, why]) => `
        <div class="admin-note">${escapeHTML(countyLabel(c))}: ${escapeHTML(why)}</div>`).join("")}
      ${newOutside.length ? `<label style="display:block; margin-top:6px;">Reason (optional), shown to the other offices<br>
        <input id="sr_reason" placeholder="e.g. Family shelter; Utah County has none" value="${escapeHTML(srReason)}"></label>` : ""}`;
  }

  function copiesHTML(res, g){
    const rows = g.members.map(SR.resource).filter(Boolean).map(c => `
      <tr><td>${escapeHTML(SR.OFFICE[c.office].label)}</td>
        <td>${escapeHTML(c.name)}<div class="admin-note">${escapeHTML([c.phone, c.website].filter(Boolean).join(" · "))}</div></td>
        <td>${c.id === g.keeper ? "<strong>Its text</strong>" : `
          <button class="button" type="button" data-sr-keeper="${escapeHTML(c.id)}">Use this copy's text</button>
          <button class="button" type="button" data-sr-unlink="${escapeHTML(c.id)}">Not the same</button>`}</td></tr>`).join("");
    const elsewhere = g.productionOnly && g.productionOnly.length
      ? `<div class="admin-note">Also held in production by ${escapeHTML(g.productionOnly.map(o => (SR.OFFICE[o] || {label:o}).label).join(", "))}, whose copies are not in this prototype's files.</div>` : "";
    return `<div style="margin-top:10px;"><strong>The same resource in each office</strong>
      <span class="admin-note">(matched ${escapeHTML(g.matchedBy)}; one copy's text is shown everywhere)</span>
      <div class="sr-scroll"><table class="sr-table"><tbody>${rows}</tbody></table></div>${elsewhere}</div>`;
  }

  let srCoverage = null, srReason = "";
  function sharedSectionHTML(res){
    const g = SR.groupOf(res.id);
    const officeId = SR.office().id;
    let sharing;
    if(g && g.keeper === res.id){
      srCoverage = JSON.parse(JSON.stringify(res.coverage));
      sharing = `<div id="sr_coverage">${coverageControlsHTML(res, srCoverage)}</div>${copiesHTML(res, g)}`;
    }else if(g){
      const keeper = SR.resource(g.keeper);
      sharing = `<p class="admin-note">${escapeHTML(SR.OFFICE[res.office].label)}'s copy of a resource shared with ${escapeHTML(keeper.name)}'s text from ${escapeHTML(SR.OFFICE[keeper.office].label)}. Its coverage leaves ${escapeHTML(SR.office().label)} out, so ${escapeHTML(SR.office().label)} shows this copy instead.</p>
        <button class="button" type="button" data-sr-unlink="${escapeHTML(res.id)}">Not the same</button>`;
    }else if(res.office === officeId && !newResourceIds.has(res.id)){
      sharing = `<p class="admin-note">Not shared: only ${escapeHTML(SR.office().label)} sees it. Serves (reader's draft): ${escapeHTML(servesText(res.serves))}.</p>
        <button class="button" type="button" data-sr-share="${escapeHTML(res.id)}">Share with other offices</button>`;
    }else{
      sharing = `<p class="admin-note">Not shared.</p>`;
    }
    return `
      <div style="margin-top:12px;">
        <strong>Coverage</strong> <span class="admin-note">(Which offices' missionaries see it.)</span>
        ${sharing}
        <label style="display:block; margin-top:10px;"><strong>Restriction</strong> <span class="admin-note">(Who is eligible, in words, e.g. "Provo residents only"; blank if anyone may use it.)</span><br>
          <input id="sr_restriction" value="${escapeHTML(res.restriction || "")}" style="width:100%;">
        </label>
        <label style="display:block; margin-top:6px;">
          <input type="checkbox" id="sr_missionaries_only" ${res.missionariesOnly ? "checked" : ""}>
          Missionaries only (shown to missionaries, never printed)
        </label>
        <div style="margin-top:10px;"><strong>Federal program run by each state</strong> <span class="admin-note">(Its front door in this state, for the Coverage tab.)</span><br>
          <span class="sr-checks">${SR.BASE.federalPrograms.map(p => `<label><input type="checkbox" class="srProgram" value="${escapeHTML(p)}" ${(res.federalPrograms || []).includes(p) ? "checked" : ""}> ${escapeHTML(p)}</label>`).join("")}</span>
        </div>
      </div><br>`;
  }

  // The app's editor sections, with Coverage and restriction after Categories.
  renderResourceEditorMarkup = function(res){
    srReason = "";
    const verifiedDisplay = formatVerifiedOnForDisplay(res.verifiedOn);
    const informationDraft = parseInformationText(res.informationText || "");
    return [
      renderResourceBasicsSection(res, verifiedDisplay),
      renderResourceUpdateSection(),
      renderResourceForGroupsSection(renderResourceForGroupChecks(res)),
      renderForGroupReviewSection(res),
      renderResourceCategoriesSection(renderResourceCategoryChecks(res)),
      sharedSectionHTML(res),
      renderResourcePDFSection(res),
      renderResourceInformationSection(informationDraft)
    ].join("");
  };

  const appEditResource = editResource;
  editResource = function(idx){
    appEditResource(idx);
    const res = data.resources[idx];
    const editor = document.getElementById("resEditor");
    if(!res || !editor) return;
    const validate = () => validateResourceEditorState(idx);
    ["sr_restriction"].forEach(id => { const el = document.getElementById(id); if(el) el.addEventListener("input", validate); });
    const mo = document.getElementById("sr_missionaries_only");
    if(mo) mo.addEventListener("change", validate);
    editor.querySelectorAll(".srProgram").forEach(cb => cb.addEventListener("change", validate));
    const box = document.getElementById("sr_coverage");
    if(box){
      box.addEventListener("input", event => {
        if(event.target.id === "sr_reason"){ srReason = event.target.value; validate(); }
      });
      box.addEventListener("change", event => {
        const t = event.target;
        if(t.name === "sr_level"){
          srCoverage = t.value === "national" ? {level:"national"}
            : t.value === "state" ? {level:"state", states:[(res.serves && res.serves.level !== "national" && res.serves.state) || SR.OFFICE[res.office].state]}
            : {level:"county", counties: servesCounties(res).length ? servesCounties(res) : SR.officeCounties(SR.OFFICE[res.office])};
        }else if(t.classList.contains("srState")){
          const set = new Set(srCoverage.states || []);
          t.checked ? set.add(t.value) : set.delete(t.value);
          srCoverage.states = [...set].sort();
        }else if(t.classList.contains("srCounty")){
          const set = new Set(srCoverage.counties || []);
          t.checked ? set.add(t.value) : set.delete(t.value);
          srCoverage.counties = [...set].sort();
        }else{
          return;
        }
        box.innerHTML = coverageControlsHTML(res, srCoverage);
        validate();
      });
    }
    editor.querySelectorAll("[data-sr-keeper],[data-sr-unlink],[data-sr-share]").forEach(btn => {
      btn.addEventListener("click", () => sharingAction(btn.dataset, res));
    });
    editorSnapshot = snapshotResourceEditor();
    validate();
  };

  const appResourceEditorDraft = resourceEditorDraft;
  resourceEditorDraft = function(){
    const draft = appResourceEditorDraft();
    if(!draft) return draft;
    const restriction = document.getElementById("sr_restriction");
    const mo = document.getElementById("sr_missionaries_only");
    draft.restriction = restriction ? restriction.value.trim() : "";
    draft.missionariesOnly = !!(mo && mo.checked);
    draft.federalPrograms = Array.from(document.querySelectorAll(".srProgram")).filter(cb => cb.checked).map(cb => cb.value);
    if(document.getElementById("sr_coverage")){
      draft.coverage = JSON.parse(JSON.stringify(srCoverage));
      draft.coverageReason = srReason.trim();
    }
    return draft;
  };

  const appApplyResourceDraft = applyResourceDraft;
  applyResourceDraft = function(idx, draft){
    const res = data.resources[idx];
    const before = res && res.coverage ? JSON.stringify(res.coverage) : "";
    appApplyResourceDraft(idx, draft);
    if(!res) return;
    res.restriction = draft.restriction || "";
    res.missionariesOnly = !!draft.missionariesOnly;
    res.federalPrograms = draft.federalPrograms || [];
    if(draft.coverage && JSON.stringify(draft.coverage) !== before){
      const reasons = {};
      const counties = draft.coverage.level === "county" ? draft.coverage.counties || [] : [];
      Object.entries(res.coverageReasons || {}).forEach(([c, why]) => { if(counties.includes(c)) reasons[c] = why; });
      if(draft.coverageReason) outsideServes(draft.coverage, res).forEach(c => { if(!reasons[c]) reasons[c] = draft.coverageReason; });
      res.coverage = draft.coverage;
      res.coverageReasons = reasons;
      const shown = SR.officesSeeing(draft.coverage).map(o => o.label).join(", ") || "no office";
      draft.updateDescription = [draft.updateDescription, `Coverage: shown in ${shown}.`, draft.coverageReason].filter(Boolean).join(" ");
    }
  };

  function sharingAction(dataset, res){
    if(!commitPendingEditsIfChanged()) return;
    const g = SR.groupOf(res.id);
    let select = res.id, note;
    if(dataset.srKeeper && g){
      setGroup(g.id, {...SR.group(g.id), keeper:dataset.srKeeper});
      const copy = SR.resource(dataset.srKeeper);
      note = `Now shows ${SR.OFFICE[copy.office].label}'s copy of ${copy.name}.`;
      select = dataset.srKeeper;
    }else if(dataset.srUnlink && g){
      const copy = SR.resource(dataset.srUnlink);
      if(!confirm(`Treat ${SR.OFFICE[copy.office].label}'s ${copy.name} as a different resource? It goes back to ${SR.OFFICE[copy.office].label} as its own resource.`)) return;
      removeFromGroup(dataset.srUnlink);
      note = `${SR.OFFICE[copy.office].label}'s ${copy.name} is not the same resource.`;
    }else if(dataset.srShare){
      const s = res.serves || {};
      const coverage = s.level === "national" ? {level:"national"}
        : s.level === "state" && s.state ? {level:"state", states:[s.state]}
        : {level:"county", counties: servesCounties(res).length ? servesCounties(res) : SR.officeCounties(SR.office())};
      setGroup("new-" + res.id, {keeper:res.id, members:[res.id], matchedBy:"shared by a vetter", productionOnly:[], coverage, reasons:{}});
      note = `Shared; shown in ${SR.officesSeeing(coverage).map(o => o.label).join(", ")}. Set its coverage to show it in other offices.`;
    }else{
      return;
    }
    SR.saveOverlay();
    reloadView(select);
    addChangeEntry(createChangeEntry("resource", "updated", res.id, res.name, note, { categoryIds:res.categories }));
    persist();
  }

  // ---- Vetters: the Coverage tab ----
  // Where: Nationwide, or one state. Nationwide lists the nationwide resources and each
  // state's front door to the federal programs states run; a state lists its nationwide
  // and statewide resources, then its counties against the county-level ones.
  const NATIONWIDE = "national";
  let covWhere = SR.office().state, covCat = "housing", covSub = "", covCounty = "";
  function coverageTabHTML(){
    const cat = data.categories.find(c => c.id === covCat) || data.categories[0];
    const subs = normalizeCategoryFilters(cat.filters);
    const inCat = r => (r.categories || []).includes(cat.id) && (!covSub || ((r.categoryFilters || {})[cat.id] || []).includes(covSub));
    const here = new Set(data.resources.map(r => r.id));
    const office = SR.office().label;
    const groups = SR.groupIds().map(id => ({id, ...SR.group(id)})).filter(g => SR.resource(g.keeper));
    const sharedIds = new Set(groups.flatMap(g => g.members));
    const all = SR.resourceIds().map(SR.resource);
    // A resource's name, opening the editor when this office's missionaries see it.
    const named = r => here.has(r.id)
      ? `<button class="button" type="button" data-sr-open="${escapeHTML(r.id)}">${escapeHTML(r.name)}</button>`
      : `<span title="Not shown in ${escapeHTML(office)}, so ${escapeHTML(office)} can't edit it">${escapeHTML(r.name)}</span>`;
    const rows = (items, describe) => items.length
      ? `<div class="sr-scroll"><table class="sr-table"><tbody>${items.map(x => `<tr><td>${x.html}</td>${x.text ? `<td>${describe(x)}</td>` : ""}</tr>`).join("")}</tbody></table></div>`
      : `<p class="admin-note">None.</p>`;
    const sharedRow = g => ({html:named(SR.resource(g.keeper)), text:""});
    const ownRow = r => ({html:named(r), text:`${escapeHTML(SR.OFFICE[r.office].label)} only`});

    let body;
    if(covWhere === NATIONWIDE){
      const national = groups.filter(g => g.coverage.level === "national" && inCat(SR.resource(g.keeper))).map(sharedRow);
      const programs = SR.BASE.federalPrograms;
      const stateOf = r => (r.serves && r.serves.state) || SR.OFFICE[r.office].state;
      const listsIn = st => SR.OFFICES.filter(o => o.state === st).map(o => o.label).join(" or ") + (SR.OFFICES.filter(o => o.state === st).length > 1 ? "'s lists" : "'s list");
      // A shared resource once, by the copy whose text is shown.
      const keepers = new Map(groups.map(g => [g.keeper, g]));
      const doors = (p, st) => all.filter(r => (r.federalPrograms || []).includes(p) && stateOf(r) === st
        && (!sharedIds.has(r.id) || keepers.has(r.id)));
      body = `
        <h4>Nationwide</h4>
        <p class="admin-note">Shown in every office.</p>
        ${rows(national, x => x.text)}
        <h4>Federal programs run by each state</h4>
        <p class="admin-note">Each state's front door: the resource where a person in that state applies. For every category; marked in the editor under "Federal program run by each state". A state with none needs its front door added to an office's list.</p>
        <div class="sr-scroll"><table class="sr-table">
          <thead><tr><th>Program</th>${STATES.map(st => `<th>${st}</th>`).join("")}</tr></thead>
          <tbody>${programs.map(p => `<tr><td>${escapeHTML(p)}</td>${STATES.map(st => {
            const found = doors(p, st);
            return `<td class="${found.length ? "" : "sr-gap"}">${found.length ? found.map(r => `<div style="margin:2px 0;">${named(r)}</div>`).join("") : `None in ${escapeHTML(listsIn(st))}`}</td>`;
          }).join("")}</tr>`).join("")}</tbody>
        </table></div>`;
    }else{
      const st = covWhere;
      const national = groups.filter(g => g.coverage.level === "national" && inCat(SR.resource(g.keeper))).map(sharedRow);
      const statewide = [
        ...groups.filter(g => g.coverage.level === "state" && (g.coverage.states || []).includes(st) && inCat(SR.resource(g.keeper))).map(sharedRow),
        ...all.filter(r => !sharedIds.has(r.id) && r.serves && r.serves.level === "state" && r.serves.state === st && inCat(r)).map(ownRow)
      ];
      const counties = [...new Set(SR.OFFICES.filter(o => o.state === st).flatMap(SR.officeCounties))].sort();
      const at = c => ({state:st, counties:[c.split(":")[1]]});
      const local = groups.filter(g => g.coverage.level === "county" && inCat(SR.resource(g.keeper)) && counties.some(c => SR.covers(g.coverage, at(c))));
      const own = c => all.filter(r => !sharedIds.has(r.id) && inCat(r) && !(r.serves && r.serves.level !== "local")
        && SR.officeCounties(SR.OFFICE[r.office]).includes(c)).sort(compareResourcesByName);
      const wide = national.length + statewide.length;
      body = `
        <h4>Nationwide (${national.length})</h4>${rows(national, x => x.text)}
        <h4>Statewide in ${st} (${statewide.length})</h4>${rows(statewide, x => x.text)}
        <h4>By county</h4>
        <p class="admin-note">Counties with an office down the side (each office's counties are a draft), the shared resources that cover counties across the top, and each county's local resources that are not shared: click a number to list them. A county with nothing here and nothing nationwide or statewide is a gap a missionary would otherwise find with someone in front of them.</p>
        <div class="sr-scroll"><table class="sr-table">
          <thead><tr><th>County</th><th>Local, not shared</th>${local.map(g => `<th>${named(SR.resource(g.keeper))}</th>`).join("")}</tr></thead>
          <tbody>${counties.map(c => {
            const mine = own(c), n = mine.length, hits = local.filter(g => SR.covers(g.coverage, at(c)));
            const count = n ? `<button class="button" type="button" data-sr-county="${escapeHTML(c)}" aria-expanded="${covCounty === c}">${n}</button>` : (hits.length || wide ? 0 : "none");
            const row = `<tr><td>${escapeHTML(countyLabel(c))}</td><td class="${n || hits.length || wide ? "" : "sr-gap"}">${count}</td>${local.map(g => `<td class="sr-yes">${hits.includes(g) ? "✓" : ""}</td>`).join("")}</tr>`;
            // A county's local resources, by name: those this office sees open in the editor,
            // where an office's own resource can be shared.
            const list = covCounty === c && n ? `<tr><td colspan="${2 + local.length}">${mine.map(r => `<div style="margin:4px 0;">${named(r)}
              <span class="admin-note">${escapeHTML(SR.OFFICE[r.office].label)}${((r.categoryFilters || {})[cat.id] || []).length ? " · " + escapeHTML(r.categoryFilters[cat.id].join(", ")) : ""}${r.vetted || r.verifiedOn ? "" : " · not yet reviewed"}</span></div>`).join("")}</td></tr>` : "";
            return row + list;
          }).join("")}</tbody>
        </table></div>`;
    }
    return `
      <div class="admin-panel"><div class="admin-box sr-coverage">
        <h3 class="admin-panel-title">Coverage</h3>
        <div class="sr-checks">
          <label>Where <select id="sr_cov_where"><option value="${NATIONWIDE}" ${covWhere === NATIONWIDE ? "selected" : ""}>Nationwide</option>${STATES.map(x => `<option ${x === covWhere ? "selected" : ""}>${x}</option>`).join("")}</select></label>
          <label>Category <select id="sr_cov_cat">${data.categories.slice().sort(compareCategoriesByLabel).map(c => `<option value="${escapeHTML(c.id)}" ${c.id === cat.id ? "selected" : ""}>${escapeHTML(c.label)}</option>`).join("")}</select></label>
          ${subs.length ? `<label>Subcategory <select id="sr_cov_sub"><option value="">All</option>${subs.map(x => `<option ${x === covSub ? "selected" : ""}>${escapeHTML(x)}</option>`).join("")}</select></label>` : ""}
        </div>
        ${body}
      </div></div>`;
  }

  const appRenderAdmin = renderAdmin;
  renderAdmin = function(){
    appRenderAdmin();
    const container = document.getElementById("adminView");
    const tabs = container.querySelector(".admin-nav-tabs");
    if(tabs){
      tabs.querySelectorAll("button").forEach(b => { if(adminTab === COVERAGE_TAB) b.classList.remove("primary"); });
      const button = document.createElement("button");
      button.className = "button" + (adminTab === COVERAGE_TAB ? " primary" : "");
      button.textContent = "Coverage";
      button.onclick = () => {
        if(adminTab === COVERAGE_TAB || !commitPendingEditsIfChanged()) return;
        adminResourceEditMode = false;
        adminTab = COVERAGE_TAB;
        safeRenderAdmin();
      };
      tabs.appendChild(button);
    }
    if(adminTab !== COVERAGE_TAB) return;
    editing = null;
    editorSnapshot = "";
    container.insertAdjacentHTML("beforeend", coverageTabHTML());
    container.querySelectorAll("#sr_cov_where, #sr_cov_cat, #sr_cov_sub").forEach(sel => {
      sel.onchange = () => {
        if(sel.id === "sr_cov_where") covWhere = sel.value;
        if(sel.id === "sr_cov_cat"){ covCat = sel.value; covSub = ""; }
        if(sel.id === "sr_cov_sub") covSub = sel.value;
        covCounty = "";
        safeRenderAdmin();
      };
    });
    container.querySelectorAll("[data-sr-county]").forEach(btn => {
      btn.onclick = () => {
        covCounty = covCounty === btn.dataset.srCounty ? "" : btn.dataset.srCounty;
        safeRenderAdmin();
      };
    });
    container.querySelectorAll("[data-sr-open]").forEach(btn => {
      btn.onclick = () => {
        selectedResourceId = btn.dataset.srOpen;
        adminResourceEditMode = true;
        adminTab = "resources";
        safeRenderAdmin();
      };
    });
  };

  // The app's own switch knows only its three tabs; leaving Coverage goes through it.
  const appSwitchAdminTab = switchAdminTab;
  switchAdminTab = function(nextTab){
    if(adminTab === COVERAGE_TAB && nextTab !== COVERAGE_TAB) adminTab = "";
    appSwitchAdminTab(nextTab);
  };

  safeRender();
})();
