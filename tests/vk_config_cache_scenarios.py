"""An already-cached empty config must be replaced after a config rebuild."""
site=Path(os.environ['SKVOZ_SITE_ROOT'])
contact='https://vk.me/test_seller'
def wait_for(expression):
    for _ in range(200):
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression,errors))
def build(value):
    (site/'site-config.js').write_text('window.SHOP_CONFIG='+json.dumps({'SITE_URL':'https://skvoz-igolki.ru/','TELEGRAM_USERNAME':'Uliamel','VK_CONTACT_URL':value})+';\n',encoding='utf-8')
    subprocess.run(['node',str(ROOT/'tools/version-assets.cjs'),str(site)],check=True)
def stub():
    js("window.dest='';window.copied='';window.open=()=>({closed:false,opener:null,close(){},location:{replace:u=>window.dest=u}});Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>window.copied=t}})")
for page in ['index.html','product.html?product=tuya-smaragd']:
    build('');navigate(page);wait_for('cartReady')
    js("window.done=false;requestCartChange('tuya-smaragd',1).then(()=>window.done=true)");wait_for('window.done')
    count=js("cart['tuya-smaragd']")
    old=js("document.querySelector('script[src*=\"assets/site-config.\"]').src")
    stub();js('openCart();document.querySelector("#sendVk").click()')
    wait_for('!vkOrderBusy')
    assert js('window.dest')==''
    assert js("document.querySelector('#vkFallback').hidden")
    assert 'VK_CONTACT_URL' not in js('document.querySelector("#orderNotice").textContent')
    build(contact)
    call('Page.reload',{'ignoreCache':False});time.sleep(.3);wait_for('typeof cartReady!=="undefined"&&cartReady&&vkContactUrl()==='+json.dumps(contact))
    assert js("document.querySelector('script[src*=\"assets/site-config.\"]').src")!=old
    assert js("document.querySelectorAll('script[src*=\"assets/site-config.\"]').length")==1
    assert js("cart['tuya-smaragd']")==count
    stub();js('openCart();document.querySelector("#sendVk").click()');wait_for('!vkOrderBusy')
    assert js('window.dest')==contact
    assert js("document.querySelector('#vkFallback').href")==contact
    js("document.querySelector('#copyOrder').click()");wait_for('window.copied.length>0')
    assert js('window.copied===buildOrder().message')
    assert 'https://skvoz-igolki.ru/product?product=tuya-smaragd' in js('window.copied')
    assert js("cart['tuya-smaragd']")==count
assert not errors,errors
print('PASS: cached empty VK config -> changed hashed config -> exact seller dialog and full copied order on both pages without cache clear; cart retained: '+TEST_BASE)
