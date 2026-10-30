'use strict';
const $ = selector => document.querySelector(selector);
const fmt = n => new Intl.NumberFormat('ru-RU').format(n) + ' ₽';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const productUrl = item =>
  (location.protocol === 'file:' ? 'product.html' : '/product')
  + '?product=' + encodeURIComponent(item.slug);
const categoryUrl = category =>
  (location.protocol === 'file:' ? 'index.html' : '/')
  + '?category=' + encodeURIComponent(category)
  + '#catalog';
function rewriteHomeLinks() {
  document.querySelectorAll('a[href]').forEach(link => {
    const raw = link.getAttribute('href');
    if (raw === '/' || raw.startsWith('/#') || raw.startsWith('index.html')) {
      const suffix = raw.startsWith('index.html') ? raw.slice(10) : raw.slice(1);
      link.setAttribute('href', (location.protocol === 'file:' ? 'index.html' : '/') + suffix);
    }
  });
}
rewriteHomeLinks();
let lastCartRemoval = null;
let toastVersion = 0;
function placeToast() {
  const el = $('#toast');
  const inside = !$('#overlay').hidden && el.dataset.undoAction === 'true';
  const destination = inside ? $('#cartNoticeSlot') : document.body;
  if (el.parentElement !== destination) destination.append(el);
  el.classList.toggle('in-cart', inside);
}
function showRemovalUndo(snapshot) {
  if (!snapshot || !Number.isSafeInteger(snapshot.quantity) || snapshot.quantity < 1) return;
  toast('Удалено из корзины', {undoAction:true, duration:5000});
  lastCartRemoval = {slug:snapshot.slug, quantity:snapshot.quantity};
}
async function undoRemoval() {
  if (!lastCartRemoval || pendingCartRestores.size) return;
  const snapshot = lastCartRemoval;
  const version = toastVersion;
  lastCartRemoval = null; // consume before awaiting; double activation cannot replay it
  $('#toastUndo').disabled = true;
  try {
    const response = await requestCartRestore(snapshot);
    if (version !== toastVersion) return; // preserve a newer removal/notification
    if (response?.result === 'restored') toast('Товар восстановлен');
    else if (response?.result === 'already-present') toast('Товар уже находится в корзине. Его количество сохранено.');
    else if (response?.result === 'refresh-failed') toast('Не удалось проверить наличие. Попробуйте обновить страницу.');
    else toast('Не удалось вернуть товар: его больше нет в наличии');
  } finally {
    $('#toastUndo').disabled = !!pendingCartRestores.size;
  }
}
window.addEventListener('cartremoved', event => showRemovalUndo(event.detail));
$('#toastUndo').addEventListener('click', event => { event.stopPropagation(); undoRemoval(); });


let toastTimer;
let toastDeadline = 0;
let toastRemaining = 4200;
function hideToast() {
  lastCartRemoval = null;
  toastVersion++;
  clearTimeout(toastTimer);
  toastTimer = null;
  $('#toast').classList.remove('show');
  $('#toast').hidden = true;
}
function pauseToast() {
  if (toastTimer == null) return;
  clearTimeout(toastTimer);
  toastTimer = null;
  toastRemaining = Math.max(0, toastDeadline - performance.now());
}
function resumeToast() {
  const el = $('#toast');
  if (el.hidden || el.matches(':hover') || el.contains(document.activeElement)) return;
  clearTimeout(toastTimer);
  toastDeadline = performance.now() + toastRemaining;
  toastTimer = setTimeout(hideToast, toastRemaining);
}
function toast(message, {cartAction = false, undoAction = false, duration = 4200} = {}) {
  hideToast();
  if ($('#overlay')?.classList.contains('open') && !undoAction) {
    if (!cartAction && typeof orderNotice === 'function') orderNotice(message);
    return;
  }
  const el = $('#toast');
  $('#toastMessage').textContent = message;
  $('#toastCart').hidden = !cartAction;
  $('#toastUndo').hidden = !undoAction;
  $('#toastUndo').disabled = !!pendingCartRestores.size;

  el.dataset.undoAction = String(undoAction);
  el.dataset.cartAction = String(cartAction);
  placeToast();
  el.hidden = false;
  el.classList.add('show');
  toastRemaining = duration;
  toastDeadline = performance.now() + toastRemaining;
  resumeToast();
}
$('#toast').addEventListener('mouseenter', pauseToast);
$('#toast').addEventListener('mouseleave', resumeToast);
$('#toast').addEventListener('focusin', pauseToast);
$('#toast').addEventListener('focusout', () => queueMicrotask(resumeToast));
$('#toast').addEventListener('click', () => {
  if (!$('#toast').hidden && $('#toast').dataset.cartAction === 'true') openCart();
});

