"""Executed by browser_check.py in its isolated browser session."""
def wait_for(expression, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression, js('location.href'), js('({scrollY,top:document.querySelector("#catalog")?.getBoundingClientRect().top,height:document.documentElement.scrollHeight})'), errors))

def loaded():
    wait_for("document.readyState==='complete' && typeof cartReady!=='undefined' && cartReady")

def targets():
    return [t for t in call('Target.getTargets')['targetInfos'] if t['type']=='page']

def connect_tab(target_id):
    tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
    connection = websocket.create_connection(next(t for t in tabs if t['id']==target_id)['webSocketDebuggerUrl'],timeout=15)
    return connection

call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
navigate('index.html')
loaded()
exec(compile((ROOT / 'tests/catalog_filters.py').read_text(encoding='utf-8'), 'catalog_filters.py', 'exec'))
assert js("document.querySelectorAll('.product').length") == js("items.filter(p=>p.availability===true||p.availability===undefined).length")
has_fixture = js("items.some(p=>p.slug==='zz-test-product')")
slugs = js("items.filter(p=>p.slug!=='zz-test-product').map(p=>p.slug)")
assert len(slugs) >= 8
assert js("document.querySelectorAll('.brand-logo').length") == 2
assert js("document.querySelector('.brand-logo').naturalWidth") == 192
assert js("[...document.querySelectorAll('.product-link')].every(a=>a.target==='_blank' && a.rel==='noopener noreferrer' && a.href.includes('?product=') && !a.href.includes('?id='))")
click('[data-filter="Туи"]')
assert js("document.querySelectorAll('.product').length") == 2
js("document.querySelector('#tagFilter').value='Популярное';document.querySelector('#tagFilter').dispatchEvent(new Event('change'))")
assert js("document.querySelectorAll('.product').length") == 1
js("document.querySelector('#search').value='Популярное';document.querySelector('#search').dispatchEvent(new Event('input'))")
assert js("document.querySelectorAll('.product').length") == 1
js("document.querySelector('#tagFilter').value='';document.querySelector('#tagFilter').dispatchEvent(new Event('change'));document.querySelector('#search').value='Брабант';document.querySelector('#search').dispatchEvent(new Event('input'))")
assert js("document.querySelectorAll('.product').length") == 1
before = len(targets())
click('.add')
wait_for("document.querySelector('#basketCount').textContent==='1'")
assert len(targets()) == before, 'Add button opened a tab'
click('.product-image')
deadline = time.monotonic() + 8
new_target = None
while time.monotonic() < deadline:
    new_target = next((t for t in targets() if 'product=tuya-brabant' in t['url']), None)
    if new_target: break
    time.sleep(.1)
assert new_target and len(targets()) == before + 1
assert js('location.pathname.endsWith("index.html")')
catalog_ws = ws
ws = connect_tab(new_target['targetId'])
call('Runtime.enable')
call('Page.enable')
loaded()
assert js('window.opener===null')
assert js("document.querySelector('h1').textContent.includes('Брабант')")
wait_for("document.querySelector('#basketCount').textContent==='1'")
click('.product-add')
wait_for("document.querySelector('#basketCount').textContent==='0'")
wait_for("!document.querySelector('.product-add').disabled")
click('.product-add')
wait_for("document.querySelector('#basketCount').textContent==='1'")
click('#openCart')
click('[data-delta="1"]')
wait_for("document.querySelector('#basketCount').textContent==='2'")
click('#closeCart')
product_ws = ws
ws = catalog_ws
# No navigation or focus refresh: verify storage-driven live synchronization.
wait_for("document.querySelector('#basketCount').textContent==='2'")
ws = product_ws
click('#openCart')
assert js("document.querySelectorAll('.cart-item').length") == 1
assert js(r"document.querySelector('#total').textContent.replace(/\D/g,'')") == '3580'
click('[data-delta="-1"]')
wait_for("document.querySelector('.qty span').textContent==='1'")
js("window.copied='';Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copied=text}}})")
click('#copyOrder')
wait_for("window.copied.length>0")
assert '\n\n' in js('window.copied') and 'Брабант' in js('window.copied')
click('#closeCart')
click('#expandPhoto')
assert js("document.querySelector('#lightbox').open")
assert js("document.querySelector('#nextPhoto').hidden")
call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Escape','code':'Escape'})
call('Input.dispatchKeyEvent', {'type':'keyUp','key':'Escape','code':'Escape'})
wait_for("!document.querySelector('#lightbox').open")
for slug in slugs:
    navigate('product.html?product=' + slug)
    loaded()
    assert js("document.querySelector('h1').textContent===items.find(i=>i.slug===new URLSearchParams(location.search).get('product')).name")
    assert js("document.querySelector('.thumbnails').hidden===(items.find(p=>p.slug===new URLSearchParams(location.search).get('product')).images.length<2)")
    assert js("document.querySelector('.product-price').textContent===fmt(items.find(i=>i.slug===new URLSearchParams(location.search).get('product')).price)")
