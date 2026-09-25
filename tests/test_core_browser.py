"""Необязательные проверки настоящего браузера: VENOM_UI_BROWSER=chrome.

pip install playwright; python -m playwright install chromium
Без переменной обычный pytest не требует браузера.
"""

from urllib.parse import parse_qs

import pytest


def test_invalid_field_border(page, live_url):
    page.goto(live_url + '/demo/login')
    assert page.locator('input[aria-invalid="true"]').first.evaluate('''el => {
        const probe = document.createElement('span');
        probe.style.borderColor = 'var(--color-danger-border)';
        el.parentElement.append(probe);
        const matches = getComputedStyle(el).borderColor === getComputedStyle(probe).borderColor;
        probe.remove();
        return matches;
    }''')


@pytest.mark.parametrize('width', [1600, 860, 360])
@pytest.mark.parametrize('demo', ['settings', 'components', 'sidebar', 'login', 'list', 'list-server'])
def test_responsive_demos(page, live_url, width, demo, screenshot):
    page.set_viewport_size({'width': width, 'height': 1000})
    page.goto(f'{live_url}/demo/{demo}')
    page.evaluate('document.fonts.ready')
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert page.locator('h1').is_visible()
    if width == 1600 and demo == 'sidebar':
        assert page.locator('.sidebar').evaluate('(el) => el.getBoundingClientRect().width') == 320
    if demo in ('list', 'list-server'):
        assert page.locator('[data-list-search]').evaluate('''el => {
            const icon = el.parentElement.querySelector('svg').getBoundingClientRect();
            return el.getBoundingClientRect().left + parseFloat(getComputedStyle(el).paddingLeft) > icon.right;
        }''')
    screenshot(page, f'{demo}-{width}')


def test_topbar_narrow_tab_order_and_wide_layout(page, live_url):
    page.set_viewport_size({'width': 360, 'height': 800})
    page.goto(f'{live_url}/demo/settings')
    brand = page.locator('.topbar__brand')
    logout = page.locator('.topbar__logout-btn')
    tabs = page.locator('.topbar__tab')
    brand.focus()
    page.keyboard.press('Tab')
    assert logout.evaluate('(el) => el === document.activeElement')
    logout_box = logout.bounding_box()
    for tab in tabs.all():
        page.keyboard.press('Tab')
        assert tab.evaluate('(el) => el === document.activeElement')
        assert tab.bounding_box()['y'] >= logout_box['y'] + logout_box['height']

    page.set_viewport_size({'width': 1600, 'height': 1000})
    logout_box = logout.bounding_box()
    brand_box = brand.bounding_box()
    for tab in tabs.all():
        box = tab.bounding_box()
        assert box['x'] >= brand_box['x'] + brand_box['width']
        assert logout_box['x'] >= box['x'] + box['width']
        assert abs(logout_box['y'] - box['y']) < 1


def test_banner_disclosure_target_and_keyboard(page, live_url):
    page.set_viewport_size({'width': 360, 'height': 800})
    page.goto(f'{live_url}/demo/components')
    summaries = page.locator('.banner__details summary')
    assert summaries.count() > 0
    for summary in summaries.all():
        assert summary.bounding_box()['height'] >= 44
        assert summary.locator('svg').is_visible()
        summary.focus()
        page.keyboard.press('Enter')
        assert summary.evaluate('(el) => el.parentElement.open')
        page.keyboard.press('Enter')
        assert not summary.evaluate('(el) => el.parentElement.open')


