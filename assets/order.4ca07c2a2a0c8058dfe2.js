'use strict';

function normalizePublicSiteUrl(value, fromLocation = false) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !url.hostname || url.username || url.password) return null;
    if (fromLocation) { url.search = ''; url.hash = ''; }
    else if (url.search || url.hash) return null;
    // Both a configured directory and an index/product HTML address resolve to
    // the containing site directory, retaining its host and deployment subfolder.
    if (fromLocation && /\/product\/?$/.test(url.pathname)) url.pathname = url.pathname.replace(/\/product\/?$/, '/');
    else if (/\.html?$/i.test(url.pathname)) url.pathname = url.pathname.slice(0, url.pathname.lastIndexOf('/') + 1);
    else if (!url.pathname.endsWith('/')) url.pathname += '/';
    return url.href;
  } catch { return null; }
}

function publicSiteUrl() {
  // Read at call time, so a config that loaded later is not cached as empty.
  const value = String(window.SHOP_CONFIG?.SITE_URL || '').trim();
  if (value) return normalizePublicSiteUrl(value);
  if (location.protocol === 'https:') return normalizePublicSiteUrl(location.href, true);
  return null; // Never share a buyer's local file:// path.
}

function publicProductUrl(product, base = publicSiteUrl()) {
  if (!base || !product?.slug) return null;

  const url = new URL(
    'product?product=' + encodeURIComponent(product.slug),
    base
  );

  return url.protocol === 'https:' ? url.href : null;
}

function telegramChatUrl() {
  const username = String(window.SHOP_CONFIG?.TELEGRAM_USERNAME || '').replace(/^@/, '').trim();
  return /^[A-Za-z0-9_]+$/.test(username) ? 'https://t.me/' + encodeURIComponent(username) : null;
}

function buildOrder() {
  // Store only slugs and quantities; names/prices/availability always come from items.
  const state = cleanCart(cart);
  const entries = Object.entries(state).map(([slug, quantity]) => ({product:items.find(p => p.slug === slug), quantity}));
  const base = publicSiteUrl();
  const total = entries.reduce((sum, {product, quantity}) => sum + product.price * quantity, 0);
  const message = entries.length ? 'Здравствуйте! Хочу уточнить наличие и заказать следующие растения в магазине «Сквозь иголки».\n\n' + entries.map(({product, quantity}, index) => {
    const lines = [
      `${index + 1}. ${product.name}`,
      `Количество: ${quantity} шт.`,
      `Цена: ${fmt(product.price)}/шт.`,
      `Сумма: ${fmt(product.price * quantity)}`
    ];
    const link = publicProductUrl(product, base);
    if (link) lines.push('Ссылка: ' + link);
    return lines.join('\n');
  }).join('\n\n') + `\n\nИтого: ${fmt(total)}\n\nПодскажите, пожалуйста, наличие растений и условия доставки.` : '';
  const chat = telegramChatUrl();
  return {message, total, entries, hasPublicUrl:!!base, chatUrl:chat,
    telegramUrl:chat && message ? chat + '?text=' + encodeURIComponent(message) : null};
}

function orderNotice(message) {
  $('#orderNotice').textContent = message;
  $('#orderNotice').hidden = !message;
}

function updateOrderActions() {
  const order = buildOrder();
  $('#sendTelegram').disabled = !cartReady || !order.entries.length;
  $('#sendMax').disabled = !cartReady || !order.entries.length || maxOrderBusy;
  updateMaxContact();
  $('#maxShareFallback').hidden = true;
  $('#maxShareFallback').removeAttribute('href');
  $('#telegramFallback').hidden = true;
  $('#telegramFallback').removeAttribute('href');
  if (!order.entries.length) orderNotice('');
  else if (!order.hasPublicUrl) orderNotice('Ссылки на растения не добавлены: публичный адрес сайта ещё не настроен. Заказ можно отправить в Telegram или скопировать без ссылок.');
  else if (!order.chatUrl) orderNotice('Укажите контакт продавца TELEGRAM_USERNAME в site-config.js. Заказ можно скопировать.');
  else orderNotice('');
}

async function currentOrder() {
  await cartInitialized;
  await cartRequest('read');
  cart = cleanCart(cart);
  return buildOrder();
}

async function copyOrderText(order) {
  try {
    await navigator.clipboard.writeText(order.message);
  } catch {
    // Keep a single selectable fallback inside the cart modal.
    let textarea = $('#manualOrder');
    if (!textarea) {
      textarea = document.createElement('textarea');
      textarea.id = 'manualOrder';
      textarea.className = 'order-fallback';
      textarea.readOnly = true;
      textarea.setAttribute('aria-label', 'Текст заказа для ручного копирования');
      $('#manualOrderContainer').append(textarea);
    }
    textarea.value = order.message;
    textarea.focus();
    textarea.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch {}
    if (!copied) {
      orderNotice('Автоматическое копирование запрещено браузером. Выделенный текст заказа можно скопировать вручную и вставить в чат продавца.');
      return false;
    }
  }
  $('#manualOrder')?.remove();
  toast(order.hasPublicUrl ? 'Заказ скопирован — вставьте его в чат продавца' : 'Заказ скопирован без ссылок: публичный адрес сайта ещё не настроен');
  return true;
}

