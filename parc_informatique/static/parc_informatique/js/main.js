/**
 * PARC INFORMATIQUE — comportements front (vanilla JS + SweetAlert2).
 * - Recherche instantanée dans les tableaux (data-pi-table)
 * - Filtres par statut (data-pi-filter)
 * - Champs conditionnels liés à une case à cocher (data-pi-toggle-fields)
 * - Confirmation avant action sensible (SweetAlert2, repli sur window.confirm)
 * - Messages Django affichés en toasts SweetAlert2 (voir window.piDjangoMessages)
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

  /* ---- Champs affichés seulement si une case est cochée ----
     <input type="checkbox" data-pi-toggle-fields="id_a,id_b"> masque les
     blocs contenant #id_a et #id_b tant que la case n'est pas cochée.
     Sans JS, les champs restent visibles (validation côté serveur de toute façon). */
  document.querySelectorAll('[data-pi-toggle-fields]').forEach(function (checkbox) {
    var ids = checkbox.getAttribute('data-pi-toggle-fields').split(',');

    function mettreAJour() {
      ids.forEach(function (id) {
        var champ = document.getElementById(id.trim());
        var bloc = champ && champ.closest('.mb-3');
        if (bloc) bloc.style.display = checkbox.checked ? '' : 'none';
      });
    }

    checkbox.addEventListener('change', mettreAJour);
    mettreAJour();
  });

  /* ---- Confirmation avant suppression (SweetAlert2) ---- */
  document.querySelectorAll('[data-pi-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();

      var message = el.getAttribute('data-pi-confirm') || 'Confirmer cette action ?';

      function executer() {
        if (el.tagName === 'A' && el.href) {
          window.location.href = el.href;
        } else if (el.form) {
          // requestSubmit() (contrairement à submit()) déclenche l'événement
          // 'submit' du formulaire, nécessaire pour que le loader plein
          // écran (data-pi-loading) s'affiche bien après confirmation.
          if (el.form.requestSubmit) {
            el.form.requestSubmit();
          } else {
            el.form.submit();
          }
        } else if (el.closest('form')) {
          var form = el.closest('form');
          if (form.requestSubmit) { form.requestSubmit(); } else { form.submit(); }
        }
      }

      // Repli sur window.confirm si SweetAlert2 n'a pas pu se charger (CDN bloqué).
      if (!window.Swal) {
        if (window.confirm(message)) executer();
        return;
      }

      var estDestructif = el.classList.contains('btn-danger') || el.classList.contains('danger');

      Swal.fire({
        title: 'Confirmation',
        text: message,
        icon: estDestructif ? 'warning' : 'question',
        showCancelButton: true,
        confirmButtonText: estDestructif ? 'Oui, supprimer' : 'Confirmer',
        cancelButtonText: 'Annuler',
        confirmButtonColor: estDestructif ? '#dc2626' : '#4f46e5',
        cancelButtonColor: '#6b7280',
        reverseButtons: true,
        focusCancel: estDestructif,
        buttonsStyling: true,
      }).then(function (result) {
        if (result.isConfirmed) executer();
      });
    });
  });

  /* ---- Messages Django en toasts SweetAlert2 ---- */
  if (window.piDjangoMessages && window.piDjangoMessages.length && window.Swal) {
    var toast = Swal.mixin({
      toast: true,
      position: 'top-end',
      showConfirmButton: false,
      timer: 4500,
      timerProgressBar: true,
      didOpen: function (el) {
        el.addEventListener('mouseenter', Swal.stopTimer);
        el.addEventListener('mouseleave', Swal.resumeTimer);
      },
    });

    var iconPour = function (tag) {
      if (tag.indexOf('error') !== -1 || tag.indexOf('danger') !== -1) return 'error';
      if (tag.indexOf('success') !== -1) return 'success';
      if (tag.indexOf('warning') !== -1) return 'warning';
      return 'info';
    };

    window.piDjangoMessages.forEach(function (msg, index) {
      setTimeout(function () {
        toast.fire({ icon: iconPour(msg.tag), title: msg.text });
      }, index * 350);
    });
  }

  /* ---- Loader lors des soumissions de formulaire ---- */
  var overlay = document.querySelector('.pi-loading-overlay');
  document.querySelectorAll('form[data-pi-loading]').forEach(function (form) {
    form.addEventListener('submit', function () {
      if (overlay) overlay.classList.add('active');
    });
  });

});
