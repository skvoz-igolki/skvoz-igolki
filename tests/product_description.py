"""Description integration: source JSON -> generated JS -> file:// page."""
description_data = json.loads(original_json)
description_text = description_data['description']
assert len(description_text) > 4000
try:
    navigate('product.html?product=zz-test-product')
    loaded()
    assert js("window.CATALOG.find(p=>p.slug==='zz-test-product').description") == description_text
    assert js("document.querySelectorAll('.plant-description').length") == 1
    assert js("document.querySelector('#plantDescriptionTitle').textContent") == 'Описание растения'
    assert js("document.querySelector('.plant-description .product-description').textContent") == description_text.strip()
    assert js("document.querySelector('.product-summary .product-description')===null")
    assert js("document.querySelector('.plant-description').previousElementSibling.classList.contains('product-layout')")
    assert js("document.querySelector('.plant-description').nextElementSibling.classList.contains('plant-characteristics')")
    assert js("document.querySelector('.plant-description script')===null && !window.descriptionExecuted")
    assert js("getComputedStyle(document.querySelector('.product-description')).whiteSpace") == 'pre-wrap'
    for width in [320,375,768,1024,1440]:
        call('Emulation.setDeviceMetricsOverride', {'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width<760})
        assert js('document.documentElement.scrollWidth<=innerWidth'), width
    for width,label in [(1440,'desktop'),(375,'mobile')]:
        call('Emulation.setDeviceMetricsOverride', {'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width<760})
        js("document.querySelector('.plant-description').scrollIntoView({block:'start',behavior:'instant'})")
        time.sleep(.2)
        result = call('Page.captureScreenshot', {'format':'png'})
        artifact_dir = ROOT / 'tests' / 'artifacts'
        artifact_dir.mkdir(exist_ok=True)
        (artifact_dir / f'description-{label}.png').write_bytes(base64.b64decode(result['data']))
    for variant in ['missing', 'empty', 'whitespace']:
        data_without_description = dict(description_data)
        if variant == 'missing': del data_without_description['description']
        else: data_without_description['description'] = '' if variant == 'empty' else '  \n\t  '
        fixture_json.write_text(json.dumps(data_without_description,ensure_ascii=False),encoding='utf-8')
        rebuild()
        navigate('product.html?product=zz-test-product')
        loaded()
        assert js("document.querySelector('.plant-description')===null && document.querySelector('.product-description')===null"), variant
finally:
    fixture_json.write_text(original_json,encoding='utf-8')
    rebuild()
    call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
print('PASS: long multiline description JSON/generated JS/file://, single block below summary, literal HTML, wrapping at 320-1440 px, missing/empty/whitespace hidden; description fixture restored.')
