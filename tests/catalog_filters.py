"""Real-browser checks for category routes, stock defaults and combined filters."""
from urllib.parse import quote

source_products = [(folder.name, json.loads((folder / 'product.json').read_text(encoding='utf-8-sig')))
                   for folder in (ROOT / 'products').iterdir() if folder.is_dir() and (folder / 'product.json').exists()]
expected_available = sum('availability' not in data or data['availability'] is True for _, data in source_products)
categories = list(dict.fromkeys(data['category'] for _, data in source_products))

def set_search(text):
    js(f"document.querySelector('#search').value={json.dumps(text)};document.querySelector('#search').dispatchEvent(new Event('input'))")

def set_tag(text):
    js(f"document.querySelector('#tagFilter').value={json.dumps(text)};document.querySelector('#tagFilter').dispatchEvent(new Event('change'))")

navigate('index.html')
loaded()
assert js("document.querySelector('#inStockOnly').checked")
assert js("document.querySelectorAll('.product').length") == expected_available
for category in categories:
    click('[data-filter=' + json.dumps(category, ensure_ascii=False) + ']')
    expected = sum(data['category'] == category and ('availability' not in data or data['availability'] is True) for _, data in source_products)
    assert js("document.querySelectorAll('.product').length") == expected
    assert js("[...document.querySelectorAll('.product .species')].every(e=>e.textContent===new URLSearchParams(location.search).get('category'))")
    assert js("document.querySelector('#filters .active').getAttribute('aria-pressed')") == 'true'
    wait_for("Math.abs(document.querySelector('#catalog').getBoundingClientRect().top-20)<3")
    navigate('index.html?category=' + quote(category) + '#catalog')
    loaded()
    assert js("document.querySelector('#filters .active').dataset.filter") == category
    assert js("document.querySelectorAll('.product').length") == expected

navigate('index.html?category=' + quote('Ели') + '#catalog')
loaded()
set_tag('Новинка')
set_search('Глаука')
assert js("document.querySelectorAll('.product').length") == 1
assert js("document.querySelector('.product-link').textContent") == 'Ель голубая «Глаука»'
click('#inStockOnly')
assert not js("document.querySelector('#inStockOnly').checked")
assert js("document.querySelector('#filters .active').dataset.filter") == 'Ели'
assert js("document.querySelector('#search').value") == 'Глаука'
assert js("document.querySelector('#tagFilter').value") == 'Новинка'
click('[data-filter="Туи"]')
assert not js("document.querySelector('#inStockOnly').checked")
assert js("document.querySelectorAll('.product').length") == 0
assert js("document.querySelector('#noResults').textContent") == 'Растения не найдены'
assert not js("document.querySelector('#noResults').hidden")
js('history.back()')
wait_for("document.querySelector('#filters .active').dataset.filter==='Ели'")
assert not js("document.querySelector('#inStockOnly').checked")
assert js("document.querySelectorAll('.product').length") == 1
click('[data-filter="all"]')
assert js("document.querySelector('#filters .active').textContent") == 'Все категории'
assert js("document.querySelector('#search').value") == 'Глаука'
assert js("document.querySelector('#tagFilter').value") == 'Новинка'
click('#inStockOnly')
assert js("document.querySelectorAll('.product').length") == 1
set_tag('')
set_search('')
click('#inStockOnly')
assert js("document.querySelectorAll('.product').length") == len(source_products)
assert js("document.querySelector('#resultCount').textContent") == f'Найдено растений: {len(source_products)}'

# Same-page category links and generic navigation preserve the existing stock state.
before_tabs = len(targets())
first_category = js("document.querySelector('.product .category-link').textContent")
click('.product .category-link')
assert len(targets()) == before_tabs
assert js("document.querySelector('#filters .active').dataset.filter") == first_category
assert not js("document.querySelector('#inStockOnly').checked")
click('.nav a[href="index.html#catalog"]')
assert js("document.querySelector('#filters .active').dataset.filter") == first_category
assert not js("document.querySelector('#inStockOnly').checked")
navigate('index.html')
loaded()
assert js("document.querySelector('#inStockOnly').checked"), 'Fresh home page must reset stock to on'

