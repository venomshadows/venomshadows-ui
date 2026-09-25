document.addEventListener('DOMContentLoaded', function () {
  document.querySelector('[data-demo-delete]').addEventListener('click', function () {
    const rows = Array.from(document.querySelectorAll('#domains [data-row-select]:checked'))
      .map(box => box.closest('[data-row]'));
    VenomList.removeRows(rows);
  });
});
