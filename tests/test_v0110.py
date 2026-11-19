"""v0.1.10: items inside the automatic «Ещё» look like card rows."""
from test_v017 import STATIC, load


def test_auto_secondary_items_are_card_rows(page, render):
    page.set_viewport_size(dict(width=390, height=900))
    load(page, render)
    page.add_style_tag(path=str(STATIC / 'tokens.css'))
    page.add_script_tag(path=str(STATIC / 'list.js'))
    page.locator('#auto-row summary').click()
    item = page.locator('#auto-row .data-table__secondary-item').first
    style = item.evaluate('el => { const s = getComputedStyle(el); return [s.display, s.justifyContent, s.borderTopStyle]; }')
    assert style == ['flex', 'space-between', 'solid']
    label = item.locator('> .field__label')
    assert label.evaluate('el => getComputedStyle(el).textTransform') == 'none'
    assert label.bounding_box()['x'] < item.bounding_box()['x'] + item.bounding_box()['width'] / 2
