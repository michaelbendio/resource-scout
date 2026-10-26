// ============================================================
// SHARED RESOURCES PROTOTYPE: DATA (runs before the app)
// ============================================================
// The page holds every office's resources once, and each shared resource once.
// Before the app starts, this puts the chosen office's view in the app's starter data,
// so the app opens on what that office's missionaries see: its own resources, and each
// shared resource whose coverage reaches one of its counties. The view is never saved
// in the browser (the app's saved-data key reads as empty and is not written): a whole
// office is too big for the storage a browser gives local files, and another office's
// page may be using it. Changes made in the app are written back by shared-layer.js into
// OVERLAY_KEY, a small record of what differs from the built data.
(function(){
  const BASE = JSON.parse(document.getElementById("shared-data").textContent);
  const OVERLAY_KEY = "sharedResourcesPrototype:" + BASE.built;
  const VIEW_KEY = "sharedResourcesData";
  const OFFICES = BASE.offices;
  const OFFICE = Object.fromEntries(OFFICES.map(o => [o.id, o]));

  let overlay;
  try{ overlay = JSON.parse(localStorage.getItem(OVERLAY_KEY) || "null"); }catch(_err){ overlay = null; }
  overlay = overlay || {};
  overlay.office = OFFICE[overlay.office] ? overlay.office : "provo";
  overlay.resources = overlay.resources || {};
  overlay.shared = overlay.shared || {};
  overlay.changes = overlay.changes || [];
  overlay.deletionRequests = overlay.deletionRequests || {};

  function saveOverlay(){
    try{
      localStorage.setItem(OVERLAY_KEY, JSON.stringify(overlay));
      return true;
    }catch(err){
      alert("The prototype could not save this change in the browser: " + err.message);
      return false;
    }
  }

  const resource = id => (id in overlay.resources ? overlay.resources[id] : BASE.resources[id]) || null;
  const resourceIds = () => [...new Set([...Object.keys(BASE.resources), ...Object.keys(overlay.resources)])].filter(resource);
  const group = id => (id in overlay.shared ? overlay.shared[id] : BASE.shared[id]) || null;
  const groupIds = () => [...new Set([...Object.keys(BASE.shared), ...Object.keys(overlay.shared)])].filter(group);
  function groupOf(resourceId){
    return groupIds().map(id => ({id, ...group(id)})).find(g => g.members.includes(resourceId)) || null;
  }

  const officeCounties = o => o.counties.map(c => o.state + ":" + c);
  function covers(coverage, office){
    if(!coverage) return false;
    if(coverage.level === "national") return true;
    if(coverage.level === "state") return (coverage.states || []).includes(office.state);
    return (coverage.counties || []).some(c => officeCounties(office).includes(c));
  }
  const officesSeeing = coverage => OFFICES.filter(o => covers(coverage, o));

  // An office sees its own resources, and each shared resource (its keeper's record)
  // whose coverage reaches it. Its own copy of a shared resource is hidden then.
  function visibleIds(officeId){
    const office = OFFICE[officeId];
    const ids = [];
    const groups = groupIds().map(group);
    const hidden = new Set(groups.filter(g => covers(g.coverage, office)).flatMap(g => g.members));
    resourceIds().forEach(id => {
      if(resource(id).office === officeId && !hidden.has(id)) ids.push(id);
    });
    groups.forEach(g => {
      if(covers(g.coverage, office) && resource(g.keeper)) ids.push(g.keeper);
    });
    return [...new Set(ids)];
  }

  const vocabulary = () => overlay.vocabulary || BASE.vocabulary;

  // The view in the app's package shape. A shared resource's record carries its
  // coverage while it is in the app, so the editor can change it like any field.
  function buildView(officeId){
    const ids = visibleIds(officeId);
    const idSet = new Set(ids);
    const resources = ids.map(id => {
      const record = JSON.parse(JSON.stringify(resource(id)));
      const g = groupOf(id);
      if(g && g.keeper === id){
        record.coverage = JSON.parse(JSON.stringify(g.coverage));
        record.coverageReasons = JSON.parse(JSON.stringify(g.reasons || {}));
      }
      return record;
    });
    const v = vocabulary();
    return {
      resourcePackageSchemaVersion: 4,
      categoryPresetVersion: 1,
      categories: JSON.parse(JSON.stringify(v.categories)),
      forGroups: v.forGroups.slice(),
      forGroupDefinitions: JSON.parse(JSON.stringify(v.forGroupDefinitions)),
      resources,
      changes: overlay.changes.filter(c => c.type === "category" || idSet.has(c.targetId)),
      deletionRequests: overlay.deletionRequests[officeId] || [],
      deletions: []
    };
  }

  const storageGet = Storage.prototype.getItem, storageSet = Storage.prototype.setItem;
  Storage.prototype.getItem = function(key){ return key === VIEW_KEY ? null : storageGet.call(this, key); };
  Storage.prototype.setItem = function(key, value){ if(key !== VIEW_KEY) storageSet.call(this, key, value); };

  window.SR = {
    BASE, OFFICES, OFFICE, overlay, saveOverlay, resource, resourceIds, group, groupIds, groupOf,
    officeCounties, covers, officesSeeing, visibleIds, vocabulary, buildView,
    office: () => OFFICE[overlay.office],
    setOffice(id){ overlay.office = id; saveOverlay(); }
  };

  document.getElementById("seed-data").textContent = JSON.stringify(buildView(overlay.office));
})();
