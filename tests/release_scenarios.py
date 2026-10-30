from urllib.parse import parse_qs,urlparse
def wait_for(expression):
    for _ in range(200):
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression,errors))
home='index.html' if TEST_BASE.startswith('file:') else ''
navigate(home);wait_for('cartReady')
assert js('items.length===10&&window.CATALOG.length===10')
assert js("document.querySelectorAll('#products .product').length===items.filter(p=>p.availability===true||p.availability===undefined).length")
assert not errors,errors
# All filter combinations derive from the actual catalog.
for category in js('[...new Set(items.map(p=>p.category))]'):
    js(f"document.querySelector('[data-filter='+CSS.escape({json.dumps(category)})+']').click()")
    assert js(f"[...document.querySelectorAll('#products [data-add]')].every(e=>items.find(p=>p.slug===e.dataset.add).category==={json.dumps(category)})")
js("document.querySelector('[data-filter=all]').click();document.querySelector('#inStockOnly').click()")
assert js("document.querySelectorAll('#products .product').length===items.length")
js("document.querySelector('#inStockOnly').click();document.querySelector('#search').value=items.find(p=>p.availability).name;document.querySelector('#search').dispatchEvent(new Event('input'))")
assert js("document.querySelectorAll('#products .product').length>=1")
for width in [320,375,390,430,1440]:
    call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
    assert js('document.documentElement.scrollWidth<=innerWidth')
    if width<768: assert js("getComputedStyle(document.querySelector('#products')).gridTemplateColumns.split(' ').length===2")
slug=js('items.find(p=>p.availability).slug')
navigate(('product.html' if TEST_BASE.startswith('file:') else 'product')+'?product='+slug);wait_for('cartReady')
assert js('document.querySelector("h1").textContent===items.find(p=>p.slug==='+json.dumps(slug)+').name')
js("window.configuredBase=SHOP_CONFIG.SITE_URL;SHOP_CONFIG.SITE_URL=''")
assert js('publicSiteUrl()')==(TEST_BASE+'/' if TEST_BASE.startswith('https:') else None)
js('SHOP_CONFIG.SITE_URL=window.configuredBase')

js('window.done=false;requestCartChange('+json.dumps(slug)+',1).then(()=>window.done=true)');wait_for('window.done')
order=js('buildOrder()')
assert 'https://skvoz-igolki.ru/product?product='+slug in order['message']
assert '.html?' not in order['message'] and 'onreza.app' not in order['message']
assert parse_qs(urlparse(order['telegramUrl']).query)['text'][0]==order['message']
# Warm the actual asset URL, then change source and rebuild without clearing cache.
old=js("document.querySelector('script[src*=\"assets/app.\"]').src")
site=Path(os.environ['SKVOZ_SITE_ROOT'])
token=str(time.time_ns())
with (site/'app.js').open('a',encoding='utf-8') as file: file.write('\nwindow.releaseProbe='+json.dumps(token)+';\n')
subprocess.run(['node',str(ROOT/'tools/version-assets.cjs'),str(site)],check=True)
call('Page.reload',{'ignoreCache':False});time.sleep(.3);wait_for('typeof window.releaseProbe!=="undefined"&&window.releaseProbe==='+json.dumps(token))
assert js("document.querySelector('script[src*=\"assets/app.\"]').src")!=old
assert js('cart['+json.dumps(slug)+']>0')
assert not errors,errors
print('PASS: 10 products, stock/category/search filters, five widths, clean HTTPS product URL, file navigation, exact Telegram links, persistent cart and changed hashed JS loaded with warm immutable cache: '+TEST_BASE)