if has_fixture:
    navigate('product.html?product=zz-test-product')
    loaded()
    assert js("document.querySelector('.product-add').disabled")
    assert 'Нет в наличии' in js("document.querySelector('.availability').textContent")
    assert js("document.querySelectorAll('.plant-characteristics dt').length") == 1
    assert js("document.querySelector('#mainPhoto').naturalWidth") == 1
    assert js("document.querySelectorAll('.thumbnail').length") == 2
    click('[data-photo="1"]')
    assert js("document.querySelector('#mainPhoto').src.endsWith('/2.png')")
    click('#expandPhoto')
    click('#nextPhoto')
    assert js("document.querySelector('#lightboxImage').src.endsWith('/1.png')")
    click('#closeLightbox')
    navigate('index.html')
    loaded()
    click('#inStockOnly')
    click('[data-filter="Тестовая категория"]')
    assert js("document.querySelector('.add').disabled")
    js("document.querySelector('#tagFilter').value='Тестовый тег';document.querySelector('#tagFilter').dispatchEvent(new Event('change'))")
    assert js("document.querySelectorAll('.product').length") == 1
for width in [320,375,768,1024,1440]:
    call('Emulation.setDeviceMetricsOverride', {'width':width,'height':900,'deviceScaleFactor':1,'mobile':width<760})
    for page in ['index.html','product.html?product=tuya-smaragd','product.html?product=missing']:
        navigate(page)
        loaded()
        assert js('document.documentElement.scrollWidth<=innerWidth'), (width,page,'overflow')
navigate('product.html?product=missing')
loaded()
assert js("!!document.querySelector('.product-error .cta')")
navigate('product.html?product=tuya-brabant')
loaded()
assert js("document.querySelector('#basketCount').textContent") == '1', 'Cart lost on reload/direct navigation'
click('#openCart')
click('[data-delta="-1"]')
wait_for("document.querySelector('#basketCount').textContent==='0'")
assert js("document.querySelector('#copyOrder').disabled")
click('#closeCart')
ws = catalog_ws
wait_for("document.querySelector('#basketCount').textContent==='0'")
ws = product_ws
navigate('product.html?product=tuya-smaragd')
loaded()
if has_fixture:
    exec(compile((ROOT / 'tests/browser_mutations.py').read_text(encoding='utf-8'), 'browser_mutations.py', 'exec'))
screenshots = ROOT / 'tests' / 'artifacts'
screenshots.mkdir(exist_ok=True)
for width,label in [(1440,'desktop'),(375,'mobile')]:
    call('Emulation.setDeviceMetricsOverride', {'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width<760})
    time.sleep(.3)
    result=call('Page.captureScreenshot', {'format':'png','captureBeyondViewport':True})
    (screenshots / f'product-{label}.png').write_bytes(base64.b64decode(result['data']))
assert not errors, errors
print(f'PASS: {len(slugs)} file:// slug URLs, real new-tab click + noopener, no popup on add, live cart sync between tabs, search/categories/tags, totals/order/quantities, gallery, 5 widths' + (', generated JSON fixture/local photos/out-of-stock' if has_fixture else '') + '; no JS exceptions.')
catalog_ws.close()
ws.close()
