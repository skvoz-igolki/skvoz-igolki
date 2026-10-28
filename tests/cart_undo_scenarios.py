import os
from urllib.parse import urlparse
def wait_for(expression,timeout=10):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if js(expression):return
        time.sleep(.04)
    raise AssertionError((expression,js('location.href'),errors))
def loaded():wait_for("typeof cartReady!=='undefined'&&cartReady&&document.readyState==='complete'")
def key(name,code,vk):
    for kind in ['keyDown','keyUp']:
        event={'type':kind,'key':name,'code':code,'windowsVirtualKeyCode':vk,'nativeVirtualKeyCode':vk}
        if kind=='keyDown' and code=='Enter':event['text']='\r'
        call('Input.dispatchKeyEvent',event)
def count(slug,n):return f'(cart[{json.dumps(slug)}]||0)==={n}'
def change(slug,delta):
    js(f"window.done=false;requestCartChange({json.dumps(slug)},{delta}).then(()=>window.done=true)");wait_for('window.done')
def quantity(slug,n):
    current=js(f'cart[{json.dumps(slug)}]||0')
    for _ in range(abs(n-current)):change(slug,1 if n>current else -1)
def remove(slug):
    selector='[data-add='+json.dumps(slug)+']'
    wait_for(f'!document.querySelector({json.dumps(selector)}).disabled')
    click(selector);wait_for(count(slug,0))
    wait_for(f'lastCartRemoval?.slug==={json.dumps(slug)}')
def restore(slug,n):
    click('#toastUndo');wait_for(count(slug,n));wait_for('pendingCartRestores.size===0')
def connect(target):
    tabs=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
    return websocket.create_connection(next(t for t in tabs if t['id']==target)['webSocketDebuggerUrl'],timeout=15)
navigate('index.html');loaded()
available=js("items.filter(p=>p.availability!==false).map(p=>p.slug)")
a,b=available[:2]
if os.environ.get('SKVOZ_ORDER_MODE')=='restore':
    assert js(count(a,5))
    assert js('lastCartRemoval===null')
    assert js("document.querySelector('#toast').hidden")
    assert js(f"document.querySelector('[data-add=\"{a}\"]').textContent")=='Удалить из корзины'
    print('PASS: restored quantity persisted through browser restart; undo snapshot was not persisted: '+TEST_BASE)
