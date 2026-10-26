"""Verify a real browser popup during the click, without navigating to Telegram."""
original_site_url = js('window.SHOP_CONFIG.SITE_URL')
try:
    for width, site_url in [(1440, original_site_url), (375, ''), (320, original_site_url)]:
        call('Emulation.setDeviceMetricsOverride', {'width':width,'height':900,'deviceScaleFactor':1,'mobile':width<760})
        js(f'window.SHOP_CONFIG.SITE_URL={json.dumps(site_url)};renderCart()')
        js("""window.actualOrderReader=currentOrder;
        currentOrder=()=>new Promise(resolve=>{window.finishTelegramRead=()=>resolve(buildOrder())});
        window.open=(...args)=>{window.realTelegramWindow=window.nativeTelegramOpen(...args);return window.realTelegramWindow};""")
        before = len([t for t in call('Target.getTargets')['targetInfos'] if t['type']=='page'])
        click('#sendTelegram')
        assert js('!!window.realTelegramWindow && !window.realTelegramWindow.closed'), (width, site_url)
        assert js('window.realTelegramWindow.opener===null')
        assert js("typeof window.finishTelegramRead==='function'")
        after = len([t for t in call('Target.getTargets')['targetInfos'] if t['type']=='page'])
        assert after == before+1, 'Native popup did not open during the click'
        # Close the reserved blank window BEFORE releasing the async order read.
        # The handler must offer its manual link, never contact Telegram in this test.
        js('window.realTelegramWindow.close()')
        wait_for('window.realTelegramWindow.closed')
        js('window.finishTelegramRead();currentOrder=window.actualOrderReader')
        wait_for("!document.querySelector('#telegramFallback').hidden")
        draft_url = js("document.querySelector('#telegramFallback').href")
        assert urlparse(draft_url).path == '/Uliamel'
        draft = parse_qs(urlparse(draft_url).query)['text'][0]
        assert draft == js('buildOrder().message')
        assert ('Ссылка:' in draft) == bool(site_url)
        assert js("document.querySelector('#basketCount').textContent") == '6'
finally:
    js(f'window.SHOP_CONFIG.SITE_URL={json.dumps(original_site_url)};currentOrder=window.originalCurrentOrder;renderCart()')
print('PASS: real user-gesture browser popup opens before async order preparation at desktop/375/320 px, with and without SITE_URL; no Telegram requests.')