def test_drawer_focus_escape_and_resize(page, live_url):
    page.set_viewport_size({'width': 360, 'height': 800})
    page.goto(f'{live_url}/demo/sidebar')
    toggle = page.locator('[data-sidebar-toggle]')
    toggle.click()
    assert toggle.get_attribute('aria-expanded') == 'true'
    assert page.locator('#main').evaluate('(el) => el.inert')
    assert page.locator('#sidebar').evaluate('(el) => el === document.activeElement')
    page.keyboard.press('Shift+Tab')
    assert page.locator('#sidebar a').last.evaluate('(el) => el === document.activeElement')
    page.keyboard.press('Tab')
    assert page.locator('button[data-sidebar-close]').evaluate('(el) => el === document.activeElement')
    page.keyboard.press('Escape')
    assert not page.locator('#main').evaluate('(el) => el.inert')
    assert toggle.evaluate('(el) => el === document.activeElement')
    toggle.click()
    page.set_viewport_size({'width': 1600, 'height': 1000})
    page.wait_for_function('!document.body.classList.contains("sidebar-open")')
    assert not page.locator('#main').evaluate('(el) => el.inert')


def test_confirmation_preserves_submitter_and_busy_reset(page, live_url):
    page.goto(f'{live_url}/demo/settings')
    page.route('**/_core_submit*', lambda route: route.fulfill(status=204))
    page.locator('#settings-site form').evaluate("""form => {
      form.action = '/_core_submit';
      form.querySelector('[value="revoke"]').setAttribute('formaction', '/_core_submit?revoke=1');
      const button = document.createElement('button');
      button.type = 'submit'; button.disabled = true; button.id = 'initial-disabled';
      form.append(button);
    }""")
    revoke = page.locator('[value="revoke"]')
    revoke.click()
    assert page.locator('[data-confirm-dialog]').evaluate('(el) => el.open')
    assert page.locator('[data-confirm-accept]').get_attribute('class') == 'btn btn--danger'
    page.locator('[data-confirm-cancel]').click()
    assert not revoke.is_disabled()
    revoke.click()
    with page.expect_request('**/_core_submit?revoke=1') as request:
        page.locator('[data-confirm-accept]').click()
    payload = parse_qs(request.value.post_data)
    assert payload['operation'] == ['revoke']
    assert payload['section'] == ['site']
    assert payload['csrf_token'] == ['demo-token']
    page.wait_for_function('document.querySelector("[value=revoke]").disabled')
    assert revoke.get_attribute('aria-busy') == 'true'
    assert page.locator('#settings-site form').evaluate('(el) => el === document.activeElement')
    page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}))")
    assert not revoke.is_disabled()
    assert revoke.get_attribute('aria-busy') is None
    assert page.locator('#initial-disabled').is_disabled()
    assert revoke.locator('svg').count() == 1


def test_confirm_button_without_form_and_escape(page, live_url):
    page.goto(f'{live_url}/demo/components')
    page.evaluate("""() => {
      const button = document.createElement('button');
      button.id = 'standalone'; button.type = 'button'; button.dataset.confirm = 'Выполнить?';
      button.textContent = 'Действие'; button.onclick = () => { window.actionCount = (window.actionCount || 0) + 1; };
      document.querySelector('main').prepend(button);
    }""")
    page.locator('#standalone').click()
    assert page.evaluate('window.actionCount || 0') == 0
    assert 'btn--danger' not in page.locator('[data-confirm-accept]').get_attribute('class')
    page.keyboard.press('Escape')
    assert page.evaluate('window.actionCount || 0') == 0
    page.locator('#standalone').click()
    page.locator('[data-confirm-accept]').click()
    assert page.evaluate('window.actionCount') == 1


def test_file_status_banner_and_clipboard_fallback(page, live_url):
    page.goto(f'{live_url}/demo/components')
    page.locator('#demo-files').set_input_files([
        {'name': 'a.csv', 'mimeType': 'text/csv', 'buffer': b'a'},
        {'name': 'b.csv', 'mimeType': 'text/csv', 'buffer': b'b'},
    ])
    assert page.locator('#demo-files-status').inner_text() == 'Выбрано: 2'
    page.locator('#demo-files').evaluate('(el) => el.form.reset()')
    page.wait_for_function('document.querySelector("#demo-files-status").textContent === "Файлы не выбраны"')
    count = page.locator('[data-banner]').count()
    page.locator('[data-banner-close]').first.click()
    assert page.locator('[data-banner]').count() == count - 1
    page.goto(f'{live_url}/demo/settings')
    page.evaluate("""() => {
      Object.defineProperty(navigator, 'clipboard', {value: undefined, configurable: true});
      document.execCommand = command => { window.copyCommand = command; return true; };
    }""")
    copy = page.locator('[data-copy-target]')
    copy.click()
    copy.click()
    assert copy.inner_text() == 'Скопировано'
    assert page.evaluate('window.copyCommand') == 'copy'
    page.wait_for_function('document.querySelector("[data-copy-target]").textContent.includes("Копировать")')
    assert copy.locator('svg').count() == 1
    page.evaluate('document.execCommand = () => false')
    copy.click()
    assert copy.inner_text() == 'Скопируйте выделенное'


