"""MAX contact transitions are mocked; no real chat requests or messages."""
def wait_for(expression):
    for _ in range(200):
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression,errors))

for page in ['index.html','product.html?product=tuya-smaragd']:
    navigate(page);wait_for('cartReady')
    js('window.done=false;requestCartClear().then(()=>window.done=true)');wait_for('window.done')
    assert js("document.querySelector('#sendMax').disabled&&document.querySelector('#toastClose')===null")
    js("window.done=false;requestCartChange('tuya-smaragd',1).then(()=>window.done=true)");wait_for('window.done')
    js("openCart();window.opens=0;window.dest='';window.copied='';window.open=()=>{window.opens++;return {closed:false,opener:null,close(){this.closed=true},location:{replace:u=>window.dest=u}}};Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>window.copied=t}})")
    js("SHOP_CONFIG.MAX_CONTACT_URL='';document.querySelector('#sendMax').click()")
    assert js('window.opens===0')
    assert js("document.querySelector('#orderNotice').textContent.includes('MAX_CONTACT_URL')")
    for bad in ['javascript:alert(1)','https://max.ru.evil/u/profile','https://max.ru/:share','file:///profile']:
        js('SHOP_CONFIG.MAX_CONTACT_URL='+json.dumps(bad))
        assert js('maxContactUrl()===null')
    js("SHOP_CONFIG.MAX_CONTACT_URL='https://max.ru/u/test-profile';document.querySelector('#sendMax').click()")
    assert js('window.opens===1'), 'Must reserve window synchronously'
    wait_for('!maxOrderBusy')
    assert js("window.dest===SHOP_CONFIG.MAX_CONTACT_URL&&window.copied===buildOrder().message&&window.copied.includes('https://')&&cart['tuya-smaragd']===1")
    js("window.open=()=>null;Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied')}}});document.execCommand=()=>false;document.querySelector('#sendMax').click()")
    wait_for('!maxOrderBusy')
    assert js("!document.querySelector('#maxFallback').hidden&&document.querySelector('#manualOrder').value===buildOrder().message")
    js('closeCart()')
    for width in [320,375,430,768,1024,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
        assert js('document.documentElement.scrollWidth<=innerWidth'),(page,width)
        assert js("[...document.querySelectorAll('[data-add]')].every(b=>getComputedStyle(b).justifyContent==='center'&&getComputedStyle(b).alignItems==='center')"),(page,width)
    js('window.done=false;requestCartClear().then(()=>window.done=true)');wait_for('window.done')
assert not errors,errors
print('PASS: MAX missing/invalid contact, exact shared order, synchronous popup, denied clipboard/manual copy, popup fallback, unchanged cart; centered buttons on both pages, six widths; no real messages.')