else:
    assert js('Object.keys(cart).length')==0
    quantity(a,1);remove(a)
    assert js("document.querySelector('#toastMessage').textContent")=='Удалено из корзины'
    assert not js("document.querySelector('#toastUndo').hidden")
    click('#toastMessage')
    assert js(count(a,0)) and js("document.querySelector('#overlay').hidden")
    restore(a,1)
    quantity(a,5);remove(a)
    assert js('lastCartRemoval.quantity')==5
    js("document.querySelector('#toastUndo').click();document.querySelector('#toastUndo').click()")
    wait_for(count(a,5));wait_for('pendingCartRestores.size===0')
    assert js("document.querySelector('#basketCount').textContent")=='5'
    navigate('product.html?product='+a);loaded()
    remove(a);restore(a,5)
    # Deletion of the last quantity in the drawer uses the same notice, inside the modal.
    quantity(a,1);click('#openCart');click('[data-delta="-1"]');wait_for(count(a,0))
    wait_for('lastCartRemoval?.quantity===1')
    assert js("document.querySelector('#toast').classList.contains('in-cart')&&document.querySelector('#overlay').contains(document.querySelector('#toast'))")
    for _ in range(8):
        if js("document.activeElement.id==='toastUndo'"):break
        key('Tab','Tab',9)
        assert js("document.querySelector('#overlay').contains(document.activeElement)")
    assert js("document.activeElement.id")=='toastUndo'
    key(' ','Space',32);wait_for(count(a,1));wait_for('pendingCartRestores.size===0')
    assert js("!document.querySelector('#overlay').hidden")
    click('#closeCart')
    navigate('index.html');loaded();quantity(a,5);quantity(b,2)
    remove(a);remove(b)
    assert js(f'lastCartRemoval.slug==={json.dumps(b)}&&lastCartRemoval.quantity===2')
    assert js("document.querySelectorAll('#toast').length") == 1
    restore(b,2);assert js(count(a,0))
    quantity(a,5);remove(a);change(a,1)
    click('#toastUndo');wait_for('pendingCartRestores.size===0')
    assert js(count(a,1))
    assert 'количество сохранено' in js("document.querySelector('#toastMessage').textContent")
    # Re-adding through a product button replaces undo with the existing add notice.
    remove(a)
    wait_for(f"!document.querySelector('[data-add=\"{a}\"]').disabled")
    click('[data-add='+json.dumps(a)+']');wait_for(count(a,1))
    assert js('lastCartRemoval===null')
    assert not js("document.querySelector('#toastCart').hidden")
    # Another tab re-adds the removed product: do not overwrite its quantity.
    quantity(a,5);remove(a);main_ws=ws
    target=call('Target.createTarget',{'url':TEST_BASE+'/index.html'})['targetId']
    ws=connect(target);call('Runtime.enable');call('Page.enable');loaded()
    quantity(a,2);other_ws=ws;ws=main_ws;wait_for(count(a,2))
    click('#toastUndo');wait_for('pendingCartRestores.size===0');assert js(count(a,2))
    # Changes to a different position must be retained when undo succeeds.
    quantity(a,5);remove(a);ws=other_ws;quantity(b,4);ws=main_ws;wait_for(count(b,4))
    restore(a,5);assert js(count(b,4))
    ws=other_ws;wait_for(count(a,5));assert js(count(b,4))
    ws.close();ws=main_ws;call('Target.closeTarget',{'targetId':target})
    # A newer deletion must survive completion of an earlier async undo.
    quantity(a,5);remove(a)
    js("window.originalCartRequest=cartRequest;cartRequest=(action,fields={})=>{const response=window.originalCartRequest(action,fields);return action==='restore'?response.then(value=>new Promise(resolve=>{window.finishEarlierUndo=()=>resolve(value)})):response}")
    js("document.querySelector('#toastUndo').click()")
    wait_for("typeof window.finishEarlierUndo==='function'")
    wait_for(count(a,5))
    remove(b)
    assert js(f'lastCartRemoval.slug==={json.dumps(b)}')
    js('cartRequest=window.originalCartRequest;window.finishEarlierUndo()')
    wait_for('pendingCartRestores.size===0')
    assert js(f'lastCartRemoval.slug==={json.dumps(b)}')
    assert js("document.querySelector('#toastMessage').textContent")=='Удалено из корзины'
    restore(b,4)
    # Only the isolated copy's generated file is varied. Source JSON/catalog stay unchanged.
    catalog=Path(os.environ['SKVOZ_TEST_SITE_PATH'])/'catalog.generated.js'
    baseline=catalog.read_text(encoding='utf-8')
    raw=json.loads(baseline.split('window.CATALOG = ',1)[1].strip().removesuffix(';'))
    original_price=next(p['price'] for p in raw if p['slug']==a)
    def write_catalog(values):catalog.write_text('window.CATALOG = '+json.dumps(values,ensure_ascii=False)+';\n',encoding='utf-8')
    try:
        remove(a)
        changed=[dict(p) for p in raw]
        next(p for p in changed if p['slug']==a)['price']=original_price+137
        write_catalog(changed);restore(a,5)
        assert js(f'items.find(p=>p.slug==={json.dumps(a)}).price')==original_price+137
        expected=js('Object.entries(cart).reduce((s,[slug,n])=>s+items.find(p=>p.slug===slug).price*n,0)')
        assert js('buildOrder().total')==expected
        for variant in ['unavailable','deleted']:
            catalog.write_text(baseline,encoding='utf-8');navigate('index.html');loaded();quantity(a,5);remove(a)
            changed=[dict(p) for p in raw]
            if variant=='deleted':changed=[p for p in changed if p['slug']!=a]
            else:next(p for p in changed if p['slug']==a)['availability']=False
            write_catalog(changed);click('#toastUndo');wait_for('pendingCartRestores.size===0')
            wait_for("document.querySelector('#toastMessage').textContent==='Не удалось вернуть товар: его больше нет в наличии'")
            assert js(count(a,0))
        catalog.write_text(baseline,encoding='utf-8');navigate('index.html');loaded();quantity(a,5);remove(a)
        catalog.write_text('',encoding='utf-8')
        click('#toastUndo');wait_for('pendingCartRestores.size===0')
        assert js(count(a,0)), 'An empty script must not reuse the previously loaded catalog'
    finally:catalog.write_text(baseline,encoding='utf-8')
    navigate('index.html');loaded();quantity(a,1);remove(a)
    call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':2,'y':2})
    wait_for("document.querySelector('#toast').hidden",6)
    assert js('lastCartRemoval===null')
    quantity(a,1);remove(a)
    time.sleep(.25)  # Let the toast appearance transition settle before pointer coordinates.
    point=js("(()=>{const r=document.querySelector('#toast').getBoundingClientRect();return {x:r.x+8,y:r.y+8}})()")
    call('Input.dispatchMouseEvent',{'type':'mouseMoved',**point});time.sleep(5.2)
    assert js('lastCartRemoval!==null') and not js("document.querySelector('#toast').hidden")
    js("document.querySelector('#toastUndo').focus()")
    call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':2,'y':2});time.sleep(.3)
    key('Enter','Enter',13);wait_for(count(a,1));wait_for('pendingCartRestores.size===0')
    remove(a);js('hideToast()');assert js('lastCartRemoval===null')
    assert js(count(a,0))
    for width in [320,375,768,1024,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':800,'deviceScaleFactor':1,'mobile':width<760})
        quantity(a,1);remove(a)
        assert js("document.querySelector('#toast').getBoundingClientRect().width<=innerWidth")
        assert js("document.querySelector('#toastUndo').getBoundingClientRect().height>=44")
        restore(a,1)
    quantity(a,5)
    print('PASS: undo 1/5 quantities, all removal entry points, double activation, last-only snapshot, manual/cross-tab conflicts, fresh price/availability/deletion, expiry/hover/keyboard/mobile, persistent quantities: '+TEST_BASE)
assert not errors,errors
ws.close()
