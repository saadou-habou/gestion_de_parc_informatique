/**
 * PARC INFORMATIQUE — comportements front (vanilla JS, sans dépendance).
 * - Recherche instantanée dans les tableaux (data-pi-table)
 * - Filtres par statut (data-pi-filter)
 * - Confirmation avant suppression
 * - Loader plein écran lors des soumissions de formulaire
 * - Ouverture/fermeture de la sidebar sur mobile
 */
document.addEventListener('DOMContentLoaded', function () {

  /* ---- Sidebar mobile ---- */
  var toggleBtn = document.querySelector('[data-pi-sidebar-toggle]');
  var sidebar = document.querySelector('.pi-sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('pi-open');
    });
  }

  /* ---- Recherche instantanée ---- */
  document.querySelectorAll('[data-pi-search-input]').forEach(function (input) {
    var targetSelector = input.getAttribute('data-pi-search-input');
    var table = document.querySelector(targetSelector);
    if (!table) return;
    input.addEventListener('input', function () {
      var term = input.value.trim().toLowerCase();
      table.querySelectorAll('tbody tr').forEach(function (row) {
        var text = row.innerText.toLowerCase();
        row.style.display = text.indexOf(term) !== -1 ? '' : 'none';
      });
      updateEmptyState(table);
    });
  });

  /* ---- Filtres par statut (boutons/select data-pi-filter-value) ---- */
  document.querySelectorAll('[data-pi-filter]').forEach(function (group) {
    var targetSelector = group.getAttribute('data-pi-filter');
    var table = document.querySelector(targetSelector);
    if (!table) return;
    group.querySelectorAll('[data-pi-filter-value]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        group.querySelectorAll('[data-pi-filter-value]').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var value = btn.getAttribute('data-pi-filter-value');
        table.querySelectorAll('tbody tr').forEach(function (row) {
          var status = row.getAttribute('data-status') || '';
          row.style.display = (value === 'all' || status === value) ? '' : 'none';
        });
        updateEmptyState(table);
      });
    });
  });

  function updateEmptyState(table) {
    var visibleRows = Array.prototype.filter.call(
      table.querySelectorAll('tbody tr'),
      function (r) { return r.style.display !== 'none'; }
    );
    var emptyRow = table.querySelector('.pi-table-empty-row');
    if (emptyRow) emptyRow.style.display = visibleRows.length === 0 ? '' : 'none';
  }

  /* ---- Confirmation avant suppression ---- */
  document.querySelectorAll('[data-pi-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      var msg = el.getAttribute('data-pi-confirm') || 'Confirmer cette action ?';
      if (!window.confirm(msg)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });

  /* ---- Loader lors des soumissions de formulaire ---- */
  var overlay = document.querySelector('.pi-loading-overlay');
  document.querySelectorAll('form[data-pi-loading]').forEach(function (form) {
    form.addEventListener('submit', function () {
      if (overlay) overlay.classList.add('active');
    });
  });

  /* ---- Fermeture auto des alertes Django messages ---- */
  document.querySelectorAll('.pi-alert[data-pi-autohide]').forEach(function (alertEl) {
    setTimeout(function () {
      alertEl.classList.add('pi-fade-out');
      setTimeout(function () { alertEl.remove(); }, 400);
    }, 4500);
  });

});
