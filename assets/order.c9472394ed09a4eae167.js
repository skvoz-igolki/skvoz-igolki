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
  $('#sendVk').disabled = !cartReady || !order.entries.length || vkOrderBusy;
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

function showManualOrder(order) {
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
}

async function copyOrderText(order) {
  try {
    await navigator.clipboard.writeText(order.message);
  } catch {
    showManualOrder(order);
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

let vkOrderBusy = false;
function vkContactUrl() {
  try {
    const url = new URL(String(window.SHOP_CONFIG?.VK_CONTACT_URL || '').trim());
    // Only the documented direct-message format, not a profile or share link.
    if (url.protocol !== 'https:' || url.hostname !== 'vk.me' || url.port || url.username || url.password || !/^\/[A-Za-z0-9_][A-Za-z0-9_.]*\/?$/.test(url.pathname) || url.search || url.hash) return null;
    return url.href;
  } catch { return null; }
}
async function sendOrderToVk() {
  if (vkOrderBusy || !cartReady || !buildOrder().entries.length) return;
  const contact = vkContactUrl();
  if (!contact) {
    orderNotice('\u0421\u0432\u044f\u0437\u044c \u0447\u0435\u0440\u0435\u0437 \u0412\u041a\u043e\u043d\u0442\u0430\u043a\u0442\u0435 \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430. \u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 Telegram \u0438\u043b\u0438 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435.');
    return;
  }
  vkOrderBusy = true;
  $('#sendVk').disabled = true;
  try {
    const order = await currentOrder();
    if (!order.entries.length) {
      orderNotice('\u0412 \u043a\u043e\u0440\u0437\u0438\u043d\u0435 \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0445 \u0440\u0430\u0441\u0442\u0435\u043d\u0438\u0439 \u0434\u043b\u044f \u0437\u0430\u043a\u0430\u0437\u0430.');
      return;
    }
    const copied = await copyOrderText(order);
    const latest = await currentOrder();
    if (latest.message !== order.message || vkContactUrl() !== contact) {
      $('#manualOrder')?.remove();
      orderNotice('\u0417\u0430\u043a\u0430\u0437 \u0438\u0437\u043c\u0435\u043d\u0438\u043b\u0441\u044f \u0432\u043e \u0432\u0440\u0435\u043c\u044f \u043f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0438. \u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435, \u0447\u0442\u043e\u0431\u044b \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0439 \u0437\u0430\u043a\u0430\u0437.');
      return;
    }
    if (!copied) {
      showManualOrder(order);
      orderNotice('\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0437\u0430\u043a\u0430\u0437 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438. \u0421\u043a\u043e\u043f\u0438\u0440\u0443\u0439\u0442\u0435 \u0442\u0435\u043a\u0441\u0442 \u0432\u0440\u0443\u0447\u043d\u0443\u044e \u0438 \u0432\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0432 \u0434\u0438\u0430\u043b\u043e\u0433 \u0412\u041a\u043e\u043d\u0442\u0430\u043a\u0442\u0435');
      $('#manualOrder')?.focus();
      $('#manualOrder')?.select();
      return;
    }
    orderNotice('\u0417\u0430\u043a\u0430\u0437 \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d. \u0412\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0435\u0433\u043e \u0432 \u0434\u0438\u0430\u043b\u043e\u0433 \u0412\u041a\u043e\u043d\u0442\u0430\u043a\u0442\u0435 \u0438 \u043e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435');
    window.location.assign(contact);
  } catch {
    orderNotice('\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u0412\u041a\u043e\u043d\u0442\u0430\u043a\u0442\u0435. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u0435\u0440\u0435\u0439\u0442\u0438 \u0432 \u0434\u0438\u0430\u043b\u043e\u0433 \u0441\u0430\u043c\u043e\u0441\u0442\u043e\u044f\u0442\u0435\u043b\u044c\u043d\u043e: ' + contact);
  } finally {
    vkOrderBusy = false;
    $('#sendVk').disabled = !cartReady || !buildOrder().entries.length;
  }
}
