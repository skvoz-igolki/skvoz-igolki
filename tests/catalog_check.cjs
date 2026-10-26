'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {spawnSync} = require('node:child_process');
const ROOT = path.resolve(__dirname, '..');
const {buildCatalog, updateCatalog} = require('../tools/update-catalog.cjs');
const baseline = buildCatalog().length;
const fixture = path.join(ROOT,'products','zz-test-product');
assert(!fs.existsSync(fixture), 'Test folder already exists. Nothing was changed.');
const outputs = ['products/index.json','catalog.generated.js'];
const original = outputs.map(name => fs.readFileSync(path.join(ROOT,name),'utf8'));
const photo = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64');
const data = {name:'Тестовый товар', category:'Тестовая категория', price:42, currency:'RUB', availability:false,
  description:'Тестовое описание', tags:['Тестовый тег'], characteristics:{height:'',lighting:'Тестовый свет'}, images:['1.png','2.png'], order:99};
data.description = fs.readFileSync(path.join(ROOT,'tests/description_sample.txt'),'utf8').repeat(20) + 'x'.repeat(400);
const write = value => fs.writeFileSync(path.join(fixture,'product.json'),JSON.stringify(value,null,2));
try {
  fs.mkdirSync(fixture);
  fs.writeFileSync(path.join(fixture,'1.png'),photo);
  fs.writeFileSync(path.join(fixture,'2.png'),photo);
  write(data);
  let products = buildCatalog();
  assert.equal(products.length,baseline + 1);
  assert.equal(products.find(p=>p.slug==='zz-test-product').description,data.description);
  assert.equal(products.at(-1).slug,'zz-test-product');
  assert.equal(products.at(-1).images[0],'products/zz-test-product/1.png');
  const originalPhoto = fs.readFileSync(path.join(fixture,'1.png'));
  for (const invalid of [
    {...data,description:42}, {...data,description:null}, {...data,price:'42'}, {...data,images:['missing.webp']}, {...data,images:['../logo.webp']},
    {...data,tags:'bad'}, {...data,availability:'false'}, {...data,characteristics:{lighting:12}},
    {...data,images:['javascript:alert(1)']}, {...data,slug:'wrong'}
  ]) {
    write(invalid);
    assert.throws(() => buildCatalog(), /Каталог не обновлён/);
    const cli = spawnSync(process.execPath,[path.join(ROOT,'tools/update-catalog.cjs')],{encoding:'utf8'});
    assert.equal(cli.status,1);
    outputs.forEach((name,i) => assert.equal(fs.readFileSync(path.join(ROOT,name),'utf8'),original[i]));
  }
  fs.writeFileSync(path.join(fixture,'product.json'),'{ broken JSON');
  assert.throws(() => buildCatalog(), /некорректный JSON/);
  write(data);
  updateCatalog();
  assert.deepEqual(fs.readFileSync(path.join(fixture,'1.png')),originalPhoto);
  const context = {window:{}};
  vm.runInNewContext(fs.readFileSync(path.join(ROOT,'catalog.generated.js'),'utf8'),context);
  assert.equal(context.window.CATALOG.length,baseline + 1);
  assert.equal(context.window.CATALOG.find(p=>p.slug==='zz-test-product').description,data.description);
  assert.equal(context.window.CATALOG.at(-1).availability,false);
  console.log('PASS: added JSON-folder product, local photos, validation, failed-build output preservation, generated data, unchanged photos.');
  // Browser scenarios include the generated test product and remove no source data.
  const browser = spawnSync('python',[path.join(ROOT,'tests/browser_check.py')],{stdio:'inherit',cwd:ROOT});
  assert.equal(browser.status,0,'Browser checks failed');
} finally {
  // Only these exact, test-created files are removed. Never recursively delete products.
  for (const name of ['product.json','1.png','2.png']) {
    const file = path.join(fixture,name);
    if (fs.existsSync(file)) fs.unlinkSync(file);
  }
  fs.rmdirSync(fixture);
  updateCatalog();
  outputs.forEach((name,i) => assert.equal(fs.readFileSync(path.join(ROOT,name),'utf8'),original[i]));
}
