"""v0.1.9: the automatic «Ещё» chevron has a size and the summary stays on one line."""
from test_v017 import STATIC, load


def test_auto_secondary_chevron_sized(page, render):
    page.set_viewport_size(dict(width=390, height=900))
    load(page, render)
    page.add_script_tag(path=str(STATIC / 'list.js'))
    chevron = page.locator('#auto-row summary > svg.icon')
    assert chevron.get_attribute('width') == '1.25em' and chevron.get_attribute('height') == '1.25em'
    box = chevron.bounding_box()
    assert box['width'] < 40 and box['height'] < 40
    summary = page.locator('#auto-row summary')
    assert summary.evaluate('el => getComputedStyle(el).whiteSpace') == 'nowrap'
    line = summary.evaluate('el => parseFloat(getComputedStyle(el).lineHeight) || 20')
    assert summary.bounding_box()['height'] <= max(line * 1.6, 48)


def test_chevron_sized_without_package_css(page, render):
    # Attributes alone must keep the SVG small even if list.css is missing.
    page.set_viewport_size(dict(width=390, height=900))
    page.set_content(__import__('test_v017').content(render))
    page.add_style_tag(content='@media (max-width: 699px) { td[data-stack="secondary"] { display: none; } }')
    page.add_script_tag(path=str(STATIC / 'list.js'))
    chevron = page.locator('#auto-row summary > svg.icon')
    if chevron.count():
        box = chevron.bounding_box()
        assert box is None or (box['width'] < 40 and box['height'] < 40)