# Category link on the product page must return to that category, not all plants.
navigate('product.html?product=el-golubaya')
loaded()
click('.product-summary .kicker')
wait_for("!!document.querySelector('#inStockOnly') && new URLSearchParams(location.search).get('category')==='Ели'")
loaded()
assert js("document.querySelector('#filters .active').dataset.filter") == 'Ели'
assert js("[...document.querySelectorAll('.species')].every(e=>e.textContent==='Ели')")

# Confirm strict true / legacy missing / explicit false / null semantics without changing JSON.
js("""for (const [suffix,availability] of [['yes',true],['no',false],['null',null],['legacy',undefined]]) {
  const item={...items.find(p=>p.slug==='el-golubaya'),slug:'stock-check-'+suffix,name:'Проверка наличия '+suffix,tags:['Новинка']};
  if(availability===undefined) delete item.availability; else item.availability=availability;
  items.push(item);
}""")
set_tag('Новинка')
set_search('Проверка наличия')
assert js("document.querySelectorAll('.product').length") == 2
click('#inStockOnly')
assert js("document.querySelectorAll('.product').length") == 4
assert js("document.querySelector('[data-add=stock-check-no]').disabled")
assert js("document.querySelector('[data-add=stock-check-no]').closest('.product').querySelector('.availability').textContent") == 'Нет в наличии'
click('#inStockOnly')
assert js("document.querySelectorAll('.product').length") == 2

navigate('index.html')
loaded()
unavailable = next((slug for slug, data in source_products if data.get('availability') is False), None)
if unavailable:
    click('#inStockOnly')
    selector = '[data-add=' + json.dumps(unavailable) + ']'
    assert js(f"document.querySelector({json.dumps(selector)}).disabled")
    js(f"window.denied=false;requestCartChange({json.dumps(unavailable)},1).then(()=>window.denied=true)")
    wait_for('window.denied')
    assert js("Object.keys(cart).length") == 0
    js(f"window.denied=false;cartRequest('change',{{slug:{json.dumps(unavailable)},delta:1}}).then(()=>window.denied=true)")
    wait_for('window.denied')
    assert js("Object.keys(cart).length") == 0
    assert js(f'document.querySelector({json.dumps(selector)}).textContent') == 'Нет в наличии'
    js(f"window.denied=false;requestCartToggle({json.dumps(unavailable)}).then(()=>window.denied=true)")
    wait_for('window.denied')
    assert js("Object.keys(cart).length") == 0
    js(f"window.denied=false;cartRequest('toggle',{{slug:{json.dumps(unavailable)}}}).then(()=>window.denied=true)")
    wait_for('window.denied')
    assert js("Object.keys(cart).length") == 0
    js("window.added=false;requestCartChange('tuya-smaragd',1).then(()=>window.added=true)")
    wait_for('window.added')
    click('#openCart')
    js("window.copied='';Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copied=text}}})")
    js(f"cart[{json.dumps(unavailable)}]=3;document.querySelector('#copyOrder').onclick()")
    wait_for('window.copied.length>0')
    unavailable_name = next(data['name'] for slug,data in source_products if slug == unavailable)
    assert unavailable_name not in js('window.copied')
    assert 'Смарагд' in js('window.copied')
    click('[data-delta="-1"]')
    wait_for("document.querySelector('#basketCount').textContent==='0'")
    click('#closeCart')
    navigate('product.html?product=' + unavailable)
    loaded()
    assert js("document.querySelector('.product-add').disabled")
    assert js("document.querySelector('.availability').textContent") == 'Нет в наличии'

navigate('index.html?category=unknown#catalog')
loaded()
assert js("document.querySelectorAll('.product').length") == 0
assert not js("document.querySelector('#noResults').hidden")
navigate('index.html')
loaded()
for width in [320,375,768,1024,1440]:
    call('Emulation.setDeviceMetricsOverride', {'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width<760})
    assert js('document.documentElement.scrollWidth<=innerWidth'), width
    click('#inStockOnly')
    assert js('document.documentElement.scrollWidth<=innerWidth'), width
call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
navigate('index.html')
loaded()
print('PASS: all category buttons/direct links/product links, scroll and active state, stock defaults/toggles, combined filters/history, strict availability semantics, blocked direct cart calls and order export, 320-1440 widths.')
