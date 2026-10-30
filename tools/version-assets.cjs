'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
function versionAssets(root = path.resolve(__dirname, '..')) {
  const read = name => fs.readFileSync(path.join(root, name), 'utf8').replace(/\r\n/g, '\n');
  const write = (name, content) => fs.writeFileSync(path.join(root, name), content);
  const hash = content => crypto.createHash('sha256').update(content).digest('hex').slice(0, 20);
  fs.mkdirSync(path.join(root, 'assets'), {recursive:true});
  const manifest = {};
  function asset(name, content = read(name)) {
    const ext = path.extname(name);
    const filename = 'assets/' + name.slice(0,-ext.length) + '.' + hash(content) + ext;
    write(filename,content);
    manifest[name] = filename;
    return filename;
  }
  for (const name of ['site-config.js','catalog.generated.js','catalog.js','cart-storage.js','order.js','app.js','product.js','styles.css','enhancements.css']) asset(name);
  let frame = read('cart-storage.html').replace(/<script\b[^>]*src="[^"]+"[^>]*><\/script>\s*/g, '');
  frame = frame.replace('</body>', ['catalog.generated.js','catalog.js','cart-storage.js'].map(name => `<script src="${manifest[name]}"></script>`).join('\n')+'\n</body>');
  write('cart-storage.html',frame);
  const frameName = 'cart-storage.'+hash(frame)+'.html';
  write(frameName,frame);
  manifest['cart-storage.html'] = frameName;
  asset('cart.js',read('cart.js').replace("cartFrame.src = 'cart-storage.html';", `cartFrame.src = location.protocol === 'file:' ? 'cart-storage.html' : '${frameName}';`));
  for (const page of ['index.html','product.html']) {
    let html = read(page).replace(/<script\b[^>]*src="[^"]+"[^>]*><\/script>\s*/g, '');
    html = html.replace(/href="(?:assets\/)?(?:styles|enhancements)(?:\.[a-f0-9]{20})?\.css(?:\?[^"]*)?"/g, reference => {
      const name = reference.includes('enhancements') ? 'enhancements.css' : 'styles.css';
      return `href="${manifest[name]}"`;
    });
    const scripts = ['site-config.js','catalog.generated.js','catalog.js','cart.js','order.js','app.js'];
    if (page==='product.html') scripts.push('product.js');
    html = html.replace('</body>',scripts.map(name=>`<script src="${manifest[name]}" defer></script>`).join('\n')+'\n</body>');
    write(page,html);
  }
  write('assets/manifest.json',JSON.stringify(manifest,null,2)+'\n');
  return manifest;
}
if (require.main === module) versionAssets(process.argv[2]);
module.exports = {versionAssets};