@pytest.mark.parametrize('submit', ['click', 'enter', 'requestSubmit'])
def test_cancelled_submit_never_enters_busy_state(page, live_url, submit):
    page.goto(f'{live_url}/demo/settings')
    form = page.locator('#settings-email form')
    form.evaluate("form => form.addEventListener('submit', event => { event.preventDefault(); window.cancelled = true; })")
    if submit == 'click':
        form.locator('button[type=submit]').first.click()
    elif submit == 'enter':
        form.locator('input:not([type=hidden])').first.press('Enter')
    else:
        form.evaluate('(form) => form.requestSubmit()')
    page.wait_for_function('window.cancelled === true')
    assert form.get_attribute('aria-busy') is None
    assert form.locator('button:disabled').count() == 0


@pytest.mark.parametrize('clipboard_mode', ['unavailable', 'rejected'])
def test_modal_clipboard_fallback_copies_actual_field_value(page, live_url, clipboard_mode):
    page.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    page.goto(f'{live_url}/demo/components')
    page.evaluate("""async mode => {
      window.realClipboard = navigator.clipboard;
      await window.realClipboard.writeText('sentinel');
      Object.defineProperty(navigator, 'clipboard', {configurable: true,
        value: mode === 'unavailable' ? undefined : {
          writeText: async () => { throw new Error('Clipboard denied'); }
        }
      });
      const modal = document.querySelector('#demo-modal');
      modal.insertAdjacentHTML('beforeend', '<input id="modal-copy-field" value="correct modal value"><button type="button" id="modal-copy-trigger" data-copy-target="modal-copy-field">Copy</button>');
      modal.showModal();
    }""", clipboard_mode)
    copy = page.locator('#modal-copy-trigger')
    copy.click()
    page.wait_for_function("async () => await window.realClipboard.readText() === 'correct modal value'")
    assert page.evaluate('window.realClipboard.readText()') == 'correct modal value'
    assert page.locator('#demo-modal textarea.visually-hidden').count() == 0
    assert copy.evaluate('(el) => el === document.activeElement')


@pytest.mark.parametrize('fallback', [False, True])
def test_copy_field_values_and_other_element_text(page, live_url, fallback):
    page.goto(f'{live_url}/demo/components')
    page.evaluate("""fallback => {
      const host = document.createElement('div');
      host.innerHTML = '<li id="copy-li" value="7">list text</li><button id="copy-button" value="wrong">button text</button><select id="copy-select"><option value="selected">Label</option></select><input id="copy-input" value="input value"><textarea id="copy-area">area value</textarea><button id="copy-trigger" type="button">Copy</button>';
      document.querySelector('main').prepend(host);
      Object.defineProperty(navigator, 'clipboard', {configurable: true, value: fallback ? undefined : {writeText: async text => { window.copied = text; }}});
      document.execCommand = () => {
        window.copied = document.activeElement instanceof HTMLTextAreaElement ? document.activeElement.value : window.getSelection().toString();
        return true;
      };
    }""", fallback)
    for target, expected in [('li', 'list text'), ('button', 'button text'), ('select', 'selected'), ('input', 'input value'), ('area', 'area value')]:
        page.locator('#copy-trigger').evaluate('(el, target) => el.dataset.copyTarget = "copy-" + target', target)
        page.locator('#copy-trigger').click()
        page.wait_for_function('(expected) => window.copied === expected', arg=expected)
