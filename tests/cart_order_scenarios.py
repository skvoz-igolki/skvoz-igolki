"""Dedicated cart/Telegram checks. Telegram navigation is stubbed: no real chat requests."""
import os
from urllib.parse import urlparse, parse_qs

def wait_for(expression, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression, js('location.href'), errors))

def loaded():
    wait_for("document.readyState==='complete' && typeof cartReady!=='undefined' && cartReady")

def add(slug, count=1):
    for _ in range(count):
        js(f"window.changed=false;requestCartChange({json.dumps(slug)},1).then(()=>window.changed=true)")
        wait_for('window.changed')

mode = os.environ.get('SKVOZ_ORDER_MODE', 'restore')
navigate('index.html')
loaded()
if mode == 'seed':
    assert js('Object.keys(cart).length') == 0
    add('tuya-smaragd',3)
    add('el-golubaya',2)
    assert js("document.querySelector('#basketCount').textContent") == '5'
    print('PASS: seeded 2 cart positions/5 plants for browser-restart check: ' + TEST_BASE)
else:
    assert js("document.querySelector('#basketCount').textContent") == '5', 'Cart lost after browser restart'
    for ignore_cache in [False, True]:
        call('Page.reload', {'ignoreCache':ignore_cache})
        time.sleep(.3)
        loaded()
        assert js("document.querySelector('#basketCount').textContent") == '5', 'Cart lost on F5/Ctrl+F5'
    navigate('product.html?product=tuya-smaragd')
    loaded()
    assert js("document.querySelector('#basketCount').textContent") == '5'
    main_ws = ws
    target = call('Target.createTarget', {'url':TEST_BASE + '/index.html'})['targetId']
    def connect_target(target_id):
        tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
        return websocket.create_connection(next(t for t in tabs if t['id']==target_id)['webSocketDebuggerUrl'],timeout=15)
    ws = connect_target(target)
    call('Runtime.enable')
    call('Page.enable')
    loaded()
    assert js("document.querySelector('#basketCount').textContent") == '5'
    add('tuya-smaragd')
    wait_for("document.querySelector('#basketCount').textContent==='6'")
    ws.close()
    ws = main_ws
    wait_for("document.querySelector('#basketCount').textContent==='6'")
    call('Target.closeTarget', {'targetId':target})
    target = call('Target.createTarget', {'url':TEST_BASE + '/index.html'})['targetId']
    ws = connect_target(target)
    call('Runtime.enable')
    call('Page.enable')
    loaded()
    assert js("document.querySelector('#basketCount').textContent") == '6', 'Cart lost after tab reopened'
    ws.close()
    ws = main_ws
    call('Target.closeTarget', {'targetId':target})
    click('#openCart')
    assert js("document.querySelectorAll('.cart-item').length") == 2
    assert js("[...document.querySelectorAll('.cart-item a')].every(a=>a.target==='_blank'&&a.rel==='noopener noreferrer'&&a.href.includes('?product='))")
    expected_total = js("4*items.find(p=>p.slug==='tuya-smaragd').price+2*items.find(p=>p.slug==='el-golubaya').price")
    assert js('buildOrder().total') == expected_total

    js("window.SHOP_CONFIG.SITE_URL='';renderCart()")
    # Prevent all real navigation to Telegram, while testing the actual click handler.
    js("""window.nativeTelegramOpen=window.open.bind(window);window.telegramNavigations=[];window.telegramOpens=0;
    window.testTelegramOpen=(url,target)=>{window.telegramOpens++;window.mockTelegramTab={closed:false,opener:'initial',document:{title:'',body:{textContent:''}},location:{replace:url=>window.telegramNavigations.push(url)},close(){this.closed=true}};return window.mockTelegramTab};window.open=window.testTelegramOpen;
    window.copied='';Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copied=text}}});""")
    assert js("document.querySelector('#openTelegramChat').href") == 'https://t.me/Uliamel'
    assert js("typeof document.querySelector('#sendTelegram').onclick==='function'")
    assert not js("document.querySelector('#sendTelegram').disabled")
    assert not errors, errors
    # Hold async preparation: the popup must already open before this promise resolves.
    js("window.originalCurrentOrder=currentOrder;currentOrder=()=>new Promise(resolve=>{window.releaseOrderRead=()=>resolve(buildOrder())})")
    click('#sendTelegram')
    assert js('window.telegramOpens') == 1, 'Empty SITE_URL blocked the user-gesture popup'
    assert js('window.telegramNavigations.length') == 0
    assert js("typeof window.releaseOrderRead==='function'")
    js('window.releaseOrderRead();currentOrder=window.originalCurrentOrder')
    wait_for('window.telegramNavigations.length===1')
    local_draft = parse_qs(urlparse(js('window.telegramNavigations[0]')).query)['text'][0]
    assert local_draft == js('buildOrder().message')
    assert 'file://' not in local_draft
    assert js("document.querySelector('#basketCount').textContent") == '6'
    click('#copyOrder')
    wait_for('window.copied.length>0')
    assert ('Ссылка:' in js('window.copied')) == TEST_BASE.startswith('https:')
    assert 'file://' not in js('window.copied')

    js("window.SHOP_CONFIG.SITE_URL='https://skvoz-igolki-miv3dgeniy-7rsq.onreza.app/garden';renderCart()")
    message = js('buildOrder().message')
    assert message.count('Количество:') == 2
    assert message.count('Цена:') == 2
    assert message.count('Сумма:') == 2
    assert 'Количество: 4 шт.' in message and 'Количество: 2 шт.' in message
    assert '\n\n' in message
    assert 'https://skvoz-igolki-miv3dgeniy-7rsq.onreza.app/garden/product.html?product=tuya-smaragd' in message
    assert 'https://skvoz-igolki-miv3dgeniy-7rsq.onreza.app/garden/product.html?product=el-golubaya' in message
    assert js('fmt(buildOrder().total)') in message
    click('#sendTelegram')
    wait_for('window.telegramNavigations.length===2')
    assert js('window.mockTelegramTab.opener===null')
    telegram_url = js('window.telegramNavigations[1]')
    parsed = urlparse(telegram_url)
    assert parsed.scheme == 'https' and parsed.netloc == 't.me' and parsed.path == '/Uliamel'
    assert parse_qs(parsed.query)['text'][0] == message
    assert '%0A' in telegram_url and '%D0' in telegram_url
    assert js("document.querySelector('#basketCount').textContent") == '6', 'Telegram must not clear the cart'
    click('#copyOrder')
    wait_for(f'window.copied==={json.dumps(message)}')
    # A direct-chat link is checked and activated with navigation prevented.
    js("document.querySelector('#openTelegramChat').addEventListener('click',e=>{e.preventDefault();window.openedChat=e.currentTarget.href})")
    click('#openTelegramChat')
    assert js('window.openedChat') == 'https://t.me/Uliamel'
    js('window.open=()=>null')
    click('#sendTelegram')
    wait_for("!document.querySelector('#telegramFallback').hidden")
    assert js("document.querySelector('#telegramFallback').href") == telegram_url
    assert 'заблокировал' in js("document.querySelector('#orderNotice').textContent")

    # Denied clipboard keeps a complete selectable fallback, without extra storage.
    js("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied')}}});document.execCommand=()=>false")
    click('#copyOrder')
    wait_for("!!document.querySelector('#manualOrder')")
    assert js("document.querySelector('#manualOrder').value") == message
    assert js("document.querySelector('#manualOrder').readOnly")
    for width in [320,375,768,1024,1440]:
        call('Emulation.setDeviceMetricsOverride', {'width':width,'height':800,'deviceScaleFactor':1,'mobile':width<760})
        assert js('document.documentElement.scrollWidth<=innerWidth'), width
        assert js("document.querySelector('.drawer').scrollWidth<=document.querySelector('.drawer').clientWidth"), width
    artifacts = ROOT / 'tests' / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    # Show normal cart actions, rather than the test fallback textarea.
    js("document.querySelector('#manualOrder').remove();renderCart();document.querySelector('.drawer').scrollTop=99999")
    call('Emulation.setDeviceMetricsOverride', {'width':375,'height':900,'deviceScaleFactor':1,'mobile':True})
    result = call('Page.captureScreenshot', {'format':'png'})
    (artifacts / ('cart-' + ('file' if TEST_BASE.startswith('file:') else 'https') + '-mobile.png')).write_bytes(base64.b64decode(result['data']))

    exec(compile((ROOT / 'tests/telegram_popup_gesture.py').read_text(encoding='utf-8'), 'telegram_popup_gesture.py', 'exec'))

    # Invalid public addresses never leak local file paths into copied orders.
    for invalid in ['file:///D:/private/', 'http://skvoz-igolki-miv3dgeniy-7rsq.onreza.app/', 'not a URL', 'https://skvoz-igolki-miv3dgeniy-7rsq.onreza.app/?token=secret']:
        js(f'window.SHOP_CONFIG.SITE_URL={json.dumps(invalid)}')
        assert js('publicSiteUrl()===null')
        assert 'Ссылка:' not in js('buildOrder().message')
    js("window.SHOP_CONFIG.SITE_URL='https://skvoz-igolki-miv3dgeniy-7rsq.onreza.app/';window.longOrderPlant=items.find(p=>p.slug===Object.keys(cart)[0]);window.savedPlantName=window.longOrderPlant.name;window.longOrderPlant.name='x'.repeat(4500);window.open=(url,target)=>{window.mockTelegramTab={closed:false,opener:null,document:{title:'',body:{textContent:''}},location:{replace:u=>window.telegramNavigations.push(u)},close(){this.closed=true}};return window.mockTelegramTab}")
    count = js('window.telegramNavigations.length')
    click('#sendTelegram')
    wait_for('window.mockTelegramTab.closed')
    assert js('window.telegramNavigations.length') == count
    assert 'длинный' in js("document.querySelector('#orderNotice').textContent")
    js('window.longOrderPlant.name=window.savedPlantName;renderCart()')
    click('#closeCart')

    # Verify the canonical storage content and corrupted/obsolete data handling.
    call('Page.navigate', {'url':TEST_BASE + '/cart-storage.html'})
    wait_for("location.pathname.endsWith('/cart-storage.html')&&document.readyState==='complete'")
    stored = json.loads(js("localStorage.getItem('skvoz-igolki.cart.v2')"))
    assert stored == {'tuya-smaragd':4,'el-golubaya':2}
    assert all(isinstance(n,int) for n in stored.values())
    js("localStorage.setItem('skvoz-igolki.cart.v2','{broken')")
    navigate('index.html')
    loaded()
    assert js('Object.keys(cart).length') == 0
    click('#openCart')
    assert js("document.querySelector('#sendTelegram').disabled && document.querySelector('#copyOrder').disabled")
    js('window.telegramOpens=0;window.open=()=>{window.telegramOpens++;return null};document.querySelector("#sendTelegram").onclick()')
    assert js('window.telegramOpens') == 0
    click('#closeCart')
    call('Page.navigate', {'url':TEST_BASE + '/cart-storage.html'})
    wait_for("location.pathname.endsWith('/cart-storage.html')&&document.readyState==='complete'")
    invalid_state = {'tuya-smaragd':2,'el-golubaya':'bad','deleted-slug':2}
    denied_slug = next((p['slug'] for p in js('window.CATALOG') if p.get('availability') is False), None)
    if denied_slug: invalid_state[denied_slug] = 9
    js(f"localStorage.setItem('skvoz-igolki.cart.v2',{json.dumps(json.dumps(invalid_state))})")
    navigate('index.html')
    loaded()
    assert js("JSON.stringify(cart)") == '{"tuya-smaragd":2}', (js('JSON.stringify(cart)'),js("items.find(p=>p.slug==='elka').availability"))
    click('#openCart')
    click('[data-delta="-1"]')
    wait_for("document.querySelector('#basketCount').textContent==='1'")
    click('[data-delta="-1"]')
    wait_for("document.querySelector('#basketCount').textContent==='0'")
    assert js("document.querySelector('#sendTelegram').disabled && document.querySelector('#copyOrder').disabled")
    print('PASS: browser restart, F5/Ctrl+F5, tab close/reopen, sync, real cart totals, draft formatting/encoding/recipient, copy/manual/popup/long-order fallbacks, empty/corrupt/unavailable cart, mobile: ' + TEST_BASE)
assert not errors, errors
ws.close()
