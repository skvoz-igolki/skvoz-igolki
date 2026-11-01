'use strict';
// Validate without repairing: catches a changed source plus stale HTML/manifest/assets.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {versionAssets}=require('./version-assets.cjs');
function checkBuild(root=path.resolve(__dirname,'..')) {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'skvoz-build-check-'));
  const read=(base,name)=>fs.readFileSync(path.join(base,name),'utf8').replace(/\r\n/g,'\n');
  try {
    const sources=['site-config.js','catalog.generated.js','catalog.js','cart.js','cart-storage.js','order.js','app.js','product.js','styles.css','enhancements.css'];
    for(const name of [...sources,'index.html','product.html','cart-storage.html']) fs.copyFileSync(path.join(root,name),path.join(temp,name));
    const expected=versionAssets(temp);
    for(const name of ['index.html','product.html','cart-storage.html','assets/manifest.json',...Object.values(expected)]) {
      if (!fs.existsSync(path.join(root,name)) || read(root,name)!==read(temp,name)) throw new Error(`Сборка не соответствует исходникам: ${name}. Выполните node tools/update-catalog.cjs и публикуйте HTML и assets вместе.`);
    }
    return expected;
  } finally {
    if(path.dirname(path.resolve(temp))!==path.resolve(os.tmpdir())) throw new Error('Unsafe temporary directory');
    fs.rmSync(temp,{recursive:true,force:true});
  }
}
if(require.main===module) {
  try { checkBuild();console.log('Сборка согласована: исходники, manifest, HTML и версионированные ресурсы.'); }
  catch(error) {console.error(error.message);process.exitCode=1;}
}
module.exports={checkBuild};
