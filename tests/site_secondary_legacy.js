(() => {
  const table = document.getElementById('domain-table');
  if (!table) return;
  const media = matchMedia('(max-width: 699px)');
  const rows = [...table.querySelectorAll('tbody > tr[data-row]')].map(row => {
    const cells = [...row.querySelectorAll(':scope > td[data-stack="secondary"]:not([data-empty])')];
    if (!cells.length) return null;
    const extra = row.insertCell(); extra.className = 'data-table__secondary-cell'; extra.colSpan = row.cells.length - 1;
    const details = document.createElement('details'); details.className = 'data-table__secondary';
    const summary = document.createElement('summary'); summary.textContent = 'Ещё'; details.append(summary); extra.append(details);
    summary.setAttribute('aria-label', 'Ещё: ' + row.querySelector('.domain-name').textContent.trim());
    const entries = cells.map(cell => {
      const content = document.createElement('div'); content.className = `domain-secondary-item ${cell.className}`;
      if (cell.title) content.title = cell.title;
      const label = document.createElement('span'); label.className = 'field__label'; label.textContent = cell.dataset.label;
      content.append(label);
      return {cell, content};
    });
    return {details, entries};
  }).filter(Boolean);
  function update() {
    rows.forEach(({details, entries}) => entries.forEach(({cell, content}) => {
      if (media.matches) {
        if (!content.isConnected) { while (cell.firstChild) content.append(cell.firstChild); details.append(content); }
      } else if (content.isConnected) {
        while (content.childNodes.length > 1) cell.append(content.childNodes[1]);
        content.remove();
      }
    }));
  }
  media.addEventListener('change', update); update();
})();
