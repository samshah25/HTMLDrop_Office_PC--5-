// Rating & Review - HTML Drop version: picks the engine for each question (30 Oct 2026).
//   cells.js  : pre-computed numbers (~4 MB), instant; used whenever it can answer exactly
//   engine.js : full DuckDB-WASM engine on docid-level rows (~76 MB, same SQL as server.py); loaded only when needed
//               (City / State filters, review limits that cut a review bin, other sources' tiles under a rating/review filter)
// Once the full engine is loaded, it also answers the views where the fast path would leave tiles empty.
import * as C from './cells.js';

const BASE = new URL('./', import.meta.url).href;
let status = () => {}, full = null, fullReady = false;

export async function init(onStatus = () => {}) {
  status = onStatus;
  status('Loading the dashboard...');
  await C.init(BASE);
  status('');
}

export function loadFull() {
  if (!full) {
    full = (async () => {
      const E = await import('./engine.js');
      await E.init(t => status(t ? t + ' - needed for City, State and exact review limits; the rest of the dashboard works without it' : ''));
      fullReady = true;
      return E;
    })();
    full.catch(() => { full = null; status(''); });
  }
  return full;
}

export const isFullReady = () => fullReady;

export async function stats(p) {
  if (C.canAnswer(p)) {
    const r = C.stats(p);
    if (!fullReady || !r.sources.some(s => s.unavailable)) return r;
  }
  return (await loadFull()).stats(p);
}
