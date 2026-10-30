'use strict';
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const {versionAssets}=require('../tools/version-assets.cjs');
const root=path.resolve(__dirname,'..'),temp=fs.mkdtempSync(path.join(os.tmpdir(),'skvoz-hashes-'));
try {
  const sources=['site-config.js','catalog.generated.js','catalog.js','cart.js','cart-storage.js','order.js','app.js','product.js','styles.css','enhancements.css'];
  for(const name of [...sources,'index.html','product.html','cart-storage.html']) fs.copyFileSync(path.join(root,name),path.join(temp,name));
  let previous=versionAssets(temp);
  assert.deepEqual(versionAssets(temp),previous,'Build must be reproducible');
  for(const name of sources){
    const old=previous[name],bytes=fs.readFileSync(path.join(temp,old));
    fs.appendFileSync(path.join(temp,name),'\n/* cache update check */\n');
    const next=versionAssets(temp);
    assert.notEqual(next[name],old,name);
    assert.deepEqual(fs.readFileSync(path.join(temp,old)),bytes,'Old immutable assets must remain intact');
    previous=next;
  }
  for(const page of ['index.html','product.html']){
    const html=fs.readFileSync(path.join(temp,page),'utf8');
    const scripts=[...html.matchAll(/<script src="([^"]+)" defer>/g)].map(m=>m[1]);
    const expected=['site-config.js','catalog.generated.js','catalog.js','cart.js','order.js','app.js',...(page==='product.html'?['product.js']:[])].map(n=>previous[n]);
    assert.deepEqual(scripts,expected);
  }
  console.log('PASS: all ten JS/CSS URLs change with content; deterministic build, dependency ordering and retained immutable assets.');
} finally { assert.equal(path.dirname(path.resolve(temp)),path.resolve(os.tmpdir())); fs.rmSync(temp,{recursive:true,force:true}); }
