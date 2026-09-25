"""Контракты макросов проверяются по DOM, а не по отступам HTML."""

from html.parser import HTMLParser

import pytest
from flask import flash


class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.text = ''

    def find(self, tag=None, **attrs):
        result = []
        for child in self.children:
            if (tag is None or child.tag == tag) and all(
                key in child.attrs if value is True else child.attrs.get(key) == value
                for key, value in attrs.items()
            ):
                result.append(child)
            result.extend(child.find(tag, **attrs))
        return result

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()

    def ancestor(self, tag):
        node = self.parent
        while node and node.tag != tag:
            node = node.parent
        return node


class DOM(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node()
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self.VOID:
            self.current = node

    def handle_endtag(self, tag):
        node = self.current
        while node.parent:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, text):
        node = self.current
        while node:
            node.text += text
            node = node.parent


def tree(html):
    return DOM(html).root


def macro(render, expression, **context):
    return render('{% import "venom_ui/macros.html" as ui %}{{ ' + expression + ' }}', **context)


@pytest.mark.parametrize('page', ['settings', 'components', 'sidebar', 'login'])
def test_demos_render(client, page):
    response = client.get(f'/demo/{page}')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<html lang="ru">' in html
    assert 'googleapis' not in html
    assert html.index('/_ui/tokens.css') < html.index('/_ui/ui.css') < html.index('/_ui/list.css')
    dom = tree(html)
    for script in dom.find('script'):
        if '/_ui/' in script.attrs.get('src', ''):
            assert 'defer' in script.attrs


@pytest.mark.parametrize('page,active', [('settings', 'Настройки'), ('components', 'Бренды'), ('sidebar', 'Бренды')])
def test_topbar_active_and_logout(client, page, active):
    dom = tree(client.get(f'/demo/{page}').get_data(as_text=True))
    nav = dom.find('nav', **{'aria-label': 'Основная навигация'})[0]
    current = nav.find('a', **{'aria-current': 'page'})
    assert len(current) == 1 and current[0].text == active
    form = dom.find('form', action='/logout')[0]
    assert form.attrs['method'] == 'post'
    assert form.find('input', name='csrf_token')[0].attrs['value'] == 'demo-token'


def test_sidebar_is_optional(client):
    for page, expected in [('settings', 0), ('components', 0), ('sidebar', 1)]:
        dom = tree(client.get(f'/demo/{page}').get_data(as_text=True))
        assert len(dom.find('button', **{'data-sidebar-toggle': True})) == expected
        assert len(dom.find('aside', id='sidebar')) == expected
        assert len([node for node in dom.find('div') if node.has_class('sidebar-backdrop')]) == expected
        assert len(dom.find('dialog', **{'data-confirm-dialog': True})) == 1
    empty = tree(client.get('/demo/sidebar').get_data(as_text=True))
    assert len(empty.find('aside')[0].find('a')) == 30


def test_settings_have_independent_forms(client):
    dom = tree(client.get('/demo/settings').get_data(as_text=True))
    sections = [node for node in dom.find('section') if node.has_class('settings-section')]
    assert len(sections) == 4
    for section in sections:
        forms = section.find('form')
        assert len(forms) == 1
        form = forms[0]
        assert not form.find('form')
        assert form.find('input', name='section')[0].attrs['value'] == section.attrs['id'].removeprefix('settings-')
        assert form.find('input', name='csrf_token')
    test = dom.find('button', formaction='/settings/test-email')[0]
    assert test.ancestor('form').find('input', name='section')[0].attrs['value'] == 'email'
    for name in ('telegram_token', 'brand_api_key'):
        assert dom.find('input', name=name)[0].attrs['type'] == 'text'
    assert 'data-toggle-password' not in client.get('/demo/settings').get_data(as_text=True)


def test_secret_is_write_only(render):
    html = macro(render, "ui.secret_field('smtp', 'Пароль', stored, clearable=true)", stored='NEVER_RENDER_THIS_PASSWORD')
    dom = tree(html)
    field = dom.find('input', name='smtp')[0]
    assert field.attrs['type'] == 'password' and field.attrs['value'] == ''
    assert 'NEVER_RENDER_THIS_PASSWORD' not in html
    assert 'сохранён' in field.attrs['placeholder']
    assert dom.find('input', name='smtp__clear')[0].attrs['type'] == 'checkbox'


def test_api_key_complete_and_escaped(render):
    key = 'a' * 150 + '<script>&secret'
    dom = tree(macro(render, "ui.api_key_block(key)", key=key))
    assert dom.find('pre', id='api-key')[0].text == key
    assert not dom.find('script')
    assert dom.find('button', **{'data-copy-target': 'api-key'})
    assert not macro(render, "ui.api_key_block('')").strip()


