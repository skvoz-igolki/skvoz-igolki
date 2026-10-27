"""Toggle buttons and accessible cart notifications, through file:// and HTTPS."""
import os
from urllib.parse import urlparse,parse_qs

def wait_for(expression, timeout=10):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if js(expression): return
        time.sleep(.04)
    raise AssertionError((expression,js('location.href'),errors))

def loaded(): wait_for("typeof cartReady!=='undefined'&&cartReady&&document.readyState==='complete'")
def pages(): return [t for t in call('Target.getTargets')['targetInfos'] if t['type']=='page']
def connect(target):
    tabs=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
    return websocket.create_connection(next(t for t in tabs if t['id']==target)['webSocketDebuggerUrl'],timeout=15)
def key(name,code,number):
    for kind in ['keyDown','keyUp']:
        event={'type':kind,'key':name,'code':code,'windowsVirtualKeyCode':number,'nativeVirtualKeyCode':number}
        if kind=='keyDown' and code=='Enter': event['text']='\r'
        call('Input.dispatchKeyEvent',event)

navigate('index.html');loaded()
slug=js("items.find(p=>p.availability!==false).slug")
button='[data-add='+json.dumps(slug)+']'
selector=json.dumps(button)
state=lambda label: f'document.querySelector({selector}).textContent==={json.dumps(label)}'
enabled=f'!document.querySelector({selector}).disabled'
count=lambda n: f'(cart[{json.dumps(slug)}]||0)==={n}'
mode=os.environ.get('SKVOZ_ORDER_MODE','restore')

if mode=='seed':
    assert js('Object.keys(cart).length')==0
    assert js(state('Добавить в корзину'))
    before=len(pages())
    # Two programmatic activations in the same task; native double click also has detail=2.
    js(f'document.querySelector({selector}).click();document.querySelector({selector}).click()')
    wait_for(count(1));wait_for(state('Удалить из корзины'))
    assert len(pages())==before
    assert js("document.querySelector('#toastMessage').textContent")=='Добавлено в корзину'
    assert not js("document.querySelector('#toast').hidden")
    assert js("document.querySelector('#openCart').onclick===openCart")
    click('#toastCart')
    assert js("document.querySelector('#overlay').classList.contains('open')")
    assert js("document.querySelector('#toast').hidden")
    assert js("document.activeElement.id")=='closeCart'
    click('[data-delta="1"]');wait_for(count(2))
    click('[data-delta="1"]');wait_for(count(3))
    js("toast('Проверка уведомления при открытой корзине')")
    assert js("document.querySelector('#toast').hidden")
    click('#closeCart');wait_for(enabled)
    click(button);wait_for(count(0));wait_for(state('Добавить в корзину'))
    assert len(pages())==before
    wait_for(enabled);click(button);wait_for(count(1))

    # Hover pauses expiry, then the toast expires after pointer exit.
    point=js("(()=>{const r=document.querySelector('#toast').getBoundingClientRect();return {x:r.x+10,y:r.y+10}})()")
    call('Input.dispatchMouseEvent',{'type':'mouseMoved',**point})
    time.sleep(4.5)
    assert not js("document.querySelector('#toast').hidden")
    call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':5,'y':5})
    wait_for("document.querySelector('#toast').hidden",6)
    # Focusing the real action keeps the toast available; Space/Enter use native buttons.
    js("toast('Добавлено в корзину',{cartAction:true});document.querySelector('#toastCart').focus()")
    time.sleep(4.5)
    assert not js("document.querySelector('#toast').hidden")
    key(' ','Space',32)
    wait_for("document.querySelector('#overlay').classList.contains('open')")
    assert js("document.querySelector('#toast').hidden")
    click('#closeCart')
    assert js('document.activeElement.id')=='openCart'
    js("toast('Добавлено в корзину',{cartAction:true});document.querySelector('#toastCart').focus()")
    key('Enter','Enter',13)
    wait_for("document.querySelector('#overlay').classList.contains('open')")
    click('#closeCart')
    js("toast('Добавлено в корзину',{cartAction:true})")
    click('#toastMessage')
    wait_for("document.querySelector('#overlay').classList.contains('open')")
    click('[data-delta="1"]');wait_for(count(2))
    click('[data-delta="1"]');wait_for(count(3))
    click('#closeCart')
    print('PASS: add/remove-all, double click, actionable toast/click/Enter/Space, hover/focus expiry pause, no toast over cart; saved quantity=3: '+TEST_BASE)
