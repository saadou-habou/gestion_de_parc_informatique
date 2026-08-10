"""
Petit helper pour alimenter le journal d'audit depuis les vues. Appelé
explicitement à chaque action sensible (création/modif/suppression
d'appareil, technicien, utilisateur, local, changement d'affectation, fin de
maintenance) — pas de signal automatique, pour que ce qui est tracé reste
lisible et prévisible en un coup d'œil dans les vues concernées.
"""

from parc_informatique.models import JournalAudit


def journaliser(request, action, obj, details=""):
    JournalAudit.objects.create(
        utilisateur=request.user if request.user.is_authenticated else None,
        action=action,
        modele=type(obj).__name__,
        objet_repr=str(obj)[:255],
        details=details[:255],
    )
