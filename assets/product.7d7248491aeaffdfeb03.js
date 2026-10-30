'use strict';
(() => {
  const slug = new URLSearchParams(location.search).get('product');
  const item = items.find(p => p.slug === slug);
  if (!item) {
    document.title = 'Растение не найдено — Сквозь иголки';
    $('#breadcrumbName').textContent = 'Растение не найдено';
    $('#productDetail').innerHTML = '<section class="product-error"><div class="kicker">КАТАЛОГ РАСТЕНИЙ</div><h1>Растение не найдено</h1><p>Возможно, ссылка устарела или в адресе есть опечатка.</p><a class="cta" href="index.html#catalog">Вернуться в каталог ↗</a></section>';
    rewriteHomeLinks();
    return;
  }
  document.title = item.name + ' — Сквозь иголки';
  $('#breadcrumbName').textContent = item.name;
  const images = item.images.filter(Boolean);
  const characteristics = {...item.characteristics, lighting:item.characteristics.lighting || item.characteristics.light};
  const labels = {species:'Вид растения', variety:'Сорт', height:'Высота', crownDiameter:'Диаметр кроны', growthRate:'Скорость роста', frostResistance:'Морозостойкость', lighting:'Освещение', soil:'Почва', care:'Особенности ухода'};
  const rows = Object.entries(labels).filter(([key]) => characteristics[key]).map(([key, label]) => `<div><dt>${label}</dt><dd>${esc(characteristics[key])}</dd></div>`).join('');
  $('#productDetail').innerHTML = `<section class="product-layout"><div class="gallery"><button class="gallery-main" id="expandPhoto" aria-label="Открыть фото: ${esc(item.name)}" ${images.length ? '' : 'disabled'}>${images.length ? `<img class="gallery-image" id="mainPhoto" src="${esc(images[0])}" alt="${esc(item.name)}"><span class="expand-hint">⤢ Смотреть крупнее</span>` : '<span>Фото пока не добавлено</span>'}</button><div class="thumbnails" aria-label="Выбрать фото" ${images.length > 1 ? '' : 'hidden'}>${images.map((src, n) => `<button data-photo="${n}" class="thumbnail ${n === 0 ? 'selected' : ''}" aria-label="Фото ${n + 1}" aria-pressed="${n === 0}"><img src="${esc(src)}" alt="" loading="lazy"></button>`).join('')}</div></div><div class="product-summary"><a class="kicker" href="${categoryUrl(item.category)}">${esc(item.category)}</a><h1>${esc(item.name)}</h1>${item.tag ? `<span class="product-badge">${esc(item.tag)}</span>` : ''}${item.size ? `<p class="product-size">${esc(item.size)}</p>` : ''}${availabilityMarkup(item)}<div class="purchase-box"><span class="price-caption">Цена от</span><div class="product-price">${fmt(item.price)}</div>${cartButtonMarkup(item, true)}<p class="hint">Наличие и условия приобретения уточняются у продавца. Соберите растения в корзине и скопируйте список для запроса.</p></div></div></section>${item.description ? `<section class="plant-description" aria-labelledby="plantDescriptionTitle"><div><div class="kicker">ПОДРОБНЕЕ О РАСТЕНИИ</div><h2 id="plantDescriptionTitle">Описание растения</h2></div><p class="product-description">${esc(item.description)}</p></section>` : ''}${rows ? `<section class="plant-characteristics"><div><div class="kicker">О РАСТЕНИИ</div><h2>Характеристики</h2><p class="hint">Сведения из каталога</p></div><dl>${rows}</dl></section>` : ''}`;

  const related = items.filter(p => p.slug !== item.slug).sort((a, b) => Number(b.category === item.category) - Number(a.category === item.category)).slice(0, 4);
  $('#relatedProducts').innerHTML = related.map(cardMarkup).join('');
  $('#relatedSection').hidden = !related.length;

  rewriteHomeLinks();
  if (!images.length) return;
  let current = 0;
  const dialog = $('#lightbox');
  function selectPhoto(n) {
    current = (n + images.length) % images.length;
    const main = $('#mainPhoto');
    main.classList.remove('image-unavailable');
    main.src = images[current];
    main.alt = item.name + ' — фото ' + (current + 1);
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) main.animate([{opacity:.35}, {opacity:1}], {duration:240});
    document.querySelectorAll('[data-photo]').forEach(button => {
      const selected = Number(button.dataset.photo) === current;
      button.classList.toggle('selected', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    $('#lightboxImage').classList.remove('image-unavailable');
    $('#lightboxImage').src = images[current];
    if (dialog.open && !matchMedia('(prefers-reduced-motion: reduce)').matches) $('#lightboxImage').animate([{opacity:.35}, {opacity:1}], {duration:240});
    $('#lightboxImage').alt = main.alt;
    $('#photoCounter').textContent = `${current + 1} / ${images.length} · ${item.name}`;
  }
  $('.thumbnails').onclick = event => {
    const button = event.target.closest('[data-photo]');
    if (button) selectPhoto(Number(button.dataset.photo));
  };
  $('#expandPhoto').onclick = () => { selectPhoto(current); dialog.showModal(); document.body.style.overflow = 'hidden'; };
  $('#closeLightbox').onclick = () => dialog.close();
  dialog.addEventListener('close', () => { document.body.style.overflow = ''; $('#expandPhoto').focus(); });
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  $('#prevPhoto').hidden = $('#nextPhoto').hidden = images.length < 2;
  $('#prevPhoto').onclick = () => selectPhoto(current - 1);
  $('#nextPhoto').onclick = () => selectPhoto(current + 1);
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); dialog.close(); return; }
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault(); selectPhoto(current + (event.key === 'ArrowLeft' ? -1 : 1));
    }
  });
  let touchStart;
  $('#lightboxImage').addEventListener('touchstart', event => { touchStart = event.changedTouches[0].clientX; }, {passive:true});
  $('#lightboxImage').addEventListener('touchend', event => {
    const delta = event.changedTouches[0].clientX - touchStart;
    if (Math.abs(delta) > 45) selectPhoto(current + (delta < 0 ? 1 : -1));
  }, {passive:true});
})();