else:
    assert js(count(3)), 'Cart lost on browser restart'
    assert js(state('Удалить из корзины'))
    for no_cache in [False,True]:
        call('Page.reload',{'ignoreCache':no_cache});time.sleep(.3);loaded()
        assert js(count(3)) and js(state('Удалить из корзины'))
    navigate('product.html?product='+slug);loaded()
    assert js(state('Удалить из корзины'))
    click(button);wait_for(count(0));wait_for(state('Добавить в корзину'))
    original_ws=ws
    other=call('Target.createTarget',{'url':TEST_BASE+'/index.html'})['targetId']
    ws=connect(other);call('Runtime.enable');call('Page.enable');loaded()
    assert js(state('Добавить в корзину'))
    click(button);wait_for(count(1));wait_for(state('Удалить из корзины'))
    other_ws=ws;ws=original_ws
    wait_for(count(1));wait_for(state('Удалить из корзины'))
    ws=other_ws
    click('#toastCart')
    click('[data-delta="1"]');wait_for(count(2))
    click('[data-delta="1"]');wait_for(count(3))
    ws=original_ws;wait_for(count(3));wait_for(enabled)
    click(button);wait_for(count(0))
    ws=other_ws;wait_for(count(0));wait_for(state('Добавить в корзину'))
    assert js("document.querySelector('#toast').hidden")
    ws=original_ws;wait_for(enabled);click(button);wait_for(count(1))
    ws=other_ws;wait_for(count(1));click('[data-delta="-1"]');wait_for(count(0))
    ws=original_ws;wait_for(state('Добавить в корзину'));wait_for(enabled)
    # A second native click in a double-click sequence must not toggle back.
    js(f'document.querySelector({selector}).dispatchEvent(new MouseEvent("click",{{bubbles:true,detail:1}}));document.querySelector({selector}).dispatchEvent(new MouseEvent("click",{{bubbles:true,detail:2}}))')
    wait_for(count(1));time.sleep(.65)
    assert js(count(1))
    click('#openCart')
    js("window.copied='';Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copied=text}}});window.prepared='';window.open=()=>({opener:null,closed:false,document:{body:{textContent:''}},location:{replace:url=>window.prepared=url},close(){this.closed=true}})")
    click('#copyOrder');wait_for('window.copied.length>0')
    assert js('window.copied===buildOrder().message')
    assert js("document.querySelector('#toast').hidden")
    click('#sendTelegram');wait_for('window.prepared.length>0')
    parsed=urlparse(js('window.prepared'))
    assert parsed.path=='/Uliamel' and parse_qs(parsed.query)['text'][0]==js('buildOrder().message')
    assert js(count(1))
    click('#closeCart')
    for width in [320,375,768,1024,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':900,'deviceScaleFactor':1,'mobile':width<760})
        assert js('document.documentElement.scrollWidth<=innerWidth')
        assert js(f'document.querySelector({selector}).getBoundingClientRect().height>=44')
        js("toast('Добавлено в корзину',{cartAction:true})")
        assert js("document.querySelector('#toastCart').getBoundingClientRect().height>=44")
        assert js("document.querySelector('#toast').getBoundingClientRect().width<=innerWidth")
        click('#toastCart')
        assert js("document.querySelector('#overlay').classList.contains('open')&&document.querySelector('#toast').hidden")
        click('#closeCart')
    ws=other_ws
    click('#closeCart')
    unavailable=js("items.find(p=>p.availability===false)?.slug||null")
    if unavailable:
        if js("document.querySelector('#inStockOnly').checked"): click('#inStockOnly')
        unavailable_button='[data-add='+json.dumps(unavailable)+']'
        assert js(f'document.querySelector({json.dumps(unavailable_button)}).disabled')
        assert js(f'document.querySelector({json.dumps(unavailable_button)}).textContent')=='Нет в наличии'
        js(f'window.denied=false;requestCartToggle({json.dumps(unavailable)}).then(()=>window.denied=true)');wait_for('window.denied')
        assert not js(f'!!cart[{json.dumps(unavailable)}]')
        js(f'window.denied=false;cartRequest("toggle",{{slug:{json.dumps(unavailable)}}}).then(()=>window.denied=true)');wait_for('window.denied')
        assert not js(f'!!cart[{json.dumps(unavailable)}]')
    ws.close();ws=original_ws;call('Target.closeTarget',{'targetId':other})
    print('PASS: persisted button state, F5/Ctrl+F5/browser restart, product remove-all, cross-tab buttons/quantity/removal, double click, copy/Telegram, 320-1440/mobile toast, unavailable guard: '+TEST_BASE)
assert not errors,errors
ws.close()
