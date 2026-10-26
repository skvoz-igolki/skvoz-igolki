from urllib.parse import urlparse,parse_qs,quote
PUBLIC='https://skvoz-igolki-miv3dgeniy-7rsq.onreza.app/'
def wait_for(expression):
    for _ in range(200):
        if js(expression):return
        time.sleep(.04)
    raise AssertionError((expression,js('location.href'),errors))
def loaded():wait_for("typeof cartReady!=='undefined'&&cartReady&&document.readyState==='complete'")
navigate('index.html');loaded()
assert js('window.SHOP_CONFIG.SITE_URL')==PUBLIC
slugs=js("items.filter(p=>p.availability!==false).slice(0,2).map(p=>p.slug)")
for slug,n in zip(slugs,[2,3]):
    for _ in range(n):
        js(f'window.changed=false;requestCartChange({json.dumps(slug)},1).then(()=>window.changed=true)');wait_for('window.changed')
for page in ['index.html','product.html?product='+slugs[0]]:
    navigate(page);loaded()
    scripts=js("[...document.scripts].filter(s=>s.src).map(s=>({name:new URL(s.src).pathname.split('/').pop(),defer:s.defer,async:s.async}))")
    names=[s['name'] for s in scripts]
    assert names.index('site-config.js')<names.index('order.js')<names.index('app.js')
    assert next(s for s in scripts if s['name']=='site-config.js')['defer']
    js("window.baseBuildOrder=buildOrder;window.orderContexts=[];buildOrder=function(){window.orderContexts.push({config:window.SHOP_CONFIG?{...window.SHOP_CONFIG}:null,base:publicSiteUrl(),product:productUrl(items.find(p=>cart[p.slug]>0))});return window.baseBuildOrder()}")
    js("window.prepared='';window.open=()=>({opener:null,closed:false,document:{body:{textContent:''}},location:{replace:url=>window.prepared=url},close(){this.closed=true}})")
    click('#openCart')
    automatic=TEST_BASE+'/' if TEST_BASE.startswith('https:') else None
    # Explicit public config must win over the local HTTPS test origin and subfolder.
    cases=[(PUBLIC,PUBLIC),('',automatic),(PUBLIC.rstrip('/'),PUBLIC)]
    for setting,expected_base in cases:
        js(f'window.SHOP_CONFIG.SITE_URL={json.dumps(setting)};renderCart();window.prepared="";window.orderContexts=[]')
        assert js('publicSiteUrl()')==expected_base
        click('#sendTelegram');wait_for('window.prepared.length>0')
        url=js('window.prepared');parsed=urlparse(url)
        assert parsed.scheme=='https' and parsed.netloc=='t.me' and parsed.path=='/Uliamel'
        message=parse_qs(parsed.query)['text'][0]
        assert message==js('buildOrder().message')
        assert message.count('Количество:')==2 and message.count('Цена:')==2 and 'Итого:' in message
        assert '%0A' in url and '%D0' in url
        links=[line.removeprefix('Ссылка: ') for line in message.splitlines() if line.startswith('Ссылка: ')]
        expected=[expected_base+'product.html?product='+quote(slug,safe='') for slug in slugs] if expected_base else []
        assert links==expected,(links,expected)
        assert 'file://' not in message
        for recorded in js('window.orderContexts'):
            assert recorded['config'] is not None and recorded['config']['SITE_URL']==setting
            assert recorded['base']==expected_base
            assert recorded['product']=='product.html?product='+quote(slugs[0],safe='')
        assert js("document.querySelector('#basketCount').textContent")=='5'
    # Simulate an absent or late config without caching an empty value forever.
    js('window.savedShopConfig=window.SHOP_CONFIG;delete window.SHOP_CONFIG')
    assert js('publicSiteUrl()')==automatic
    assert js('buildOrder().hasPublicUrl')==bool(automatic)
    js('window.SHOP_CONFIG=window.savedShopConfig')
    assert js('publicSiteUrl()')==PUBLIC
    for setting in ['file:///private/catalog/', 'http://127.0.0.1/']:
        js(f'window.SHOP_CONFIG.SITE_URL={json.dumps(setting)}')
        assert js('publicSiteUrl()') is None
        assert 'file://' not in js('buildOrder().message')
    js(f'window.SHOP_CONFIG.SITE_URL={json.dumps(PUBLIC)}')
    click('#closeCart')
assert not errors,errors
print('PASS: config available at buildOrder call, deferred script order, config -> base -> per-slug HTTPS links -> decoded Telegram draft on both pages: '+TEST_BASE)
ws.close()