function cartButtonState(item) {
  const unavailable = item.availability === false;
  const included = !unavailable && (cart[item.slug] || 0) > 0;
  return {
    label: unavailable ? 'Нет в наличии' : included ? 'Удалить из корзины' : 'Добавить в корзину',
    included,
    disabled: unavailable || !cartReady || pendingCartClear || pendingCartToggles.has(item.slug) || pendingCartRestores.has(item.slug)
  };
}
function cartButtonMarkup(item, productPage = false) {
  const state = cartButtonState(item);
  return `<button type="button" class="${productPage ? 'full-button product-add' : 'add'}${state.included ? ' is-in-cart' : ''}" data-add="${esc(item.slug)}" aria-pressed="${state.included}" aria-label="${esc(state.label)}: ${esc(item.name)}" ${state.disabled ? 'disabled' : ''}><span class="cart-label-full">${state.label}</span><span class="cart-label-short" aria-hidden="true" data-label="${item.availability === false ? 'Нет в наличии' : state.included ? 'Удалить' : 'В корзину'}"></span></button>`;
}
function updateCartButtons() {
  document.querySelectorAll('[data-add]').forEach(button => {
    const item = items.find(product => product.slug === button.dataset.add);
    if (!item) { button.disabled = true; button.textContent = 'Нет в наличии'; return; }
    const state = cartButtonState(item);
    button.querySelector('.cart-label-full').textContent = state.label;
    button.querySelector('.cart-label-short').dataset.label = item.availability === false ? 'Нет в наличии' : state.included ? 'Удалить' : 'В корзину';
    button.disabled = state.disabled;
    button.classList.toggle('is-in-cart', state.included);
    button.setAttribute('aria-pressed', String(state.included));
    button.setAttribute('aria-label', `${state.label}: ${item.name}`);
  });
}
window.addEventListener('cartbuttonschange', () => { updateCartButtons(); $('#clearCart').disabled = !cartReady || !Object.keys(cart).length || pendingCartClear; });

function availabilityMarkup(item) {
  if (item.availability === false) return '<p class="availability unavailable">Нет в наличии</p>';
  if (item.availability === true) return '<p class="availability">В наличии</p>';
  return '';
}
function cardMarkup(item) {
  return `<article class="product"><div class="image-box">${item.images.length ? `<img class="product-image" src="${esc(item.images[0])}" alt="Иллюстрация: ${esc(item.name)}" loading="lazy">` : '<span class="photo-placeholder">Фото пока не добавлено</span>'}<span class="tag" ${item.tag ? '' : 'hidden'}>${esc(item.tag)}</span></div><div class="product-info"><a class="species category-link" href="${categoryUrl(item.category)}">${esc(item.category)}</a><h3><a class="product-link" href="${productUrl(item)}" target="_blank" rel="noopener noreferrer">${esc(item.name)}</a></h3>${item.size ? `<p class="detail card-size">${esc(item.size)}</p>` : ''}${availabilityMarkup(item)}<div class="bottom"><div class="price"><small>Цена от</small>${fmt(item.price)}</div>${cartButtonMarkup(item)}</div></div></article>`;
}
document.addEventListener('error', event => {
  if (event.target.matches?.('.product-image, .gallery-image, #lightboxImage')) {
    event.target.classList.add('image-unavailable');
    event.target.alt = 'Фото недоступно. ' + event.target.alt;
  }
}, true);

