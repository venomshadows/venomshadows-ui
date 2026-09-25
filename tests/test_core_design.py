"""Ограничения общей системы применяются и к будущим CSS списка."""

import fnmatch
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'src' / 'venomshadows_ui'
STATIC = PACKAGE / 'static'
TEMPLATES = PACKAGE / 'templates'


def css_sources():
    for path in STATIC.glob('*.css'):
        css = re.sub(r'/\*.*?\*/', '', path.read_text(encoding='utf-8'), flags=re.S)
        # Дескриптор font-face требует число: это не вес текста компонента.
        yield path.name, re.sub(r'@font-face\s*\{[^}]*\}', '', css, flags=re.S)


def css_rules(css):
    # Скобки внутри строк и комментариев не меняют глубину правил.
    stack = []
    start = 0
    for match in re.finditer(r'''/\*.*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[{};]''', css, re.S):
        token = match[0]
        if token == '{':
            selector = re.sub(r'/\*.*?\*/', '', css[start:match.start()], flags=re.S).strip()
            stack.append((selector, match.end()))
            start = match.end()
        elif token == '}':
            selector, body_start = stack.pop()
            yield selector, css[body_start:match.start()].strip()
            start = match.end()
        elif token == ';':
            start = match.end()


def test_css_rules_walks_nested_rules():
    css = '''
        .first { color: red; }
        @media (max-width: 480px) {
            .brand-logo { height: clamp(1rem, 2vw, 3rem); }
            @supports (display: grid) {
                .btn:disabled { opacity: .5; content: "}"; }
            }
        }
        .last { content: "{"; /* } */ color: blue; }
    '''
    rules = dict(css_rules(css))
    assert rules['.first'] == 'color: red;'
    assert rules['.brand-logo'] == 'height: clamp(1rem, 2vw, 3rem);'
    assert rules['.btn:disabled'] == 'opacity: .5; content: "}";'
    assert '@media (max-width: 480px)' in rules
    assert '@supports (display: grid)' in rules
    assert rules['.last'] == 'content: "{"; /* } */ color: blue;'


def test_font_scale_and_weights():
    for name, css in css_sources():
        for value in re.findall(r'(?<![-\w])font-size\s*:\s*([^;{}]+)', css):
            token = re.fullmatch(r'var\(--text-(caption|sm|base|heading|title)\)', value.strip())
            em = re.fullmatch(r'(\d*\.?\d+)em', value.strip())
            assert token or (em and 0 < float(em[1]) <= 1), (name, value)
        for value in re.findall(r'(?<![-\w])font-weight\s*:\s*([^;{}]+)', css):
            assert value.strip() in ('var(--weight-regular)', 'var(--weight-medium)'), (name, value)
        for value in re.findall(r'(?<![-\w])font\s*:\s*([^;{}]+)', css):
            assert value.strip() == 'inherit', f'{name}: shorthand bypasses scale'


def test_breakpoints_and_logo():
    widths = {860, 861, 699, 700, 640, 641, 480, 481, 360, 361}
    for name, css in css_sources():
        for selectors, body in css_rules(css):
            if selectors.startswith('@media'):
                for width in re.findall(r'(?:min|max)-width\s*:\s*([^\s)]+)', selectors):
                    assert width.endswith('px') and float(width[:-2]) in widths, (name, selectors)
            if 'logo' in selectors:
                assert 'clamp(' not in body, (name, selectors)
            if ':disabled' in selectors:
                assert not re.search(r'\bopacity\s*:', body), (name, selectors)


def test_tokens_resolve_and_fonts_are_local():
    tokens = (STATIC / 'tokens.css').read_text(encoding='utf-8')
    defined = set(re.findall(r'(--[\w-]+)\s*:', tokens))
    for path in PACKAGE.rglob('*'):
        if path.suffix not in ('.html', '.css', '.js'):
            continue
        text = path.read_text(encoding='utf-8')
        used = set(re.findall(r'var\((--(?:text|color)-[\w-]+)', text))
        assert not used - defined, (path.name, used - defined)
        assert 'fonts.googleapis.com' not in text
        assert 'fonts.gstatic.com' not in text


def test_no_text_glyph_icons():
    forbidden = re.compile('[×✓✔✕✖✎⇅▲▼▸⌖\U0001f000-\U0001faff\u2600-\u27bf]')
    for path in TEMPLATES.rglob('*.html'):
        source = re.sub(r'\{#.*?#\}', '', path.read_text(encoding='utf-8'), flags=re.S)
        assert not forbidden.search(source), path.name


def test_template_assets_exist_and_are_packaged(app):
    config = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    globs = config['tool']['setuptools']['package-data']['venomshadows_ui']
    referenced = set()
    for path in TEMPLATES.rglob('*.html'):
        source = path.read_text(encoding='utf-8')
        referenced.update(re.findall(r"venom_ui\.static\(['\"]([^'\"]+)['\"]\)", source))
        assert any(fnmatch.fnmatch(path.relative_to(PACKAGE).as_posix(), pattern) for pattern in globs)
    # Динамические имена поисковиков проверяются после рендера обоих вариантов.
    with app.test_request_context('/'):
        macros = app.jinja_env.get_template('venom_ui/macros.html').module
        for engine in ('yandex', 'google'):
            html = str(macros.engine_logo(engine))
            referenced.update(re.findall(r'/_ui/([^?"\s]+)', html))
    for filename in referenced:
        assert (STATIC / filename).is_file(), f'Missing package asset: {filename}'
        assert any(fnmatch.fnmatch(f'static/{filename}', pattern) for pattern in globs), filename
    for _, css in css_sources():
        for filename in re.findall(r'url\([\'"]?([^\)\'"\s]+)', css):
            assert (STATIC / filename).is_file(), filename
            assert any(fnmatch.fnmatch(f'static/{filename}', pattern) for pattern in globs)


def test_layout_contracts():
    css = (STATIC / 'ui.css').read_text(encoding='utf-8')
    assert 'scrollbar-gutter: stable' in css
    assert 'flex: 0 0 var(--sidebar-w)' in css
    assert 'repeat(auto-fill, minmax(18rem, 1fr))' in css
    for selector, body in css_rules(css):
        if selector in ('.panel', '.settings-section'):
            assert '--shadow-glow' not in body
    assert '@media (prefers-reduced-motion: reduce)' in css
    assert 'animation: none !important' in css
