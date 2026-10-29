"""Mobile hero geometry; fixtures stay in the test page, never in site assets."""
navigate('index.html')
for _ in range(100):
    if js('cartReady'): break
    time.sleep(.05)
source=js("document.querySelector('.hero-photo').src")
for width in [320,360,375,390,412,430,768,1024,1440]:
    call('Emulation.setDeviceMetricsOverride',{'width':width,'height':850,'deviceScaleFactor':1,'mobile':width<768})
    # A deterministic landscape photo shape also works when Unsplash is offline.
    fixture='<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900"><rect width="1600" height="900" fill="#719775"/></svg>'
    js('document.querySelector(".hero-photo").src='+json.dumps('data:image/svg+xml;base64,'+base64.b64encode(fixture.encode()).decode()))
    for _ in range(100):
        if js("document.querySelector('.hero-photo').complete&&document.querySelector('.hero-photo').naturalWidth===1600"): break
        time.sleep(.05)
    assert js('document.documentElement.scrollWidth<=innerWidth'),width
    if width<768:
        assert js("(()=>{const r=s=>document.querySelector(s).getBoundingClientRect(),i=r('.hero-photo'),h=r('.hero h1'),p=r('.hero p'),b=r('.hero .cta'),hero=r('.hero');return Math.abs(i.width-hero.width)<1&&Math.abs(i.height-i.width*900/1600)<1&&h.bottom<=i.bottom+1&&h.top>=i.top&&p.top>=i.bottom-1&&b.top>=p.bottom-1})()"),width
        assert js("getComputedStyle(document.querySelector('.hero .eyebrow')).display==='none'&&getComputedStyle(document.querySelector('.hero-stamp')).display==='none'"),width
    else:
        assert js("getComputedStyle(document.querySelector('.hero-inner')).display!=='contents'&&getComputedStyle(document.querySelector('.hero-stamp')).display!=='none'"),width
js('document.querySelector(".hero-photo").src='+json.dumps(source))
assert not errors,errors
print('PASS: nine widths, full-width proportional mobile image, title inside photo, description and CTA below, hidden labels, desktop preserved; no page overflow or JavaScript errors: '+TEST_BASE)
