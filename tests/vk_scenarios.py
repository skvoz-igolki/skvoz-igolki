"""VK checkout with fake seller and intercepted navigation/clipboard; no external sends."""
CONTACT='https://vk.me/test_seller'

def wait_for(expression):
    for _ in range(200):
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression,errors))

def mutate(expression):
    js('window.done=false;('+expression+').then(()=>window.done=true)');wait_for('window.done')

def stub():
    js("window.opens=0;window.dest='';window.copied='';window.open=()=>{window.opens++;return window.popup={closed:false,opener:'initial',close(){this.closed=true},location:{replace:u=>window.dest=u}}};Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>window.copied=t}})")

for page in ['index.html','product.html?product=tuya-smaragd']:
    navigate(page);wait_for('typeof cartReady!=="undefined"&&cartReady');mutate('requestCartClear()')
    js('window.nativeVkOpen=window.open.bind(window);window.originalCurrentOrder=currentOrder')
    stub();js('sendOrderToVk()');assert js('window.opens===0&&document.querySelector("#sendVk").disabled')
    assert js("!document.querySelector('[id*=Max],[id*=max]')&&!document.body.textContent.includes('MAX')")
    slugs=js('items.filter(p=>p.availability!==false).slice(0,2).map(p=>p.slug)')
    for slug in slugs:
        for _ in range(2):mutate('requestCartChange('+json.dumps(slug)+',1)')
    js('openCart()')
    # Empty, unsafe and unrelated URLs must never open a tab or copy an order.
    for contact in ['', 'javascript:alert(1)','https://vk.me.evil/person','http://vk.me/person','https://vk.com/share.php','https://vk.me/person?redirect=evil','https://user@vk.me/person','https://vk.me/person/other']:
        stub();js('SHOP_CONFIG.VK_CONTACT_URL='+json.dumps(contact)+';document.querySelector("#sendVk").click()')
        assert js('window.opens===0&&window.copied===""&&vkContactUrl()===null')
        assert 'VK_CONTACT_URL' not in js('document.querySelector("#orderNotice").textContent')
    js('SHOP_CONFIG.VK_CONTACT_URL='+json.dumps(CONTACT))
    # Change storage while read is pending; the final copied order must be current.
    stub();js("window.barrier=new Promise(r=>window.release=r);currentOrder=async()=>{await window.barrier;return window.originalCurrentOrder()};document.querySelector('#sendVk').click();sendOrderToVk()")
    assert js('window.opens===1&&window.dest===""&&vkOrderBusy')
    mutate('requestCartChange('+json.dumps(slugs[0])+',1)')
    js('window.release()');wait_for('!vkOrderBusy');js('currentOrder=window.originalCurrentOrder')
    assert js('window.dest')==CONTACT
    assert js('window.popup.opener===null&&window.copied===buildOrder().message')
    for slug in slugs: assert 'https://skvoz-igolki.ru/product?product='+slug in js('window.copied')
    expected=js('JSON.stringify(cart)')
    assert 'Заказ скопирован.' in js("document.querySelector('#orderNotice').textContent")
    # Storage changes during asynchronous clipboard permission: do not open stale order.
    stub();js("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>{window.copied=t;await new Promise(r=>window.finishCopy=r)}}});document.querySelector('#sendVk').click()")
    wait_for('!!window.finishCopy');mutate('requestCartChange('+json.dumps(slugs[0])+',1)')
    js('window.finishCopy()');wait_for('!vkOrderBusy')
    assert js('window.popup.closed&&window.dest===""')
    assert 'изменился' in js("document.querySelector('#orderNotice').textContent")
    expected=js('JSON.stringify(cart)')
    # Blocked popup: full copy and native fallback link, safely protected from opener access.
    stub();js("window.open=()=>null;document.querySelector('#sendVk').click()");wait_for('!vkOrderBusy')
    assert js('window.copied===buildOrder().message')
    assert js("!document.querySelector('#vkFallback').hidden&&document.querySelector('#vkFallback').href===vkContactUrl()")
    assert js("document.querySelector('#vkFallback').rel.includes('noopener')&&document.querySelector('#vkFallback').target==='_blank'")
    # Clipboard denied: visible selectable order, closed reservation, no false success notice.
    stub();js("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied')}}});document.execCommand=()=>false;document.querySelector('#sendVk').click()")
    wait_for('!vkOrderBusy')
    assert js("window.popup.closed&&window.dest===''&&document.querySelector('#manualOrder').value===buildOrder().message")
    assert 'Браузер запретил копирование' in js("document.querySelector('#orderNotice').textContent")
    assert not js("document.querySelector('#vkFallback').hidden")
    # Normal copy button remains available as a separate fallback.
    stub();js("document.querySelector('#copyOrder').click()");wait_for('window.copied.length>0')
    assert js('window.copied===buildOrder().message')
    for expression in ["({entries:[],message:''})",None]:
        stub();js('currentOrder='+('async()=>{throw Error("read failed")}' if expression is None else 'async()=>'+expression))
        js("document.querySelector('#sendVk').click()");wait_for('!vkOrderBusy')
        assert js("window.popup.closed&&window.dest===''&&document.querySelector('#vkFallback').hidden")
        js('currentOrder=window.originalCurrentOrder')
    # Actual user activation reserves a real tab, but close it before releasing the read.
    for width in [320,375,430,768,1024,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
        assert js('document.documentElement.scrollWidth<=innerWidth')
    for width in [320,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
        stub();js("window.waitVk=new Promise(r=>window.finishVk=r);currentOrder=async()=>{await window.waitVk;return window.originalCurrentOrder()};window.open=(...args)=>(window.actualVkTab=window.nativeVkOpen(...args))")
        click('#sendVk')
        assert js('!!window.actualVkTab&&!window.actualVkTab.closed&&window.actualVkTab.opener===null')
        js('window.actualVkTab.close()');wait_for('window.actualVkTab.closed')
        js('window.finishVk()');wait_for('!vkOrderBusy')
        assert not js("document.querySelector('#vkFallback').hidden")
        js('currentOrder=window.originalCurrentOrder')
    assert js('JSON.stringify(cart)')==expected
    mutate('requestCartClear()');assert js("document.querySelector('#sendVk').disabled")
assert not errors,errors
print('PASS: VK current multi-product copy, exact dialog, invalid contacts, synchronous tab, double click, clipboard and popup denial, concurrent changes, error cleanup, cart retained, both pages and six widths: '+TEST_BASE)
