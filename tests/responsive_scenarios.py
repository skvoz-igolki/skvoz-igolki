"""Compact layout and atomic clear checks using the existing CDP browser harness."""
from urllib.parse import parse_qs, urlparse

def wait_for(expression, timeout=10):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression,errors,js("JSON.stringify({row:document.querySelector('#filters')?.getBoundingClientRect().toJSON(),active:document.querySelector('#filters .active')?.getBoundingClientRect().toJSON(),scroll:document.querySelector('#filters')?.scrollLeft})")))

def settled(): wait_for("typeof cartReady!=='undefined'&&cartReady")
def mutate(expression):
    js('window.done=false;('+expression+').then(()=>window.done=true)');wait_for('window.done')

navigate('index.html');settled();assert js('!Object.keys(cart).length'), 'Empty cart lost across browser restart';mutate('requestCartClear()')
# Use a deterministic image because external Unsplash access may be blocked.
original_hero=js("document.querySelector('.hero-photo').src")
def hero_fixture(w,h):
    image='<svg xmlns="http://www.w3.org/2000/svg" width="'+str(w)+'" height="'+str(h)+'"><rect width="100%" height="100%" fill="#9bbd8b"/><rect x="4" y="4" width="'+str(w-8)+'" height="'+str(h-8)+'" fill="none" stroke="#254b38" stroke-width="8"/></svg>'
    source='data:image/svg+xml;base64,'+base64.b64encode(image.encode()).decode()
    js('document.querySelector(".hero-photo").src='+json.dumps(source))
    wait_for('document.querySelector(".hero-photo").complete&&document.querySelector(".hero-photo").naturalWidth>0')
hero_fixture(1600,900)
widths=[320,360,375,390,412,430,768,1024,1440]
js("document.querySelector('#products h3 a').textContent='Long plant name with several words '.repeat(5)")
for width in widths:
    call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
    time.sleep(.1)
    assert js('document.documentElement.scrollWidth<=innerWidth'),width
    assert js("getComputedStyle(document.querySelector('#filters')).flexWrap==='nowrap'"),width
    assert js("[...document.querySelectorAll('#filters button')].every(e=>e.offsetTop===document.querySelector('#filters button').offsetTop)"),width
    assert js("(()=>{const r=document.querySelector('.stock-switch').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})()"),width
    assert js("document.querySelectorAll('#inStockOnly').length===1&&document.querySelector('#inStockOnly').checked"),width
    if width<768:
        assert js("document.querySelector('.hero').getBoundingClientRect().height<760"),width
        assert js("getComputedStyle(document.querySelector('.hero-photo')).maxHeight==='none'"),width
        assert js("(()=>{const t=document.querySelector('.tag-buttons').getBoundingClientRect(),s=document.querySelector('.stock-switch').getBoundingClientRect();return s.top>=t.bottom+7&&Math.abs(s.left-t.left)<3})()"),width
        for selector in ['#filters','.tag-buttons']:
            assert js(f"getComputedStyle(document.querySelector({json.dumps(selector)})).scrollbarWidth==='none'"),width
            assert js(f"getComputedStyle(document.querySelector({json.dumps(selector)}),'::-webkit-scrollbar').display==='none'"),width
            js(f"document.querySelector({json.dumps(selector)}).scrollLeft=9999")
            assert js(f"(()=>{{const e=document.querySelector({json.dumps(selector)});return e.scrollWidth<=e.clientWidth||e.scrollLeft>0}})()"),width
            js(f"document.querySelector({json.dumps(selector)}).scrollLeft=0")
        assert js("getComputedStyle(document.querySelector('#products')).gridTemplateColumns.split(' ').length===2"),width
        assert js("[...document.querySelectorAll('.card-size')].every(e=>getComputedStyle(e).display==='none')"),width
        assert js("[...document.querySelectorAll('#products .product')].every(e=>e.scrollWidth<=e.clientWidth)"),width
        assert js("[...document.querySelectorAll('#products h3')].every(e=>e.clientHeight<=parseFloat(getComputedStyle(e).lineHeight)*2+1)"),width
    else:
        assert js("document.querySelector('.hero').getBoundingClientRect().height<760"),width
        assert js("(()=>{const t=document.querySelector('.tag-buttons').getBoundingClientRect(),s=document.querySelector('.stock-switch').getBoundingClientRect();return Math.abs((s.top+s.bottom-t.top-t.bottom)/2)<3})()"),width
        assert js("[...document.querySelectorAll('.card-size')].every(e=>getComputedStyle(e).display!=='none')"),width
    assert js("getComputedStyle(document.querySelector('.hero-photo')).objectFit==='contain'"),width
    js("toast('Добавлено в корзину',{cartAction:true})")
    assert js("document.querySelector('#toast').getBoundingClientRect().height<=64"),width
    assert js("document.querySelector('#toastCart').getBoundingClientRect().height>=44"),width
    if width==320:
        time.sleep(.2)
        (ROOT/'tests/artifacts/hero-toast-320.png').write_bytes(base64.b64decode(call('Page.captureScreenshot',{'format':'png'})['data']))
    assert js("getComputedStyle(document.querySelector('#toast')).backgroundColor==='rgb(244, 248, 239)'"),width
    js("toast('Удалено из корзины',{undoAction:true})")
    assert js("document.querySelector('#toast').getBoundingClientRect().height<=64"),width
    assert js("document.querySelector('#toast').scrollWidth<=document.querySelector('#toast').clientWidth"),width
    js('hideToast();openCart()')
    assert js("document.querySelector('.drawer').scrollWidth<=document.querySelector('.drawer').clientWidth"),width
    assert js("document.querySelector('#sendTelegram').disabled&&document.querySelector('#clearCart').disabled"),width
    js('closeCart()')
    if width in [320,1440]:
        js("document.querySelector('#catalog').scrollIntoView({behavior:'instant'})")
        time.sleep(.15)
        (ROOT/'tests'/'artifacts'/('catalog-responsive-'+str(width)+'.png')).write_bytes(base64.b64decode(call('Page.captureScreenshot',{'format':'png'})['data']))
