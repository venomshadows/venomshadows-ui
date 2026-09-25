document.addEventListener('DOMContentLoaded', function () {
  document.querySelector('[data-demo-delete]').addEventListener('click', function () {
    document.querySelectorAll('#domains [data-row-select]:checked').forEach(function (box) { box.closest('tr').remove(); });
    document.getElementById('domains').dispatchEvent(new Event('venomlist:refresh'));
  });
});
