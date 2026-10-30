'use strict';
let cart = Object.create(null);
let cartReady = false;
const cartFrame = document.createElement('iframe');
cartFrame.hidden = true;
cartFrame.title = 'Локальное хранилище корзины';
cartFrame.src = location.protocol === 'file:' ? 'cart-storage.html' : 'cart-storage.1b86db9bd843002e4417.html';
let cartSequence = 0;
const cartRequests = new Map();
let resolveCartReady;
const cartInitialized = new Promise(resolve => { resolveCartReady = resolve; });
function cleanCart(value) {
  const result = Object.create(null);
  if (!value || typeof value !== 'object' || Array.isArray(value)) return result;
  for (const item of items) {
    const count = value[item.slug];
    if (item.availability !== false && Number.isSafeInteger(count) && count > 0) result[item.slug] = Math.min(count, 999);
  }
  return result;
}
function cartRequest(action, fields = {}) {
  const requestId = ++cartSequence;
  return new Promise(resolve => {
    cartRequests.set(requestId, resolve);
    cartFrame.contentWindow.postMessage({type:'skvoz-cart-request', requestId, action, ...fields}, '*');
  });
}
async function requestCartChange(slug, delta) {
  if (!items.some(item => item.slug === slug && item.availability !== false) || (delta !== 1 && delta !== -1)) return;
  if (pendingCartRestores.has(slug)) return {result:'busy'};
  await cartInitialized;
  return cartRequest('change', {slug, delta});
}
// Only an operation lock, never a second copy of cart membership.
const pendingCartToggles = new Set();
async function requestCartToggle(slug) {
  if (!items.some(item => item.slug === slug && item.availability !== false)) return {result:'rejected'};
  if (pendingCartToggles.has(slug) || pendingCartRestores.has(slug)) return {result:'busy'};
  pendingCartToggles.add(slug);
  window.dispatchEvent(new Event('cartbuttonschange'));
  const started = performance.now();
  try {
    await cartInitialized;
    return await cartRequest('toggle', {slug});
  } finally {
    setTimeout(() => {
      pendingCartToggles.delete(slug);
      window.dispatchEvent(new Event('cartbuttonschange'));
    }, Math.max(0, 500 - (performance.now() - started)));
  }
}

let pendingCartClear = false;
async function requestCartClear() {
  if (pendingCartClear) return {result:'busy'};
  pendingCartClear = true;
  window.dispatchEvent(new Event('cartbuttonschange'));
  try {
    await cartInitialized;
    return await cartRequest('clear');
  } finally {
    pendingCartClear = false;
    window.dispatchEvent(new Event('cartbuttonschange'));
  }
}
const pendingCartRestores = new Set();
async function requestCartRestore(snapshot) {
  if (pendingCartRestores.size) return {result:'busy'};
  if (!snapshot || typeof snapshot.slug !== 'string' || !Number.isSafeInteger(snapshot.quantity) || snapshot.quantity < 1 || snapshot.quantity > 999) return {result:'rejected'};
  const {slug, quantity} = snapshot;
  pendingCartRestores.add(slug);
  window.dispatchEvent(new Event('cartbuttonschange'));
  try {
    await cartInitialized;
    return await cartRequest('restore', {slug, quantity});
  } finally {
    pendingCartRestores.delete(slug);
    window.dispatchEvent(new Event('cartbuttonschange'));
  }
}

window.addEventListener('message', event => {
  if (event.source !== cartFrame.contentWindow) return;
  if (event.data?.type === 'skvoz-cart-ready') {
    let legacy = {};
    try { legacy = JSON.parse(localStorage.getItem('skvoz-igolki.cart.v1')) || {}; } catch {}
    cartRequest('init', {legacy});
  }
  if (event.data?.type === 'skvoz-cart-state') {
    const status = event.data.productStatus;
    if (status && typeof status.slug === 'string') {
      const item = items.find(p => p.slug === status.slug);
      if (item) {
        if (!status.exists) item.availability = false;
        else {
          item.availability = status.availability;
          if (Number.isFinite(status.price) && status.price >= 0) item.price = status.price;
        }
      }
    }
    cart = cleanCart(event.data.cart);
    cartReady = true;
    resolveCartReady();
    cartRequests.get(event.data.requestId)?.(event.data);
    cartRequests.delete(event.data.requestId);
    window.dispatchEvent(new Event('cartchange'));
    if (event.data.removed) window.dispatchEvent(new CustomEvent('cartremoved', {detail:event.data.removed}));
    if (!event.data.persistent && !window.cartStorageWarned) {
      window.cartStorageWarned = true;
      if (typeof toast === 'function') toast('Браузер запретил хранение корзины. Разрешите локальное хранилище для сохранения товаров.');
    }
  }
});
document.body.append(cartFrame);
// storage provides live updates; refresh also covers suspended/background tabs.
window.addEventListener('focus', () => { if (cartReady) cartRequest('read'); });
window.addEventListener('pageshow', () => { if (cartReady) cartRequest('read'); });
document.addEventListener('visibilitychange', () => { if (!document.hidden && cartReady) cartRequest('read'); });