@pytest.mark.parametrize('category,expected', [('success', 'success'), ('info', 'info'), ('warning', 'warning'), ('error', 'error'), ('danger', 'error'), ('message', 'info'), ('other', 'info')])
def test_flash_categories(app, category, expected):
    with app.test_request_context('/'):
        flash('<unsafe>', category)
        html = str(app.jinja_env.get_template('venom_ui/macros.html').module.flash_stack())
    banners = tree(html).find('div', **{'data-banner': True})
    assert len(banners) == 1 and banners[0].has_class(f'banner--{expected}')
    assert '&lt;unsafe&gt;' in html


@pytest.mark.parametrize('page', ['settings', 'components', 'sidebar', 'login'])
def test_accessibility_basics(client, page):
    dom = tree(client.get(f'/demo/{page}').get_data(as_text=True))
    ids = [node.attrs['id'] for node in dom.find() if 'id' in node.attrs]
    assert len(ids) == len(set(ids))
    for button in dom.find('button'):
        if not button.text.strip():
            assert button.attrs.get('aria-label'), button.attrs
    for node in dom.find():
        for attribute in ('aria-labelledby', 'aria-describedby'):
            if attribute in node.attrs:
                assert all(id_ in ids for id_ in node.attrs[attribute].split())
    for dialog in dom.find('dialog'):
        assert dialog.attrs.get('aria-labelledby')
    if page != 'login':
        assert dom.find('a', href='#main')
        assert dom.find('main', id='main')[0].attrs['tabindex'] == '-1'
    for label in dom.find('label'):
        if 'for' in label.attrs:
            assert label.attrs['for'] in ids


def test_file_picker_and_field_errors(render):
    dom = tree(macro(render, "ui.file_picker('files', 'pick', 'Документы', multiple=true, required=true, accept='.csv')"))
    file = dom.find('input')[0]
    assert all(key in file.attrs for key in ('multiple', 'required', 'aria-labelledby', 'aria-describedby'))
    assert file.attrs['accept'] == '.csv'
    assert dom.find('span', id='pick-status')[0].attrs['aria-live'] == 'polite'
    dom = tree(macro(render, "ui.field('email', 'Email', hint='Подсказка', error='Ошибка', attrs={'id': 'custom'})"))
    field = dom.find('input')[0]
    assert field.attrs['aria-describedby'] == 'custom-hint custom-error'
    assert field.attrs['aria-invalid'] == 'true'


def test_auth_logo_has_context_class(render):
    dom = tree(macro(render, "ui.logo('auth')"))
    logo = dom.find('img')[0]
    assert logo.has_class('brand-logo')
    assert logo.has_class('brand-logo--auth')


def test_auth_done_step_uses_svg(render):
    dom = tree(macro(render, "ui.auth_steps(2, 2, ['Вход', 'Подтверждение'])"))
    assert dom.find('li')[0].find('svg')
    assert dom.find('li')[1].attrs['aria-current'] == 'step'


def test_nullable_macro_values(render):
    dom = tree(macro(render, "ui.field('a', 'A', value=none, placeholder=none)"))
    assert dom.find('input')[0].attrs['value'] == ''
    assert dom.find('input')[0].attrs['placeholder'] == ''
    assert tree(macro(render, "ui.textarea('t', 'T', value=none)")).find('textarea')[0].text == ''
    dom = tree(macro(render, "ui.secret_field('p', 'P', false, placeholder_hint=none, clearable=true)"))
    assert dom.find('input')[0].attrs['placeholder'] == ''
    assert len(dom.find('input')) == 1
    assert not dom.find('span', **{'class': 'field__hint'})
    assert len(tree(macro(render, "ui.auth_steps(1, 2, none)")).find('li')) == 2


def test_secret_hint_and_clear_share_field(render):
    for stored in (True, False):
        html = macro(render, "ui.secret_field('p', 'P', stored, placeholder_hint='custom hint', clearable=true)", stored=stored)
        assert html.count('custom hint') == 1
        dom = tree(html)
        fields = dom.find('div', **{'class': 'field'})
        assert len(fields) == 1
        assert len(fields[0].find('input', name='p__clear')) == int(stored)
        assert len(fields[0].find('span', **{'class': 'field__hint'})) == int(stored)


def test_settings_section_id_does_not_collide(render):
    dom = tree(render('{% import "venom_ui/macros.html" as ui %}{% call ui.settings_section("email", "Email", false) %}{{ ui.field("email", "Email") }}{% endcall %}'))
    assert len(dom.find(id='email')) == 1
    assert dom.find('section', id='settings-email')


def test_js_class_precedes_stylesheets(client):
    html = client.get('/demo/settings').get_data(as_text=True)
    script = "<script>document.documentElement.classList.add('js')</script>"
    assert html.index('<head>') < html.index(script) < html.index('/_ui/tokens.css') < html.index('</head>')
