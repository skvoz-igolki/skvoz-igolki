"""Official MAX share URL, popup lifecycle and fallback actions; no MAX requests."""
from urllib.parse import urlparse,parse_qs
def wait_for(expression):
    for _ in range(200):
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression,errors))
def mutate(expression):
    js('window.done=false;('+expression+').then(()=>window.done=true)');wait_for('window.done')
def stub():
    js("window.opens=0;window.dest='';window.copied='';window.open=()=>{window.opens++;return window.popup={closed:false,opener:'initial',close(){this.closed=true},location:{replace:u=>window.dest=u}}};Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>window.copied=t}})")
def check_url():
    url=js('window.dest');parsed=urlparse(url)
    assert parsed.scheme=='https' and parsed.netloc=='max.ru' and parsed.path=='/:share'
    assert parse_qs(parsed.query)['text'][0]==js('buildOrder().message')
    assert '%0A' in url and '%D0' in url and '%26' in url and '%2B' in url
    assert js("buildOrder().message.includes('https://skvoz-igolki.ru/product?product=')")
for page in ['index.html','product.html?product=tuya-smaragd']:
    navigate(page);wait_for('cartReady');mutate('requestCartClear()')
    js('window.nativeMaxOpen=window.open.bind(window)')
    stub();js('sendOrderToMax()');assert js('window.opens===0&&document.querySelector("#sendMax").disabled')
    slugs=js('items.filter(p=>p.availability!==false).slice(0,2).map(p=>p.slug)')
    for slug in slugs:
        for _ in range(2):mutate('requestCartChange('+json.dumps(slug)+',1)')
    js('items.find(p=>p.slug==='+json.dumps(slugs[0])+').name+=" & + # ? %";openCart()')
    original_contact=js('SHOP_CONFIG.MAX_CONTACT_URL')
    assert js("!document.querySelector('#maxFallback').hidden&&document.querySelector('#maxFallback').href===maxContactUrl()")
    # Hold storage preparation: the reserved popup must already exist, and double activation is ignored.
    stub();js("window.originalCurrentOrder=currentOrder;window.barrier=new Promise(r=>window.release=r);currentOrder=async()=>{await window.barrier;return window.originalCurrentOrder()};document.querySelector('#sendMax').click();sendOrderToMax()")
    assert js('window.opens===1&&window.dest===""&&maxOrderBusy')
    mutate('requestCartChange('+json.dumps(slugs[0])+',1)')
    js('window.release()');wait_for('!maxOrderBusy');js('currentOrder=window.originalCurrentOrder')
    check_url();assert js('window.popup.opener===null&&window.copied===""')
    expected=js('JSON.stringify(cart)')
    for contact in ['', 'javascript:alert(1)','https://max.ru.evil/u/person',original_contact]:
        stub();js('SHOP_CONFIG.MAX_CONTACT_URL='+json.dumps(contact)+';renderCart();document.querySelector("#sendMax").click()')
        wait_for('!maxOrderBusy');check_url()
        assert js('JSON.stringify(cart)')==expected
        assert js("document.querySelector('#maxFallback').hidden")== (contact!=original_contact)
    # A blocked popup exposes the share URL; clipboard denial retains manual-copy text.
    js("window.open=()=>null;document.querySelector('#sendMax').click()")
    wait_for('!maxOrderBusy')
    fallback=js("document.querySelector('#maxShareFallback').href")
    assert parse_qs(urlparse(fallback).query)['text'][0]==js('buildOrder().message')
    assert not js("document.querySelector('#maxShareFallback').hidden")
    js("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied')}}});document.execCommand=()=>false;document.querySelector('#copyOrder').click()")
    wait_for("!!document.querySelector('#manualOrder')")
    assert js("document.querySelector('#manualOrder').value===buildOrder().message")
    js("document.querySelector('#maxFallback').addEventListener('click',e=>{e.preventDefault();window.profile=e.currentTarget.href});document.querySelector('#maxFallback').click()")
    assert js('window.profile')==original_contact
    stub();js("document.querySelector('#copyOrder').click()");wait_for('window.copied.length>0')
    assert js('window.copied===buildOrder().message')
    # Close reservations for a long order, an emptied cart and preparation failure.
    for expression in ["({...buildOrder(),message:buildOrder().message.repeat(30)})", "({entries:[],message:''})", None]:
        stub()
        js('currentOrder='+('async()=>{throw Error("read failed")}' if expression is None else 'async()=>'+expression))
        js("document.querySelector('#sendMax').click()");wait_for('!maxOrderBusy')
        assert js("window.popup.closed&&window.dest===''&&document.querySelector('#maxShareFallback').hidden")
        assert js('JSON.stringify(cart)')==expected
        js('currentOrder=window.originalCurrentOrder')
    for width in [320,375,430,768,1024,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
        assert js('document.documentElement.scrollWidth<=innerWidth')
    # Exercise real browser user activation; close the blank tab before releasing the read.
    for width in [320,375,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
        js("window.waitMax=new Promise(r=>window.finishMax=r);currentOrder=async()=>{await window.waitMax;return window.originalCurrentOrder()};window.open=(...args)=>(window.actualMaxTab=window.nativeMaxOpen(...args))")
        click('#sendMax')
        assert js('!!window.actualMaxTab&&!window.actualMaxTab.closed&&window.actualMaxTab.opener===null')
        js('window.actualMaxTab.close()');wait_for('window.actualMaxTab.closed')
        js('window.finishMax()');wait_for('!maxOrderBusy')
        assert not js("document.querySelector('#maxShareFallback').hidden")
        js('currentOrder=window.originalCurrentOrder')
    mutate('requestCartClear()');assert js("document.querySelector('#sendMax').disabled")
assert not errors,errors
print('PASS: decoded MAX share equals fresh multi-product order; special characters, links, no-contact share, synchronous popup, double-click lock, empty/error/long-order cleanup, copy/profile fallbacks, cart preservation and six widths on both pages: '+TEST_BASE)