print('PASS: nine widths 320–1440; exactly two columns up to 767; no page/card/cart overflow; compact toasts and stock toggle visible.')

# Landscape, portrait and square images all fit the bounded area without cover.
for width in [320,430,1440]:
    call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
    for w,h in [(1600,900),(900,1600),(1000,1000)]:
        hero_fixture(w,h)
        assert js("getComputedStyle(document.querySelector('.hero-photo')).objectFit==='contain'")
        if width<768:
            assert js("(()=>{const i=document.querySelector('.hero-photo'),r=i.getBoundingClientRect();return Math.abs(r.height-r.width*i.naturalHeight/i.naturalWidth)<1})()")
        else:
            assert js("document.querySelector('.hero').getBoundingClientRect().height<760")
js('document.querySelector(".hero-photo").src='+json.dumps(original_hero))
# Offscreen category is revealed without changing the independent controls.
call('Emulation.setDeviceMetricsOverride',{'width':320,'height':850,'deviceScaleFactor':1,'mobile':True})
js("document.querySelector('#inStockOnly').checked=false;document.querySelector('#filters button:last-child').click()")
wait_for("(()=>{const a=document.querySelector('#filters .active').getBoundingClientRect(),r=document.querySelector('#filters').getBoundingClientRect();return a.left>=r.left-1&&a.right<=r.right+1})()")
assert not js("document.querySelector('#inStockOnly').checked")
js("document.querySelector('#filters button').click();document.querySelector('#inStockOnly').checked=true;document.querySelector('#inStockOnly').dispatchEvent(new Event('change'))")
tag=js("items.find(p=>p.availability!==false&&p.tags.length)?.tags[0]||''")
if tag:
    js(f"document.querySelector('#tagButtons [data-tag='+CSS.escape({json.dumps(tag)})+']').click()")
    assert js(f"[...document.querySelectorAll('#products [data-add]')].every(e=>items.find(p=>p.slug===e.dataset.add).tags.includes({json.dumps(tag)}))")
    js("document.querySelector('#tagButtons button').click()")

slugs=js("items.filter(p=>p.availability!==false).slice(0,2).map(p=>p.slug)")
for slug in slugs:
    for _ in range(3): mutate(f'requestCartChange({json.dumps(slug)},1)')
js('openCart()');click('#clearCart')
assert js("!document.querySelector('#clearCartConfirm').hidden&&Object.keys(cart).length===2")
click('#cancelClearCart');assert js('Object.keys(cart).length===2')

# Another product tab receives the single clear mutation and membership changes.
main_ws=ws
target=call('Target.createTarget',{'url':TEST_BASE+'/product.html?product='+slugs[0]})['targetId']
tabs=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
ws=websocket.create_connection(next(t for t in tabs if t['id']==target)['webSocketDebuggerUrl'],timeout=15)
call('Runtime.enable');call('Page.enable');settled();assert js('Object.keys(cart).length===2')
product_ws=ws;ws=main_ws
js("window.mutations=[];window.originalCartRequest=cartRequest;cartRequest=(action,fields)=>{window.mutations.push(action);return window.originalCartRequest(action,fields)}")
click('#clearCart');js("document.querySelector('#confirmClearCart').click();document.querySelector('#confirmClearCart').click()")
wait_for('!Object.keys(cart).length&&!pendingCartClear')
assert js("window.mutations.filter(x=>x==='clear').length") == 1
assert js("lastCartRemoval===null&&document.querySelector('#toast').hidden&&document.querySelector('#sendTelegram').disabled")
ws=product_ws;wait_for('!Object.keys(cart).length')
assert js("!document.querySelector('.product-add').classList.contains('is-in-cart')")
call('Page.reload',{'ignoreCache':True});time.sleep(.4);settled();assert js('!Object.keys(cart).length')
ws.close();ws=main_ws;call('Target.closeTarget',{'targetId':target})
call('Page.reload',{'ignoreCache':True});time.sleep(.4);settled();assert js('!Object.keys(cart).length')
for slug in slugs: mutate(f'requestCartChange({json.dumps(slug)},1)')
draft=js('buildOrder()');decoded=parse_qs(urlparse(draft['telegramUrl']).query)['text'][0]
assert decoded==draft['message'] and decoded.count('Ссылка: https://')==2
navigate('product.html?product='+slugs[0]);settled();js('openCart()');click('#clearCart');click('#confirmClearCart');wait_for('!Object.keys(cart).length')
assert not errors,errors
print('PASS: category/tag/stock preservation; cancellation; one atomic clear despite double click; product and index controls; persisted empty cart; cross-tab buttons; encoded HTTPS Telegram links.')