function renderCart() {
  cart = cleanCart(cart);
  const entries = Object.entries(cart);
  $('#basketCount').textContent = entries.reduce((sum, [, n]) => sum + n, 0);
  $('#cartList').innerHTML = entries.length ? entries.map(([id, n]) => {
    const p = items.find(item => String(item.slug) === id);
    return `<div class="cart-item"><div><a href="${productUrl(p)}" target="_blank" rel="noopener noreferrer"><b>${esc(p.name)}</b></a><div class="cart-unit">${fmt(p.price)} / шт.</div><div class="cart-subtotal">${fmt(p.price * n)}</div></div><div class="qty"><button data-change="${esc(id)}" data-delta="-1" aria-label="Уменьшить количество: ${esc(p.name)}">−</button><span>${n}</span><button data-change="${esc(id)}" data-delta="1" aria-label="Увеличить количество: ${esc(p.name)}">+</button></div></div>`;
  }).join('') : '<p class="empty">Корзина пока пуста. Добавьте понравившиеся растения из каталога.</p>';
  $('#total').textContent = fmt(entries.reduce((sum, [id, n]) => sum + items.find(p => String(p.slug) === id).price * n, 0));
  $('#clearCart').disabled = !cartReady || !entries.length || pendingCartClear;
  if (!entries.length) $('#clearCartConfirm').hidden = true;
  $('#copyOrder').disabled = !cartReady || !entries.length;
  $('#manualOrder')?.remove();
  updateOrderActions();
  updateCartButtons();
}
document.addEventListener('click', async event => {
  const button = event.target.closest('[data-add], [data-change]');
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  const id = button.dataset.add ?? button.dataset.change;
  if (button.disabled || !items.some(item => item.slug === id && item.availability !== false)) return;
  if (button.hasAttribute('data-add')) {
    if (event.detail > 1) return;
    const result = await requestCartToggle(id);
    if (result?.result === 'added') toast('Добавлено в корзину', {cartAction:true});
    // Removal notifications use the exact snapshot returned by the storage frame.
  } else {
    await requestCartChange(id, Number(button.dataset.delta));
  }
});