async function copyCurrentOrder() {
  const order = await currentOrder();
  if (!order.entries.length) { orderNotice('В корзине нет доступных растений для заказа.'); return; }
  return copyOrderText(order);
}

async function sendOrderToTelegram() {
  // Reserve a tab during the user gesture so refreshing storage does not lose
  // popup permission. Never navigate to Telegram until the order is validated.
  const initial = buildOrder();
  if (!cartReady || !initial.entries.length) return;
  if (!initial.chatUrl) { updateOrderActions(); return; }
  let tab = null;
  try {
    tab = window.open('about:blank', '_blank');
    if (tab) {
      tab.opener = null;
      tab.document.title = 'Подготовка заказа';
      tab.document.body.textContent = 'Подготавливаем заказ для Telegram…';
    }
  } catch { tab = null; }
  try {
    const order = await currentOrder();
    if (!order.entries.length || !order.telegramUrl) { tab?.close(); updateOrderActions(); return; }
    // Telegram clients can trim drafts. Preserve the full order via manual copy
    // instead of silently opening a truncated long draft.
    if (Array.from(order.message).length > 4000) {
      tab?.close();
      orderNotice('Заказ слишком длинный для надёжной передачи в ссылке Telegram. Скопируйте его целиком и вставьте в чат; при необходимости отправьте частями.');
      $('#copyOrder').focus();
      return;
    }
    const fallback = $('#telegramFallback');
    fallback.href = order.telegramUrl;
    fallback.hidden = false;
    if (tab && !tab.closed) {
      // No automatic submission and no cart clearing: only open a prepared draft.
      tab.location.replace(order.telegramUrl);
      orderNotice('Подготовлен переход в Telegram. Проверьте заказ и отправьте его самостоятельно. Если текст не появился, скопируйте заказ и вставьте его в чат.');
    } else {
      orderNotice('Браузер заблокировал новую вкладку. Нажмите «Открыть Telegram» ниже или скопируйте заказ и откройте чат.');
      fallback.focus();
    }
  } catch {
    tab?.close();
    orderNotice('Не удалось подготовить переход. Скопируйте заказ и откройте чат продавца.');
  }
}

let maxOrderBusy = false;
function maxContactUrl() {
  try {
    const url = new URL(String(window.SHOP_CONFIG?.MAX_CONTACT_URL || '').trim());
    // Use the exact contact link copied from MAX, never construct one from a phone/name.
    if (url.protocol !== 'https:' || url.hostname !== 'max.ru' || url.port || url.username || url.password || !new RegExp('^/u/[A-Za-z0-9_-]+/?$').test(url.pathname) || url.search || url.hash) return null;
    return url.href;
  } catch { return null; }
}
// Local conservative URL-size guard, not a documented MAX service limit.
const MAX_SHARE_URL_LIMIT = 8000;
function maxShareUrl(order) {
  if (!order.entries.length || !order.message) return null;
  const url = 'https://max.ru/:share?text=' + encodeURIComponent(order.message);
  return url.length <= MAX_SHARE_URL_LIMIT ? url : null;
}
function updateMaxContact() {
  const contact = maxContactUrl();
  const link = $('#maxFallback');
  link.hidden = !contact;
  if (contact) link.href = contact;
  else link.removeAttribute('href');
}
async function sendOrderToMax() {
  if (maxOrderBusy || !cartReady || !buildOrder().entries.length) return;
  maxOrderBusy = true;
  $('#sendMax').disabled = true;
  updateMaxContact();
  const fallback = $('#maxShareFallback');
  fallback.hidden = true;
  fallback.removeAttribute('href');
  // Preserve the user gesture before refreshing shared storage.
  let tab = null;
  try {
    tab = window.open('about:blank', '_blank');
    if (tab) tab.opener = null;
  } catch { tab?.close(); tab = null; }
  try {
    const order = await currentOrder();
    if (!order.entries.length) {
      tab?.close();
      orderNotice('В корзине нет доступных растений для заказа.');
      return;
    }
    const url = maxShareUrl(order);
    if (!url) {
      tab?.close();
      orderNotice('Заказ слишком длинный для надёжной передачи ссылкой. Скопируйте заказ и вставьте его вручную в чат продавца в MAX.');
      $('#copyOrder').focus();
      return;
    }
    fallback.href = url;
    fallback.hidden = false;
    const instruction = 'В MAX выберите чат продавца, проверьте текст заказа и отправьте его самостоятельно. Если текст не появился, скопируйте заказ и вставьте его вручную.';
    if (tab && !tab.closed) {
      tab.location.replace(url);
      orderNotice(instruction);
    } else {
      orderNotice('Новая вкладка не открылась. Нажмите «Открыть MAX с заказом» ниже. ' + instruction);
      fallback.focus();
    }
  } catch {
    tab?.close();
    fallback.hidden = true;
    fallback.removeAttribute('href');
    orderNotice('Не удалось подготовить переход в MAX. Попробуйте скопировать заказ и открыть профиль продавца.');
  } finally {
    maxOrderBusy = false;
    $('#sendMax').disabled = !cartReady || !buildOrder().entries.length;
  }
}
