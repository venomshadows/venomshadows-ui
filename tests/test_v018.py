"""Selection event lifecycle, exercised offline in a real browser."""
from pathlib import Path

import pytest


LIST_JS = Path(__file__).parents[1] / 'src/venomshadows_ui/static/list.js'


@pytest.mark.parametrize('mode', ['client', 'server'])
@pytest.mark.parametrize('restored', [False, True])
def test_selection_event_lifecycle(page, mode, restored):
    page.set_content(f'''
      <table id="items" data-list data-mode="{mode}"><tbody>
        <tr data-row data-id="42"><td><input type="checkbox" data-row-select value="1"></td></tr>
        <tr data-row><td><input type="checkbox" data-row-select value="2"></td></tr>
      </tbody></table>
    ''')
    # Restore the live checked property before initialization, without a checked
    # attribute or change event, as with browser-restored form state.
    page.evaluate('''restored => {
      document.querySelector('[data-row-select]').checked = restored;
      window.selections = [];
      document.addEventListener('venomlist:selection', event => {
        selections.push({ids: event.detail.ids, initial: event.detail.initial,
                         target: event.target.id});
      });
    }''', restored)
    page.add_script_tag(path=str(LIST_JS))
    expected = [dict(ids=['42'], initial=True, target='items')] if restored else []
    assert page.evaluate('selections') == expected

    def reinitialize():
        page.evaluate('''() => {
          VenomList.init();
          VenomList.init();
          document.querySelector('#items').dispatchEvent(new Event('venomlist:refresh'));
        }''')
        assert page.evaluate('selections') == expected

    reinitialize()
    boxes = page.locator('[data-row-select]')
    if not restored:
        boxes.nth(0).check()
        expected.append(dict(ids=['42'], initial=False, target='items'))
        assert page.evaluate('selections') == expected
    boxes.nth(1).check()
    expected.append(dict(ids=['42', '2'], initial=False, target='items'))
    assert page.evaluate('selections') == expected
    reinitialize()
    boxes.nth(0).uncheck()
    expected.append(dict(ids=['2'], initial=False, target='items'))
    assert page.evaluate('selections') == expected
    boxes.nth(1).uncheck()
    expected.append(dict(ids=[], initial=False, target='items'))
    assert page.evaluate('selections') == expected
    reinitialize()
