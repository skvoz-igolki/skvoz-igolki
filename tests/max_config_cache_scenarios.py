"""An already-cached empty config must be replaced after a config rebuild."""
site=Path(os.environ['SKVOZ_SITE_ROOT'])
contact='https://max.ru/u/f9LHodD0cOK_pii8PJA9GDRXPq8bQW_r_vbuGnqgusdUTxmHOduB3OaolQI'
def wait_for(expression):
    for _ in range(200):
        if js(expression): return
        time.sleep(.05)
    raise AssertionError((expression,errors))
def build(value):
    (site/'site-config.js').write_text('window.SHOP_CONFIG='+json.dumps({'SITE_URL':'https://skvoz-igolki.ru/','TELEGRAM_USERNAME':'Uliamel','MAX_CONTACT_URL':value})+';\n',encoding='utf-8')
    subprocess.run(['node',str(ROOT/'tools/version-assets.cjs'),str(site)],check=True)
def stub():
    js("window.dest='';window.copied='';window.open=()=>({closed:false,opener:null,close(){},location:{replace:u=>window.dest=u}});Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>window.copied=t}})")
for page in ['index.html','product.html?product=tuya-smaragd']:
    build('');navigate(page);wait_for('cartReady')
    js("window.done=false;requestCartChange('tuya-smaragd',1).then(()=>window.done=true)");wait_for('window.done')
    count=js("cart['tuya-smaragd']")
    old=js("document.querySelector('script[src*=\"assets/site-config.\"]').src")
    stub();js('openCart();document.querySelector("#sendMax").click()')
    assert js('window.dest')==''
    assert 'MAX_CONTACT_URL' not in js('document.querySelector("#orderNotice").textContent')
    build(contact)
    call('Page.reload',{'ignoreCache':False});time.sleep(.3);wait_for('typeof cartReady!=="undefined"&&cartReady&&maxContactUrl()==='+json.dumps(contact))
    assert js("document.querySelector('script[src*=\"assets/site-config.\"]').src")!=old
    assert js("document.querySelectorAll('script[src*=\"assets/site-config.\"]').length")==1
    assert js("cart['tuya-smaragd']")==count
    stub();js('openCart();document.querySelector("#sendMax").click()');wait_for('!maxOrderBusy')
    assert js('window.dest')==contact
    assert js('window.copied===buildOrder().message')
    assert 'https://skvoz-igolki.ru/product?product=tuya-smaragd' in js('window.copied')
    assert js("cart['tuya-smaragd']")==count
assert not errors,errors
print('PASS: cached empty MAX config -> changed hashed config -> exact seller profile and full copied order on both pages without cache clear; cart retained: '+TEST_BASE)