// Use one accessible modal with focus restoration and keyboard containment.
let cartOpener;
const overlay = $('#overlay');
overlay.hidden = true;
function openCart() {
  const active = document.activeElement;
  cartOpener = active?.closest('#toast') ? $('#openCart') : active;
  if ($('#toast').dataset.undoAction !== 'true' || $('#toast').hidden) hideToast();
  renderCart();
  overlay.hidden = false;
  placeToast();
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
  $('#closeCart').focus();
}
$('#openCart').onclick = openCart;
function closeCart() {
  $('#clearCartConfirm').hidden = true;
  if (overlay.hidden) return;
  overlay.hidden = true;
  placeToast();
  overlay.classList.remove('open');
  document.body.style.overflow = '';
  const target = cartOpener?.isConnected && !cartOpener.disabled ? cartOpener : $('#openCart');
  target.focus();
}
$('#closeCart').onclick = closeCart;
overlay.addEventListener('click', event => { if (event.target === overlay) closeCart(); });
document.addEventListener('keydown', event => {
  if (overlay.hidden) return;
  if (event.key === 'Escape') closeCart();
  if (event.key === 'Tab') {
    const controls = [...overlay.querySelectorAll('button:not(:disabled), a[href], textarea')].filter(el => !el.hidden && el.getClientRects().length);
    const first = controls[0], last = controls.at(-1);
    if (!overlay.contains(document.activeElement)) {
      event.preventDefault();
      (event.shiftKey ? last : first)?.focus();
      return;
    }
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});
$('#clearCart').onclick = () => {
  if ($('#clearCart').disabled) return;
  $('#clearCartConfirm').hidden = false;
  $('#cancelClearCart').focus();
};
$('#cancelClearCart').onclick = () => { $('#clearCartConfirm').hidden = true; $('#clearCart').focus(); };
$('#confirmClearCart').onclick = async () => {
  if (pendingCartClear) return;
  $('#confirmClearCart').disabled = true;
  hideToast();
  try {
    await requestCartClear();
    $('#clearCartConfirm').hidden = true;
    $('#closeCart').focus();
  } finally { $('#confirmClearCart').disabled = false; }
};
$('#copyOrder').onclick = copyCurrentOrder;
$('#sendTelegram').onclick = sendOrderToTelegram;
$('#sendMax').onclick = sendOrderToMax;
window.addEventListener('cartchange', renderCart);
$('#year').textContent = new Date().getFullYear();
renderCart();

if ($('#products')) {
  const categoryFromUrl = () => new URLSearchParams(location.search).get('category') || 'all';
  let category = categoryFromUrl();
  const categories = [...new Set(items.map(item => item.category))];
  $('#filters').innerHTML = '<button class="chip" data-filter="all">Все категории</button>' + categories.map(name => `<button class="chip" data-filter="${esc(name)}">${esc(name)}</button>`).join('');
  const tags = [...new Set(items.flatMap(item => item.tags))].sort((a,b) => a.localeCompare(b, 'ru'));
  $('#tagFilterRow').hidden = !tags.length;
  $('#tagButtons').innerHTML = '<button class="chip active" data-tag="">Все</button>' + tags.map(tag => `<button class="chip" data-tag="${esc(tag)}">${esc(tag)}</button>`).join('');
  $('#tagFilter').innerHTML += tags.map(tag => `<option value="${esc(tag)}">${esc(tag)}</option>`).join('');
  // Do not restore this control from browser form history on a fresh page load.
  $('#inStockOnly').checked = true;

  function renderCatalog() {
    const query = $('#search').value.trim().toLocaleLowerCase('ru');
    const tag = $('#tagFilter').value;
    const inStockOnly = $('#inStockOnly').checked;
    const found = items.filter(item =>
      (category === 'all' || item.category === category) &&
      (!tag || item.tags.includes(tag)) &&
      (!inStockOnly || item.availability === true || item.availability === undefined) &&
      [item.name, item.category, ...item.tags].join(' ').toLocaleLowerCase('ru').includes(query)
    );
    $('#products').innerHTML = found.map(cardMarkup).join('');
    $('#tagButtons').querySelectorAll('[data-tag]').forEach(button => {
      button.classList.toggle('active', button.dataset.tag === tag);
      button.setAttribute('aria-pressed', String(button.dataset.tag === tag));
    });
    $('#resultCount').textContent = `Найдено растений: ${found.length}`;
    $('#noResults').hidden = !!found.length;
    $('#filters').querySelectorAll('[data-filter]').forEach(button => {
      const active = button.dataset.filter === category;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  }
  function revealCategory() {
    const row = $('#filters'), active = row.querySelector('.active');
    if (!active) return;
    const box = active.getBoundingClientRect(), bounds = row.getBoundingClientRect();
    if (box.left < bounds.left) row.scrollLeft += box.left - bounds.left;
    else if (box.right > bounds.right) row.scrollLeft += box.right - bounds.right;
  }
  window.addEventListener('resize', revealCategory);
  function scrollToCatalog(animate = true) {
    $('#catalog').scrollIntoView({block:'start', behavior:animate && !matchMedia('(prefers-reduced-motion: reduce)').matches ? 'smooth' : 'instant'});
  }
  function selectCategory(nextCategory) {
    category = nextCategory || 'all';
    const url = new URL(location.href);
    if (category === 'all') url.searchParams.delete('category');
    else url.searchParams.set('category', category);
    url.hash = 'catalog';
    if (url.href !== location.href) history.pushState(null, '', url.href);
    renderCatalog();
    revealCategory();
    scrollToCatalog();
  }
  $('#filters').addEventListener('click', event => {
    const button = event.target.closest('[data-filter]');
    if (button) selectCategory(button.dataset.filter);
  });
  // Category links from cards, navigation or other home-page blocks share one route.
  // Plain links back to this catalog preserve its current search, tags and stock state.
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
    const url = new URL(link.href, location.href);
    const homePath = new URL('index.html', location.href).pathname;
    if (url.origin !== location.origin || (url.pathname !== location.pathname && url.pathname !== homePath) || url.hash !== '#catalog') return;
    event.preventDefault();
    if (url.searchParams.has('category')) selectCategory(url.searchParams.get('category'));
    else scrollToCatalog();
  });
  window.addEventListener('popstate', () => {
    category = categoryFromUrl();
    renderCatalog();
    revealCategory();
    if (location.hash === '#catalog') scrollToCatalog();
  });
  $('#search').addEventListener('input', renderCatalog);
  $('#tagButtons').addEventListener('click', event => {
    const button = event.target.closest('[data-tag]');
    if (!button) return;
    $('#tagFilter').value = button.dataset.tag;
    renderCatalog();
  });
  $('#tagFilter').addEventListener('change', renderCatalog);
  $('#inStockOnly').addEventListener('change', renderCatalog);
  renderCatalog();
  requestAnimationFrame(revealCategory);
  document.fonts.ready.then(revealCategory);
  if (location.hash === '#catalog') requestAnimationFrame(() => scrollToCatalog(false));
}
