'use strict';
// All pages use this one local file's storage, including file:// tabs with noopener.
(() => {
  const KEY = 'skvoz-igolki.cart.v2';
  let memory = {};
  let persistent = true;
  function clean(value) {
    const result = Object.create(null);
    if (!value || typeof value !== 'object' || Array.isArray(value)) return result;
    for (const item of items) {
      const count = value[item.slug] ?? value[item.legacyId];
      if (item.availability !== false && Number.isSafeInteger(count) && count > 0) result[item.slug] = Math.min(count, 999);
    }
    return result;
  }
  function read() {
    if (!persistent) return clean(memory);
    let serialized;
    try { serialized = localStorage.getItem(KEY); }
    catch { persistent = false; return clean(memory); }
    try { return clean(JSON.parse(serialized)); }
    catch { return Object.create(null); }
  }
  function write(value) {
    memory = clean(value);
    try { localStorage.setItem(KEY, JSON.stringify(memory)); }
    catch { persistent = false; }
  }
  async function refreshCatalog() {
    window.CATALOG = null; // an empty/broken script must not validate the old catalog
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'catalog.generated.js?cart-restore=' + Date.now() + '-' + Math.random().toString(36).slice(2);
      script.onload = () => { script.remove(); resolve(); };
      script.onerror = () => { script.remove(); reject(new Error('Catalog unavailable')); };
      document.head.append(script);
    });
    if (!Array.isArray(window.CATALOG)) throw new Error('Invalid catalog');
    // The storage frame only needs slug, quantity limits and current availability.
    items.splice(0, items.length, ...window.CATALOG);
  }
  async function serializeMutation(operation) {
    // The canonical file/origin shares this lock between frames/tabs where supported.
    if (!navigator.locks?.request) return operation();
    try { return await navigator.locks.request('skvoz-igolki.cart.v2.mutation', operation); }
    catch (error) {
      if (error.name === 'SecurityError' || error.name === 'NotSupportedError') return operation();
      throw error;
    }
  }

  function reply(requestId, result, removed, productStatus) {
    parent.postMessage({type:'skvoz-cart-state', requestId, result, removed, productStatus, cart:read(), persistent}, '*');
  }
  window.addEventListener('message', async event => {
    if (event.source !== parent || event.data?.type !== 'skvoz-cart-request') return;
    const {action, requestId, slug, delta, legacy, quantity} = event.data;
    await serializeMutation(async () => {
    let result, removed, productStatus;
    if (action === 'init') {
      let exists = false;
      try { exists = localStorage.getItem(KEY) !== null; } catch { persistent = false; }
      if (!exists) {
        let previous = legacy;
        try { previous = JSON.parse(localStorage.getItem('skvoz-igolki.cart.v1')) || previous; } catch {}
        write(clean(previous));
      } else {
        // On a fresh page, permanently remove unavailable/deleted positions.
        // Do not write during storage-event reads: another open tab may still
        // have an older catalog until it is refreshed.
        write(read());
      }
    } else if (action === 'clear') {
      write({});
      result = 'cleared';
    } else if (action === 'change') {
      const item = items.find(p => p.slug === slug);
      if (item && item.availability !== false && (delta === 1 || delta === -1)) {
        const next = read();
        const previous = next[slug] || 0;
        const count = Math.min(999, Math.max(0, previous + delta));
        if (previous > 0 && count === 0) removed = {slug, quantity:previous};
        if (count) next[slug] = count; else delete next[slug];
        write(next);
      }
    } else if (action === 'toggle') {
      const item = items.find(p => p.slug === slug);
      if (item && item.availability !== false) {
        const next = read();
        if (next[slug] > 0) { removed = {slug, quantity:next[slug]}; delete next[slug]; result = 'removed'; }
        else { next[slug] = 1; result = 'added'; }
        write(next);
      } else result = 'rejected';
    } else if (action === 'restore') {
      try { await refreshCatalog(); }
      catch { reply(requestId, 'refresh-failed'); return; }
      const item = items.find(p => p.slug === slug);
      productStatus = {slug, exists:!!item, availability:item?.availability, price:item?.price};
      if (!item || item.availability === false || !Number.isSafeInteger(quantity) || quantity < 1 || quantity > 999) result = 'rejected';
      else {
        const next = read();
        if (next[slug] > 0) result = 'already-present';
        else { next[slug] = quantity; write(next); result = 'restored'; }
      }
    } else if (action !== 'read') return;
    reply(requestId, result, removed, productStatus);
    });
  });
  window.addEventListener('storage', event => { if (event.key === KEY || event.key === null) reply(); });
  parent.postMessage({type:'skvoz-cart-ready'}, '*');
})();
