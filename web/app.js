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

function openSeed(seed) {
  document.querySelector('#record-name').textContent = seed.name;
  document.querySelector('#record-json').textContent = JSON.stringify(seed.fullRecord, null, 2);
  document.querySelector('#record-dialog').showModal();
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
