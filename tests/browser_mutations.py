"""Exercise actual JSON edits and rebuilds, not just in-memory UI fixtures."""
fixture_json = ROOT / 'products' / 'zz-test-product' / 'product.json'
original_json = fixture_json.read_text(encoding='utf-8')
def rebuild():
    subprocess.run(['node', str(ROOT / 'tools' / 'update-catalog.cjs')], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
exec(compile((ROOT / 'tests/product_description.py').read_text(encoding='utf-8'), 'product_description.py', 'exec'))
try:
    data = json.loads(original_json)
    data['availability'] = True
    fixture_json.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    rebuild()
    navigate('product.html?product=zz-test-product')
    loaded()
    assert not js("document.querySelector('.product-add').disabled")
    click('.product-add')
    wait_for("document.querySelector('#basketCount').textContent==='1'")
    click('#openCart')
    click('[data-delta="1"]')
    wait_for("document.querySelector('#basketCount').textContent==='2'")
    assert js("document.querySelectorAll('.cart-item').length") == 1
    assert js(r"document.querySelector('#total').textContent.replace(/\D/g,'')") == '84'
    click('#closeCart')
    data['price'] = 77
    fixture_json.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    rebuild()
    navigate('product.html?product=zz-test-product')
    loaded()
    click('#openCart')
    assert js("document.querySelector('#basketCount').textContent") == '2'
    assert js(r"document.querySelector('#total').textContent.replace(/\D/g,'')") == '154'
    click('#closeCart')
    data['availability'] = False
    fixture_json.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    rebuild()
    navigate('product.html?product=zz-test-product')
    loaded()
    assert js("document.querySelector('.product-add').disabled")
    assert js("document.querySelector('#basketCount').textContent") == '0'
    click('#openCart')
    assert js("document.querySelector('#copyOrder').disabled")
    click('#closeCart')
    data['availability'] = True
    fixture_json.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    rebuild()
    navigate('product.html?product=zz-test-product')
    loaded()
    click('.product-add')
    wait_for("document.querySelector('#basketCount').textContent==='1'")
    fixture_json.unlink()
    rebuild()
    navigate('product.html?product=zz-test-product')
    loaded()
    assert js("!!document.querySelector('.product-error')")
    assert js("document.querySelector('#basketCount').textContent") == '0'
    click('#openCart')
    assert js("document.querySelector('#copyOrder').disabled")
    click('#closeCart')
finally:
    fixture_json.write_text(original_json,encoding='utf-8')
    rebuild()
print('PASS: JSON availability change, persisted cart uses rebuilt price, deleted JSON product is safely removed from cart; fixture restored.')

# Migrate the previous numeric cart to slug keys through the canonical storage file.
call('Page.navigate', {'url': ROOT.as_uri() + '/cart-storage.html'})
wait_for("location.pathname.endsWith('/cart-storage.html') && document.readyState==='complete'")
js("localStorage.setItem('skvoz-igolki.cart.v2','broken JSON')")
navigate('product.html?product=tuya-smaragd')
loaded()
assert js("document.querySelector('#basketCount').textContent") == '0'
assert not js('!!window.cartStorageWarned')
click('.product-add')
wait_for("document.querySelector('#basketCount').textContent==='1'")
navigate('product.html?product=tuya-smaragd')
loaded()
assert js("document.querySelector('#basketCount').textContent") == '1'
call('Page.navigate', {'url': ROOT.as_uri() + '/cart-storage.html'})
wait_for("location.pathname.endsWith('/cart-storage.html') && document.readyState==='complete'")
legacy_product=js("items.find(p=>p.legacyId&&p.availability!==false)")
legacy_value=json.dumps({str(legacy_product['legacyId']):2,'unknown':100})
js(f"localStorage.removeItem('skvoz-igolki.cart.v2');localStorage.setItem('skvoz-igolki.cart.v1',{json.dumps(legacy_value)})")
navigate('product.html?product='+legacy_product['slug'])
loaded()
assert js("document.querySelector('#basketCount').textContent") == '2'
assert js("Object.keys(cart).join(',')") == legacy_product['slug']
click('#openCart')
click('[data-delta="-1"]')
click('[data-delta="-1"]')
wait_for("document.querySelector('#basketCount').textContent==='0'")
click('#closeCart')
print('PASS: legacy numeric cart migration to stable slugs; unknown positions ignored.')
