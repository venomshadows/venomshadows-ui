(function () {
  'use strict';
  const all = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const normalize = value => String(value || '').toLocaleLowerCase('ru').replace(/ё/g, 'е');
  const linked = (selector, target) => all(selector).filter(node => node.dataset.target === target);
  const checkbox = row => row.querySelector('[data-row-select]');
  const initialized = new WeakSet();

  // Старые tbody поддерживаются, новые контейнеры явно отмечают тело списка.
  const bodies = target => target.matches('[data-list-body]') ? [target] : all('[data-list-body], tbody', target);
  const rowsOf = target => bodies(target).flatMap(body => Array.from(body.children).filter(row => row.matches('[data-row]')));
  const sortGroup = target => linked('[data-sort-control]', target.id)[0]
    || (target.previousElementSibling?.matches('[data-sort-control]:not([data-target])') ? target.previousElementSibling : null);
  const focusTarget = target => target.closest('.table-scroll') || target;
  const detailOpen = new WeakMap();
  const detailsOf = row => {
    const details = [];
    for (let next = row.nextElementSibling; next?.matches('[data-row-detail]'); next = next.nextElementSibling) details.push(next);
    return details;
  };
  const detailTargets = (button, details) => {
    const controls = button.getAttribute('aria-controls');
    const ids = controls === null ? null : controls.trim().split(/\s+/).filter(Boolean);
    return ids === null ? details : details.filter(detail => detail.id && ids.includes(detail.id));
  };
  function syncDetails(row, details) {
    details.forEach(detail => { detail.hidden = row.hidden || !detailOpen.get(detail); });
    all('[data-detail-toggle]', row).forEach(button => {
      const targets = detailTargets(button, details);
      if (targets.length) button.setAttribute('aria-expanded', String(targets.every(detail => detailOpen.get(detail))));
    });
  }
  // Делегирование работает и для серверной страницы, и для добавленных строк.
  function initDetails(table) {
    const remember = row => {
      const details = detailsOf(row);
      details.forEach(detail => {
        if (!detailOpen.has(detail)) detailOpen.set(detail, !detail.hidden);
      });
      return details;
    };
    const sync = () => rowsOf(table).forEach(row => syncDetails(row, remember(row)));
    table.addEventListener('click', event => {
      const button = event.target.closest('[data-detail-toggle]');
      const row = button?.closest('[data-row]');
      if (!row || row.closest('[data-list]') !== table) return;
      const details = remember(row);
      const targets = detailTargets(button, details);
      if (!targets.length) return;
      const open = !targets.every(detail => detailOpen.get(detail));
      targets.forEach(detail => detailOpen.set(detail, open));
      syncDetails(row, details);
    });
    table.addEventListener('venomlist:refresh', sync);
    sync();
  }
  // Удаляем всю группу до refresh, иначе подробности перейдут к соседу.
  function removeRows(rows) {
    const tables = new Set();
    Array.from(rows).forEach(row => {
      if (!row.matches('[data-row]')) return;
      const table = row.closest('[data-list]');
      if (table) tables.add(table);
      detailsOf(row).forEach(detail => detail.remove());
      row.remove();
    });
    tables.forEach(table => table.dispatchEvent(new Event('venomlist:refresh')));
  }
  function collectDetails(state) {
    state.details = new Map(state.rows.map(row => [row, detailsOf(row)]));
    state.details.forEach(details => details.forEach(detail => {
      if (!detailOpen.has(detail)) detailOpen.set(detail, !detail.hidden);
    }));
  }
  function showDetails(state, row) {
    syncDetails(row, state.details.get(row) || []);
  }

  function controls(form) {
    return form ? all('[data-list-search], [data-list-filter], [data-chip-value]', form) : [];
  }

  function syncChips(form) {
    if (!form) return;
    all('[data-chip-group]', form).forEach(group => {
      const value = group.querySelector('[data-chip-value]').value;
      all('[data-chip]', group).forEach(chip => chip.setAttribute('aria-pressed', String(chip.dataset.chip === value)));
    });
    const reset = form.querySelector('[data-list-reset]');
    if (reset?.matches('button')) reset.disabled = !controls(form).some(control => control.value !== '');
  }

  function bindFilters(form, changed) {
    if (!form) return;
    form.addEventListener('click', event => {
      const chip = event.target.closest('[data-chip]');
      if (!chip) return;
      const input = chip.closest('[data-chip-group]').querySelector('[data-chip-value]');
      input.value = input.value === chip.dataset.chip ? '' : chip.dataset.chip;
      syncChips(form);
      changed(false);
    });
    form.addEventListener('input', event => {
      if (event.target.matches('[data-list-search]')) { syncChips(form); changed(true); }
    });
    form.addEventListener('change', event => {
      if (!event.target.matches('[data-list-search]')) { syncChips(form); changed(false); }
    });
    form.querySelector('button[data-list-reset]')?.addEventListener('click', () => {
      controls(form).forEach(control => { control.value = ''; });
      syncChips(form);
      changed(false);
    });
    syncChips(form);
  }

  function initServer(form) {
    let timer;
    const submit = () => form.requestSubmit();
    bindFilters(form, delayed => {
      clearTimeout(timer);
      if (delayed) timer = setTimeout(submit, 400);
      else submit();
    });
    const disabled = new Set();
    form.addEventListener('submit', () => {
      clearTimeout(timer);
      Array.from(form.elements).forEach(control => {
        if (control.name && !control.disabled && control.value === '') {
          disabled.add(control);
          control.disabled = true;
        }
      });
    });
    // Возврат из bfcache должен снова разрешать ввод в пустые поля.
    window.addEventListener('pageshow', () => {
      disabled.forEach(control => { control.disabled = false; });
      disabled.clear();
    });
  }

  function restore(state) {
    let saved = {};
    try { saved = JSON.parse(sessionStorage.getItem('venomlist:' + location.pathname + '#' + state.table.id) || '{}') || {}; } catch (_) { /* Хранилище может быть запрещено. */ }
    const params = new URLSearchParams(location.search);
    const names = state.fields.map(field => field.name).concat(['sort', 'dir']);
    // Явная ссылка описывает весь список: старые фильтры сессии не подмешиваются.
    const fromURL = names.some(name => params.has(name));
    const read = name => fromURL ? params.get(name) : saved[name];
    state.fields.forEach(field => {
      const value = read(field.name);
      if (typeof value !== 'string') {
        if (fromURL) field.value = '';
        return;
      }
      let valid = true;
      if (field.matches('select')) valid = Array.from(field.options).some(option => option.value === value);
      if (field.matches('[data-chip-value]')) valid = all('[data-chip]', field.parentElement).some(chip => chip.dataset.chip === value) || value === '';
      field.value = valid ? value : '';
    });
    const key = read('sort');
    if (state.headers.some(header => header.dataset.sortKey === key)) state.sort = key;
    const dir = read('dir');
    if (dir === 'asc' || dir === 'desc') state.direction = dir;
    syncChips(state.form);
  }

  function persist(state) {
    const values = Object.fromEntries(state.fields.map(field => [field.name, field.value]));
    values.sort = state.sort;
    values.dir = state.sort ? state.direction : '';
    const url = new URL(location.href);
    Object.entries(values).forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    });
    try { history.replaceState(history.state, '', url); } catch (_) { /* Например, sandbox без доступа к адресу. */ }
    try { sessionStorage.setItem('venomlist:' + location.pathname + '#' + state.table.id, JSON.stringify(values)); } catch (_) { /* Приватный режим не мешает фильтрации. */ }
  }

  function matches(state, row, except) {
    return state.fields.every(field => {
      if (field.name === except || !field.value) return true;
      if (field.matches('[data-list-search]')) {
        const haystack = normalize(row.dataset.search);
        return normalize(field.value).split(/\s+/).filter(Boolean).every(word => haystack.includes(word));
      }
      return row.getAttribute('data-filter-' + field.name) === field.value;
    });
  }

  function updateCounts(state) {
    if (!state.form) return;
    const count = state.form.querySelector('[data-list-count]');
    if (count) count.textContent = state.matching.length + ' из ' + state.rows.length;
    all('[data-chip-group]', state.form).forEach(group => {
      const scope = state.rows.filter(row => matches(state, row, group.dataset.chipGroup));
      all('[data-chip]', group).forEach(chip => {
        const count = chip.querySelector('[data-chip-count]');
        if (count) count.textContent = scope.filter(row => !chip.dataset.chip || row.getAttribute('data-filter-' + group.dataset.chipGroup) === chip.dataset.chip).length;
      });
    });
    syncChips(state.form);
  }

  function updateSelection(state) {
    state.rows = rowsOf(state.table);
    const visible = state.rows.filter(row => !row.hidden && checkbox(row) && !checkbox(row).disabled);
    const selected = state.rows.filter(row => checkbox(row)?.checked);
    state.rows.forEach(row => row.classList.toggle('is-selected', Boolean(checkbox(row)?.checked)));
    if (state.selectAll) {
      const checked = visible.filter(row => checkbox(row).checked).length;
      state.selectAll.checked = visible.length > 0 && checked === visible.length;
      state.selectAll.indeterminate = checked > 0 && checked < visible.length;
      state.selectAll.disabled = visible.length === 0;
    }
    state.bars.forEach(bar => {
      if (!selected.length && bar.contains(document.activeElement)) {
        (state.selectAll && !state.selectAll.disabled ? state.selectAll : focusTarget(state.table))?.focus();
      }
      bar.hidden = selected.length === 0;
      const count = bar.querySelector('[data-selection-count]');
      if (count) count.textContent = selected.length;
    });
    const ids = selected.map(row => row.dataset.id || checkbox(row).value);
    const serialized = JSON.stringify([...new Set(ids)].sort());
    if (serialized !== state.lastSelection) {
      state.lastSelection = serialized;
      state.table.dispatchEvent(new CustomEvent('venomlist:selection', { bubbles: true, detail: { ids } }));
    }
  }

  function reveal(state) {
    const matching = new Set(state.matching);
    const visible = new Set(state.matching.slice(0, state.limit));
    const firstRevealed = state.matching.find(row => row.hidden && visible.has(row));
    state.rows.forEach(row => {
      row.hidden = !visible.has(row);
      showDetails(state, row);
      if (!row.hidden) row.removeAttribute('data-lazy-pending');
      // Выбор снимается только фильтром, а не границей ленивого показа.
      if (!matching.has(row) && checkbox(row)) checkbox(row).checked = false;
    });
    state.sentinels.forEach(sentinel => {
      const hidden = state.matching.length <= state.limit;
      if (hidden && sentinel.contains(document.activeElement)) {
        const box = firstRevealed && checkbox(firstRevealed);
        (box && !box.disabled ? box : focusTarget(state.table))?.focus();
      }
      sentinel.hidden = hidden;
    });
    all('[data-empty-row]', state.table).forEach(row => { row.hidden = state.matching.length !== 0; });
    if (state.selection) updateSelection(state.selection);
    scheduleReveal(state);
  }

  function compareValues(a, b, type, direction) {
    if (type === 'number' || type === 'date') {
      const convert = value => value.trim() === '' ? NaN : (type === 'number' ? Number(value) : Date.parse(value));
      const av = convert(a), bv = convert(b);
      if (!Number.isFinite(av)) return Number.isFinite(bv) ? 1 : 0;
      if (!Number.isFinite(bv)) return -1;
      return (av - bv) * (direction === 'desc' ? -1 : 1);
    }
    return a.localeCompare(b, 'ru', { numeric: true }) * (direction === 'desc' ? -1 : 1);
  }

  function applySort(state) {
    const active = state.headers.find(header => header.dataset.sortKey === state.sort);
    if (active) state.rows.sort((a, b) => {
      const comparison = compareValues(a.getAttribute('data-sort-' + state.sort) || '', b.getAttribute('data-sort-' + state.sort) || '', active.dataset.sortType, state.direction);
      return comparison || state.originalOrder.get(a) - state.originalOrder.get(b);
    });
    state.rows.forEach(row => {
      const body = row.parentElement;
      body.appendChild(row);
      (state.details.get(row) || []).forEach(detail => body.appendChild(detail));
    });
    all('[data-empty-row]', state.table).forEach(row => row.parentElement.appendChild(row));
    state.headers.forEach(header => {
      const dir = header === active ? state.direction : 'none';
      const th = header.closest('th');
      if (th) th.setAttribute('aria-sort', dir === 'none' ? 'none' : (dir === 'asc' ? 'ascending' : 'descending'));
      else {
        header.setAttribute('aria-pressed', String(header === active));
        const direction = header.querySelector('[data-sort-direction]');
        if (direction) direction.textContent = dir === 'none' ? '' : (dir === 'asc' ? ', по возрастанию' : ', по убыванию');
      }
      all('[data-sort-icon]', header).forEach(icon => { icon.hidden = icon.dataset.sortIcon !== dir; });
    });
  }

  function refresh(state, save = true, resetLimit = true) {
    if (resetLimit) state.limit = state.lazy ? 50 : Infinity;
    state.matching = state.rows.filter(row => matches(state, row));
    updateCounts(state);
    reveal(state);
    if (save) persist(state);
  }

  // После refresh новые строки получают те же подписи, что и исходные.
  function fillLabels(table) {
    // Явные роли сохраняют семантику таблицы при карточной flex-разметке.
    if (table.classList.contains('data-table--stacked')) {
      table.setAttribute('role', 'table');
      Object.entries({ 'thead, tbody': 'rowgroup', tr: 'row', th: 'columnheader', td: 'cell' })
        .forEach(([selector, role]) => all(selector, table).forEach(node => node.setAttribute('role', role)));
    }
    const labels = all('thead th', table).map(th => th.textContent.trim());
    all('tbody > [data-row]:not(.data-table__empty)', table).forEach(row => Array.from(row.cells).forEach((cell, index) => {
      if (!cell.hasAttribute('data-label')) cell.dataset.label = labels[index] || '';
    }));
  }

  function initSelection(table) {
    const group = sortGroup(table);
    if (!table.querySelector('[data-row-select]') && !table.querySelector('[data-select-all]') && !group?.querySelector('[data-select-all]')) return null;
    const state = {
      table, rows: [], bars: linked('[data-bulk-bar]', table.id),
      selectAll: table.querySelector('[data-select-all]') || group?.querySelector('[data-select-all]'), lastSelection: ''
    };
    const changed = event => {
      if (!event.target.matches('[data-select-all], [data-row-select]')) return;
      if (event.target === state.selectAll) {
        state.rows.filter(row => !row.hidden && checkbox(row) && !checkbox(row).disabled)
          .forEach(row => { checkbox(row).checked = state.selectAll.checked; });
      }
      updateSelection(state);
    };
    table.addEventListener('change', changed);
    group?.addEventListener('change', changed);
    state.bars.forEach(bar => bar.querySelector('[data-clear-selection]')?.addEventListener('click', () => {
      state.rows.forEach(row => { if (checkbox(row)) checkbox(row).checked = false; });
      updateSelection(state);
    }));
    table.addEventListener('venomlist:refresh', () => updateSelection(state));
    updateSelection(state);
    return state;
  }

  // Проверяем геометрию после пакета: observer не сообщает о неизменном пересечении.
  function scheduleReveal(state) {
    if (!state.lazy || state.revealFrame) return;
    state.revealFrame = requestAnimationFrame(() => {
      state.revealFrame = null;
      if (!state.table.isConnected || state.matching.length <= state.limit) return;
      const bounds = state.lazyRoot?.getBoundingClientRect() || { top: 0, bottom: innerHeight };
      const nearby = state.sentinels.some(sentinel => {
        const rect = sentinel.getBoundingClientRect();
        return !sentinel.hidden && rect.bottom >= bounds.top - 200 && rect.top <= bounds.bottom + 200;
      });
      if (nearby) revealMore(state);
    });
  }

  function revealMore(state) {
    state.limit += 50;
    reveal(state);
  }

  function initLazy(state) {
    // В фиксированной области подгрузка следует её прокрутке, а не прокрутке страницы.
    state.lazyRoot = state.table.closest('.table-scroll--fixed');
    if (state.lazyRoot) state.sentinels.forEach(sentinel => state.lazyRoot.appendChild(sentinel));
    state.sentinels.forEach(sentinel => sentinel.querySelector('[data-reveal-more]')
      ?.addEventListener('click', () => revealMore(state)));
    if (!state.lazy) return;
    const observer = new IntersectionObserver(entries => {
      if (!state.table.isConnected) { observer.disconnect(); return; }
      if (entries.some(entry => entry.isIntersecting && !entry.target.hidden)) revealMore(state);
    }, { root: state.lazyRoot, rootMargin: '200px' });
    state.sentinels.forEach(sentinel => observer.observe(sentinel));
  }

  function bindClient(state) {
    state.table.addEventListener('venomlist:refresh', () => {
      state.rows = rowsOf(state.table);
      collectDetails(state);
      fillLabels(state.table);
      state.rows.forEach(row => {
        if (!state.originalOrder.has(row)) state.originalOrder.set(row, state.nextOrder++);
      });
      applySort(state);
      refresh(state, true, false);
    });
    bindFilters(state.form, () => refresh(state));
    state.form?.addEventListener('submit', event => event.preventDefault());
    state.headers.forEach(header => header.addEventListener('click', () => {
      state.direction = state.sort === header.dataset.sortKey && state.direction === 'asc' ? 'desc' : 'asc';
      state.sort = header.dataset.sortKey;
      applySort(state);
      refresh(state, true, false);
    }));
  }

  function initClient(table, form, selection) {
    const rows = rowsOf(table);
    const sentinels = linked('[data-lazy-sentinel]', table.id);
    const group = sortGroup(table);
    const state = {
      table, form, rows, sentinels, selection, fields: controls(form),
      headers: all('[data-sort-key]', table).concat(group ? all('[data-sort-key]', group) : []), originalOrder: new WeakMap(rows.map((row, index) => [row, index])), nextOrder: rows.length,
      lazy: sentinels.length > 0 && 'IntersectionObserver' in window,
      sort: table.dataset.sort || group?.dataset.sort || '', direction: (table.dataset.dir || group?.dataset.dir) === 'desc' ? 'desc' : 'asc',
      matching: [], limit: Infinity, revealFrame: null
    };
    collectDetails(state);
    restore(state);
    applySort(state);
    bindClient(state);
    initLazy(state);
    refresh(state, false);
  }

  function init(root = document) {
    const forms = all('[data-filter-bar]', root);
    if (root.matches?.('[data-filter-bar]')) forms.unshift(root);
    forms.forEach(form => {
      if (form.dataset.mode !== 'server' || initialized.has(form)) return;
      initialized.add(form);
      initServer(form);
    });
    const tables = all('[data-list]', root);
    if (root.matches?.('[data-list]')) tables.unshift(root);
    tables.forEach(table => {
      if (initialized.has(table)) return;
      initialized.add(table);
      fillLabels(table);
      initDetails(table);
      const selection = initSelection(table);
      if (table.dataset.mode === 'server') {
        table.addEventListener('venomlist:refresh', () => fillLabels(table));
        return;
      }
      const form = linked('[data-filter-bar]', table.id).find(item => item.dataset.mode !== 'server');
      initClient(table, form, selection);
    });
  }
  window.VenomList = { init, removeRows };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => init());
  else init();
}());
