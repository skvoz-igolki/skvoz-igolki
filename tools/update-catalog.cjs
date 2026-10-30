#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..');
const PRODUCTS = path.join(ROOT, 'products');
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const imagePattern = /\.(?:jpe?g|png|webp)$/i;
const textFields = ['name','category','description','height','size','tag'];
const characteristicFields = ['species','variety','height','crownDiameter','growthRate','frostResistance','lighting','light','soil','care'];

function buildCatalog(root = PRODUCTS) {
  const errors = [], products = [], legacyIds = new Set();
  const fail = (slug, message) => errors.push(`${slug}/product.json: ${message}`);
  for (const entry of fs.readdirSync(root, {withFileTypes:true})) {
    if (!entry.isDirectory()) continue;
    const slug = entry.name;
    const file = path.join(root, slug, 'product.json');
    if (!fs.existsSync(file)) continue;
    if (!slugPattern.test(slug)) { fail(slug, 'имя папки: только латиница в нижнем регистре, цифры и одиночные дефисы'); continue; }
    let data;
    try { data = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '')); }
    catch (error) { fail(slug, `некорректный JSON (${error.message})`); continue; }
    if (!data || typeof data !== 'object' || Array.isArray(data)) { fail(slug, 'ожидается объект JSON'); continue; }
    for (const key of textFields) {
      if (data[key] !== undefined && typeof data[key] !== 'string') fail(slug, `${key} должен быть строкой`);
    }
    for (const key of ['name','category']) {
      if (typeof data[key] !== 'string' || !data[key].trim()) fail(slug, `заполните ${key}`);
    }
    if (typeof data.price !== 'number' || !Number.isFinite(data.price) || data.price < 0) fail(slug, 'price должен быть неотрицательным числом');
    if (data.currency !== undefined && data.currency !== 'RUB') fail(slug, 'поддерживается только currency: "RUB"');
    if (data.availability !== undefined && data.availability !== null && typeof data.availability !== 'boolean') fail(slug, 'availability: true, false или null (неизвестно)');
    if (data.order !== undefined && (typeof data.order !== 'number' || !Number.isFinite(data.order))) fail(slug, 'order должен быть числом');
    if (data.tags !== undefined && (!Array.isArray(data.tags) || data.tags.some(tag => typeof tag !== 'string' || !tag.trim()))) fail(slug, 'tags должен быть массивом непустых строк');
    if (data.characteristics !== undefined) {
      if (!data.characteristics || typeof data.characteristics !== 'object' || Array.isArray(data.characteristics)) fail(slug, 'characteristics должен быть объектом');
      else for (const [key, value] of Object.entries(data.characteristics)) {
        if (!characteristicFields.includes(key)) fail(slug, `неизвестная характеристика ${key}`);
        if (typeof value !== 'string') fail(slug, `characteristics.${key} должен быть строкой`);
      }
    }
    if (data.legacyId !== undefined) {
      if (!Number.isSafeInteger(data.legacyId) || data.legacyId < 1 || legacyIds.has(data.legacyId)) fail(slug, 'legacyId должен быть уникальным положительным целым числом');
      legacyIds.add(data.legacyId);
    }
    if ('slug' in data || 'id' in data) fail(slug, 'идентификатор берётся из имени папки; удалите поля slug и id');
    const images = [];
    if (!Array.isArray(data.images)) fail(slug, 'images должен быть массивом (можно пустым)');
    else for (const image of data.images) {
      if (typeof image !== 'string' || !image.trim()) { fail(slug, 'каждое изображение должно быть непустой строкой'); continue; }
      if (/^https?:\/\//i.test(image)) {
        try { new URL(image); images.push(image); } catch { fail(slug, `некорректный URL изображения: ${image}`); }
        continue;
      }
      // Local paths stay inside the product folder; no query strings or traversal.
      const segments = image.split('/');
      if (!imagePattern.test(image) || segments.some(s => !s || s === '.' || s === '..') || /[\\:#?\x00-\x1f]/.test(image)) {
        fail(slug, `недопустимый путь фото: ${image}. Используйте 1.jpg, 2.png, 3.webp или вложенную папку`); continue;
      }
      const productDir = fs.realpathSync(path.join(root, slug));
      const photo = path.join(productDir, ...segments);
      try {
        const realPhoto = fs.realpathSync(photo);
        const relative = path.relative(productDir, realPhoto);
        if (relative.startsWith('..') || path.isAbsolute(relative) || !fs.statSync(photo).isFile()) throw new Error('путь вне папки товара или не файл');
        images.push(['products', slug, ...segments].map(encodeURIComponent).join('/'));
      } catch (error) { fail(slug, `фото ${image} не найдено или недоступно (${error.message})`); }
    }
    products.push({...data, slug, images});
  }
  if (errors.length) throw new Error('Каталог не обновлён:\n- ' + errors.join('\n- '));
  return products.sort((a,b) => (a.order ?? Infinity) - (b.order ?? Infinity) || a.name.localeCompare(b.name, 'ru') || a.slug.localeCompare(b.slug));
}

function updateCatalog() {
  // Validate everything before replacing either generated file.
  const products = buildCatalog();
  const index = JSON.stringify({products:products.map(p => p.slug)}, null, 2) + '\n';
  const generated = '// АВТОМАТИЧЕСКИ СОЗДАНО. Редактируйте products/*/product.json и запускайте node tools/update-catalog.cjs\n' +
    'window.CATALOG = ' + JSON.stringify(products, null, 2).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029') + ';\n';
  fs.writeFileSync(path.join(PRODUCTS, 'index.json'), index);
  fs.writeFileSync(path.join(ROOT, 'catalog.generated.js'), generated);
  require('./version-assets.cjs').versionAssets(ROOT);
  console.log(`Каталог обновлён: ${products.length} товаров. products/index.json и catalog.generated.js готовы.`);
  const external = products.reduce((n,p) => n + p.images.filter(image => /^https?:/.test(image)).length, 0);
  if (external) console.log(`Внешние фотографии: ${external}. Ссылки сохранены, загрузка из интернета не выполнялась.`);
}

if (require.main === module) {
  try { updateCatalog(); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
module.exports = {buildCatalog, updateCatalog};
