import csv
import io

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now

from parc_informatique.audit import journaliser
from parc_informatique.decorators import role_required
from parc_informatique.forms import (
    AffectationForm,
    AppareilForm,
    BootstrapPasswordChangeForm,
    HistoriqueMaintenanceForm,
    ImporterAppareilsForm,
    LocalForm,
    ModificationAppareilForm,
    TechnicienForm,
    UtilisateurForm,
)
from parc_informatique.models import (
    Appareil,
    HistoriqueAffectation,
    HistoriqueMaintenance,
    JournalAudit,
    Local,
    Notification,
    Technicien,
    Utilisateur,
)
from parc_informatique.notifications import generer_notifications
from parc_informatique.roles import ADMIN, GESTIONNAIRE, TECHNICIEN
from parc_informatique.services.assignments import changer_affectation
from parc_informatique.services.maintenance import (
    changer_etat_appareil,
    ouvrir_maintenance,
    terminer_maintenance as terminer_maintenance_service,
)

PARC_INFORMATIQUE_INDEX = "parc_informatique:index"

APPAREILS_PAR_PAGE = 10
UTILISATEURS_PAR_PAGE = 10
MAINTENANCES_PAR_PAGE = 10
TECHNICIENS_PAR_PAGE = 10
NOTIFICATIONS_PAR_PAGE = 15
LOCAUX_PAR_PAGE = 10
JOURNAL_PAR_PAGE = 25


def dashboard(request):
    appareils = Appareil.objects.all()
    context = {
        "total_appareils": appareils.count(),
        "appareils_disponibles": appareils.filter(etat="Disponible").count(),
        "appareils_maintenance": appareils.filter(etat="En réparation").count(),
        "appareils_obsoletes": appareils.filter(etat="Obsolète").count(),
        "appareils_affectes": appareils.exclude(utilisateur__isnull=True).count(),
        "utilisateurs_actifs": Utilisateur.objects.filter(appareils__isnull=False)
        .distinct()
        .count(),
        "appareils_en_alerte": appareils.filter(etat="En réparation").order_by("nom")[
            :5
        ],
        "dernieres_activites": HistoriqueMaintenance.objects.select_related(
            "appareil"
        ).order_by("-date_intervention")[:6],
    }
    return render(request, "parc_informatique/dashboard.html", context)


def index(request):
    appareils_list = Appareil.objects.all().order_by("nom")
    paginator = Paginator(appareils_list, APPAREILS_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "appareils": page_obj,  # itérable : {% for appareil in appareils %} fonctionne toujours
        "page_obj": page_obj,
        "total_appareils": paginator.count,
    }
    return render(request, "parc_informatique/index.html", context)


def afficher_appareil(request, appareil_id):
    appareil = get_object_or_404(Appareil, pk=appareil_id)
    context = {
        "appareil": appareil,
        "local": appareil.localisation,
    }
    return render(request, "parc_informatique/afficher_appareil.html", context)


@role_required(ADMIN, GESTIONNAIRE)
def ajouter_appareil(request):
    if request.method == "POST":
        form = AppareilForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                appareil = form.save()
                # L'équipement et sa première affectation sont enregistrés ensemble.
                if appareil.utilisateur:
                    HistoriqueAffectation.objects.create(
                        appareil=appareil,
                        utilisateur=appareil.utilisateur,
                        date_debut=appareil.date_acquisition or now().date(),
                    )
                journaliser(request, "creation", appareil)
            return redirect(PARC_INFORMATIQUE_INDEX)
    else:
        form = AppareilForm()
    context = {"form": form}
    return render(request, "parc_informatique/appareil-form.html", context)


@role_required(ADMIN, GESTIONNAIRE)
def modifier_appareil(request, appareil_id):
    appareil = get_object_or_404(Appareil, pk=appareil_id)
    ancien_etat = appareil.etat

    if request.method == "POST":
        form = ModificationAppareilForm(request.POST, instance=appareil)

        if form.is_valid():
            nouvel_etat = form.cleaned_data["etat"]

            if nouvel_etat == "En réparation" and ancien_etat != "En réparation":
                # On ne bascule jamais l'état vers "En réparation" depuis ce
                # formulaire rapide : ça créait des appareils "En réparation"
                # sans aucune intervention associée, donc invisibles depuis
                # la page Maintenances. On redirige vers le formulaire dédié
                # pour que technicien + description soient bien enregistrés.
                messages.info(
                    request,
                    "Merci de renseigner les détails de l'intervention (technicien, description) "
                    "pour envoyer cet appareil en maintenance.",
                )
                return redirect(
                    "parc_informatique:envoyer_en_maintenance", appareil_id=appareil.id
                )

            appareil = changer_etat_appareil(
                appareil_id=appareil.pk, nouvel_etat=nouvel_etat
            )
            journaliser(
                request, "modification", appareil, details=f"état → {nouvel_etat}"
            )

            return redirect(PARC_INFORMATIQUE_INDEX)
    else:
        form = ModificationAppareilForm(instance=appareil)

    return render(
        request,
        "parc_informatique/appareil_edit_form.html",
        {"form": form, "appareil": appareil},
    )


@role_required(ADMIN)
def supprimer_appareil(request, appareil_id):
    appareil = Appareil.objects.get(pk=appareil_id)
    if request.method == "POST":
        journaliser(request, "suppression", appareil)
        appareil.delete()
        return redirect(PARC_INFORMATIQUE_INDEX)
    return render(
        request, "parc_informatique/confirmer_suppression.html", {"appareil": appareil}
    )


def historique_maintenance(request, appareil_id):
    appareil = get_object_or_404(Appareil, pk=appareil_id)
    maintenances = HistoriqueMaintenance.objects.filter(appareil=appareil).order_by(
        "-date_intervention"
    )
    context = {
        "appareil": appareil,
        "historiquemaintenances": maintenances,
    }
    return render(request, "parc_informatique/historique_maintenance.html", context)


@role_required(ADMIN, GESTIONNAIRE, TECHNICIEN)
def envoyer_en_maintenance(request, appareil_id):
    appareil = get_object_or_404(Appareil, pk=appareil_id)

    if request.method == "POST":
        form = HistoriqueMaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = ouvrir_maintenance(
                appareil_id=appareil.pk,
                description=form.cleaned_data["description"],
                technicien=form.cleaned_data.get("technicien"),
                cout=form.cleaned_data.get("cout"),
                date_intervention=now().date(),
            )
            journaliser(
                request,
                "action",
                appareil,
                details=f"Envoyé en maintenance (intervention #{maintenance.id})",
            )
            return redirect(
                "parc_informatique:afficher_appareil", appareil_id=appareil.id
            )
    else:
        form = HistoriqueMaintenanceForm()

    return render(
        request,
        "parc_informatique/envoyer_en_maintenance.html",
        {"form": form, "appareil": appareil},
    )


# ---------------------------------------------------------------------------
# Utilisateurs & affectations
# ---------------------------------------------------------------------------


def liste_utilisateurs(request):
    utilisateurs_list = Utilisateur.objects.all().order_by("nom", "prenom")
    paginator = Paginator(utilisateurs_list, UTILISATEURS_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "utilisateurs": page_obj,
        "page_obj": page_obj,
        "total_utilisateurs": paginator.count,
    }
    return render(request, "parc_informatique/utilisateurs_liste.html", context)


def profil_utilisateur(request, utilisateur_id):
    utilisateur = get_object_or_404(Utilisateur, pk=utilisateur_id)
    appareils_affectes = Appareil.objects.filter(utilisateur=utilisateur).order_by(
        "nom"
    )
    historique_affectations = (
        HistoriqueAffectation.objects.filter(utilisateur=utilisateur)
        .select_related("appareil")
        .order_by("-date_debut")
    )
    context = {
        "utilisateur": utilisateur,
        "appareils_affectes": appareils_affectes,
        "historique_affectations": historique_affectations,
    }
    return render(request, "parc_informatique/utilisateur_profil.html", context)


@role_required(ADMIN, GESTIONNAIRE)
def affecter_appareil(request, appareil_id):
    """Change l'utilisateur affecté à un appareil et historise le changement."""
    appareil = get_object_or_404(Appareil, pk=appareil_id)

    if request.method == "POST":
        form = AffectationForm(request.POST, instance=appareil)
        if form.is_valid():
            nouvel_utilisateur = form.cleaned_data["utilisateur"]
            appareil, changement_effectue = changer_affectation(
                appareil_id=appareil.pk, utilisateur=nouvel_utilisateur
            )
            if changement_effectue:
                journaliser(
                    request,
                    "action",
                    appareil,
                    details=(
                        f"Affecté à {nouvel_utilisateur}"
                        if nouvel_utilisateur
                        else "Retiré à son utilisateur"
                    ),
                )
            return redirect(
                "parc_informatique:afficher_appareil", appareil_id=appareil.id
            )
    else:
        form = AffectationForm(instance=appareil)

    return render(
        request,
        "parc_informatique/affecter_appareil.html",
        {"form": form, "appareil": appareil},
    )


def historique_affectations(request, appareil_id):
    appareil = get_object_or_404(Appareil, pk=appareil_id)
    affectations = (
        HistoriqueAffectation.objects.filter(appareil=appareil)
        .select_related("utilisateur")
        .order_by("-date_debut")
    )
    context = {"appareil": appareil, "affectations": affectations}
    return render(request, "parc_informatique/historique_affectations.html", context)


# ---------------------------------------------------------------------------
# Maintenances
# ---------------------------------------------------------------------------


def liste_maintenances(request):
    """Vue globale de toutes les interventions de maintenance, tous appareils confondus."""
    maintenances_list = HistoriqueMaintenance.objects.select_related(
        "appareil"
    ).order_by("-date_intervention", "-id")
    paginator = Paginator(maintenances_list, MAINTENANCES_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "maintenances": page_obj,
        "page_obj": page_obj,
        "total_maintenances": paginator.count,
        "maintenances_en_cours": HistoriqueMaintenance.objects.filter(
            statut="Non réparé"
        ).count(),
        "maintenances_terminees": HistoriqueMaintenance.objects.filter(
            statut="Réparé"
        ).count(),
    }
    return render(request, "parc_informatique/maintenances_liste.html", context)


@role_required(ADMIN, GESTIONNAIRE, TECHNICIEN)
def terminer_maintenance(request, maintenance_id):
    """
    Marque une intervention comme réparée. Si l'appareil concerné n'a plus
    aucune autre maintenance "Non réparé" en cours, il repasse automatiquement
    à l'état "Disponible" (symétrique de `envoyer_en_maintenance`, qui le
    faisait passer à "En réparation").
    """
    maintenance = get_object_or_404(HistoriqueMaintenance, pk=maintenance_id)

    if request.method == "POST":
        if (
            TECHNICIEN in request.user.groups.values_list("name", flat=True)
            and not request.user.is_superuser
            and not request.user.groups.filter(name__in=[ADMIN, GESTIONNAIRE]).exists()
            and (
                not maintenance.technicien_id
                or maintenance.technicien.compte_utilisateur_id != request.user.pk
            )
        ):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "Vous ne pouvez clôturer que vos propres interventions."
            )
        maintenance = terminer_maintenance_service(maintenance_id=maintenance.pk)
        journaliser(
            request,
            "action",
            maintenance.appareil,
            details=f"Maintenance #{maintenance.id} terminée",
        )

    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("parc_informatique:liste_maintenances")


# ---------------------------------------------------------------------------
# Techniciens
# ---------------------------------------------------------------------------


def liste_techniciens(request):
    techniciens_list = Technicien.objects.all().order_by("nom", "prenom")
    paginator = Paginator(techniciens_list, TECHNICIENS_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "techniciens": page_obj,
        "page_obj": page_obj,
        "total_techniciens": paginator.count,
    }
    return render(request, "parc_informatique/techniciens_liste.html", context)


def _journaliser_technicien(request, action, technicien, form):
    """Journalise la fiche, en précisant si un compte de connexion a été créé
    (jamais le mot de passe, évidemment : seulement l'identifiant)."""
    details = ""
    if form.compte_cree:
        details = f"Compte de connexion « {form.compte_cree.username} » créé (rôle Technicien)"
    journaliser(request, action, technicien, details=details)


def _message_technicien(base, form):
    if form.compte_cree:
        return f"{base} Compte de connexion « {form.compte_cree.username} » créé."
    return base


@role_required(ADMIN, GESTIONNAIRE)
def ajouter_technicien(request):
    if request.method == "POST":
        form = TechnicienForm(request.POST)
        if form.is_valid():
            technicien = form.save()
            _journaliser_technicien(request, "creation", technicien, form)
            messages.success(
                request, _message_technicien("Technicien ajouté avec succès.", form)
            )
            return redirect("parc_informatique:liste_techniciens")
    else:
        form = TechnicienForm()
    return render(request, "parc_informatique/technicien-form.html", {"form": form})


@role_required(ADMIN, GESTIONNAIRE)
def modifier_technicien(request, technicien_id):
    technicien = get_object_or_404(Technicien, pk=technicien_id)
    if request.method == "POST":
        form = TechnicienForm(request.POST, instance=technicien)
        if form.is_valid():
            form.save()
            _journaliser_technicien(request, "modification", technicien, form)
            messages.success(
                request, _message_technicien("Technicien mis à jour.", form)
            )
            return redirect("parc_informatique:liste_techniciens")
    else:
        form = TechnicienForm(instance=technicien)
    return render(
        request,
        "parc_informatique/technicien_edit_form.html",
        {"form": form, "technicien": technicien},
    )


@role_required(ADMIN)
def supprimer_technicien(request, technicien_id):
    technicien = get_object_or_404(Technicien, pk=technicien_id)
    if request.method == "POST":
        journaliser(request, "suppression", technicien)
        technicien.delete()
        messages.success(
            request, "Technicien supprimé. Son historique d'interventions est conservé."
        )
        return redirect("parc_informatique:liste_techniciens")
    return render(
        request,
        "parc_informatique/confirmer_suppression_technicien.html",
        {"technicien": technicien},
    )


# ---------------------------------------------------------------------------
# Compte (profil / paramètres)
# ---------------------------------------------------------------------------


@login_required
def profil_compte(request):
    return render(request, "parc_informatique/compte/profil.html")


@login_required
def parametres_compte(request):
    if request.method == "POST":
        password_form = BootstrapPasswordChangeForm(
            user=request.user, data=request.POST
        )
        if password_form.is_valid():
            user = password_form.save()
            # Sans ça, changer son propre mot de passe invaliderait la
            # session en cours et déconnecterait immédiatement l'utilisateur.
            update_session_auth_hash(request, user)
            messages.success(request, "Mot de passe mis à jour avec succès.")
            return redirect("parc_informatique:parametres_compte")
    else:
        password_form = BootstrapPasswordChangeForm(user=request.user)

    return render(
        request,
        "parc_informatique/compte/parametres.html",
        {"password_form": password_form},
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@login_required
def notifications_liste(request):
    generer_notifications()

    notifications_list = Notification.objects.annotate(
        lue=Exists(Notification.objects.filter(pk=OuterRef("pk"), lue_par=request.user))
    ).order_by("-cree_le")

    paginator = Paginator(notifications_list, NOTIFICATIONS_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "notifications": page_obj,
        "page_obj": page_obj,
        "notifications_non_resolues_count": Notification.objects.filter(
            resolue=False
        ).count(),
    }
    return render(request, "parc_informatique/notifications_liste.html", context)


@login_required
def marquer_notifications_lues(request):
    if request.method == "POST":
        actives = Notification.objects.filter(resolue=False)
        request.user.notifications_lues.add(*actives)

    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("parc_informatique:notifications_liste")


# ---------------------------------------------------------------------------
# CRUD Utilisateurs
# ---------------------------------------------------------------------------


@role_required(ADMIN, GESTIONNAIRE)
def ajouter_utilisateur(request):
    if request.method == "POST":
        form = UtilisateurForm(request.POST)
        if form.is_valid():
            utilisateur = form.save()
            journaliser(request, "creation", utilisateur)
            messages.success(request, "Utilisateur ajouté avec succès.")
            return redirect("parc_informatique:liste_utilisateurs")
    else:
        form = UtilisateurForm()
    return render(request, "parc_informatique/utilisateur-form.html", {"form": form})


@role_required(ADMIN, GESTIONNAIRE)
def modifier_utilisateur(request, utilisateur_id):
    utilisateur = get_object_or_404(Utilisateur, pk=utilisateur_id)
    if request.method == "POST":
        form = UtilisateurForm(request.POST, instance=utilisateur)
        if form.is_valid():
            form.save()
            journaliser(request, "modification", utilisateur)
            messages.success(request, "Utilisateur mis à jour.")
            return redirect(
                "parc_informatique:profil_utilisateur", utilisateur_id=utilisateur.id
            )
    else:
        form = UtilisateurForm(instance=utilisateur)
    return render(
        request,
        "parc_informatique/utilisateur_edit_form.html",
        {"form": form, "utilisateur": utilisateur},
    )


@role_required(ADMIN)
def supprimer_utilisateur(request, utilisateur_id):
    utilisateur = get_object_or_404(Utilisateur, pk=utilisateur_id)
    if request.method == "POST":
        journaliser(request, "suppression", utilisateur)
        utilisateur.delete()
        messages.success(request, "Utilisateur supprimé.")
        return redirect("parc_informatique:liste_utilisateurs")
    return render(
        request,
        "parc_informatique/confirmer_suppression_utilisateur.html",
        {"utilisateur": utilisateur},
    )


# ---------------------------------------------------------------------------
# CRUD Locaux
# ---------------------------------------------------------------------------


def liste_locaux(request):
    locaux_list = Local.objects.annotate(nb_appareils=Count("appareils")).order_by(
        "batiment", "nom"
    )
    paginator = Paginator(locaux_list, LOCAUX_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "locaux": page_obj,
        "page_obj": page_obj,
        "total_locaux": paginator.count,
    }
    return render(request, "parc_informatique/locaux_liste.html", context)


@role_required(ADMIN, GESTIONNAIRE)
def ajouter_local(request):
    if request.method == "POST":
        form = LocalForm(request.POST)
        if form.is_valid():
            local = form.save()
            journaliser(request, "creation", local)
            messages.success(request, "Local ajouté avec succès.")
            return redirect("parc_informatique:liste_locaux")
    else:
        form = LocalForm()
    return render(request, "parc_informatique/local-form.html", {"form": form})


@role_required(ADMIN, GESTIONNAIRE)
def modifier_local(request, local_id):
    local = get_object_or_404(Local, pk=local_id)
    if request.method == "POST":
        form = LocalForm(request.POST, instance=local)
        if form.is_valid():
            form.save()
            journaliser(request, "modification", local)
            messages.success(request, "Local mis à jour.")
            return redirect("parc_informatique:liste_locaux")
    else:
        form = LocalForm(instance=local)
    return render(
        request,
        "parc_informatique/local_edit_form.html",
        {"form": form, "local": local},
    )


@role_required(ADMIN)
def supprimer_local(request, local_id):
    local = get_object_or_404(Local, pk=local_id)
    if request.method == "POST":
        journaliser(request, "suppression", local)
        local.delete()
        messages.success(request, "Local supprimé.")
        return redirect("parc_informatique:liste_locaux")
    return render(
        request, "parc_informatique/confirmer_suppression_local.html", {"local": local}
    )


# ---------------------------------------------------------------------------
# Recherche globale
# ---------------------------------------------------------------------------


@login_required
def recherche_globale(request):
    terme = request.GET.get("q", "").strip()
    resultats = {"appareils": [], "utilisateurs": [], "techniciens": []}

    if terme:
        resultats["appareils"] = Appareil.objects.filter(
            Q(nom__icontains=terme)
            | Q(numero_serie__icontains=terme)
            | Q(marque__icontains=terme)
            | Q(modele__icontains=terme)
        ).order_by("nom")[:25]
        resultats["utilisateurs"] = Utilisateur.objects.filter(
            Q(nom__icontains=terme)
            | Q(prenom__icontains=terme)
            | Q(email__icontains=terme)
        ).order_by("nom")[:25]
        resultats["techniciens"] = Technicien.objects.filter(
            Q(nom__icontains=terme) | Q(prenom__icontains=terme)
        ).order_by("nom")[:25]

    total = (
        len(resultats["appareils"])
        + len(resultats["utilisateurs"])
        + len(resultats["techniciens"])
    )
    context = {"terme": terme, "resultats": resultats, "total_resultats": total}
    return render(request, "parc_informatique/recherche_resultats.html", context)


# ---------------------------------------------------------------------------
# Mes interventions (technicien connecté)
# ---------------------------------------------------------------------------


@login_required
def mes_interventions(request):
    technicien = getattr(request.user, "profil_technicien", None)
    if technicien is None:
        messages.info(request, "Votre compte n'est relié à aucune fiche technicien.")
        return redirect("parc_informatique:dashboard")

    maintenances_list = (
        HistoriqueMaintenance.objects.filter(technicien=technicien)
        .select_related("appareil")
        .order_by("-date_intervention", "-id")
    )
    paginator = Paginator(maintenances_list, MAINTENANCES_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "technicien": technicien,
        "maintenances": page_obj,
        "page_obj": page_obj,
        "total_maintenances": paginator.count,
        "maintenances_en_cours": maintenances_list.filter(statut="Non réparé").count(),
    }
    return render(request, "parc_informatique/mes_interventions.html", context)


# ---------------------------------------------------------------------------
# Exports CSV
# ---------------------------------------------------------------------------


def _csv_safe(value):
    """Neutralise les formules exécutables lors de l'ouverture d'un CSV dans un tableur."""
    if value is None:
        return ""
    text_value = str(value)
    if text_value.lstrip(" \\t\\r\\n").startswith(("=", "+", "-", "@")):
        return "'" + text_value
    return text_value


@role_required(ADMIN, GESTIONNAIRE)
def export_appareils_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="appareils.csv"'
    response.write("\ufeff")  # BOM pour un bon rendu des accents dans Excel

    writer = csv.writer(response)
    writer.writerow(
        [
            "Nom",
            "Type",
            "Marque",
            "Modèle",
            "Numéro de série",
            "État",
            "Date d'acquisition",
            "Fournisseur",
            "Prix d'achat",
            "Fin de garantie",
            "Localisation",
            "Utilisateur",
        ]
    )
    for a in Appareil.objects.select_related("localisation", "utilisateur").order_by(
        "nom"
    ):
        writer.writerow(
            [
                *[
                    _csv_safe(value)
                    for value in (
                        a.nom,
                        a.type,
                        a.marque,
                        a.modele,
                        a.numero_serie,
                        a.etat,
                        a.date_acquisition,
                        a.fournisseur,
                        a.prix_achat,
                        a.date_fin_garantie,
                        a.localisation,
                        a.utilisateur,
                    )
                ],
            ]
        )
    journaliser(request, "action", Appareil, details="Export CSV de l'inventaire")
    return response


@role_required(ADMIN, GESTIONNAIRE)
def export_maintenances_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="maintenances.csv"'
    response.write("\ufeff")

    writer = csv.writer(response)
    writer.writerow(
        [
            "Appareil",
            "Date d'intervention",
            "Date de réparation",
            "Technicien",
            "Statut",
            "Coût",
            "Description",
        ]
    )
    for m in HistoriqueMaintenance.objects.select_related(
        "appareil", "technicien"
    ).order_by("-date_intervention"):
        writer.writerow(
            [
                *[
                    _csv_safe(value)
                    for value in (
                        m.appareil.nom,
                        m.date_intervention,
                        m.date_reparation,
                        m.technicien,
                        m.statut,
                        m.cout,
                        m.description,
                    )
                ],
            ]
        )
    journaliser(
        request, "action", HistoriqueMaintenance, details="Export CSV des maintenances"
    )
    return response


# ---------------------------------------------------------------------------
# Import CSV en masse
# ---------------------------------------------------------------------------


@role_required(ADMIN, GESTIONNAIRE)
def importer_appareils(request):
    resultat = None
    if request.method == "POST":
        form = ImporterAppareilsForm(request.POST, request.FILES)
        if form.is_valid():
            resultat = _traiter_import_csv(request, request.FILES["fichier"])
    else:
        form = ImporterAppareilsForm()

    return render(
        request,
        "parc_informatique/importer_appareils.html",
        {"form": form, "resultat": resultat},
    )


def _traiter_import_csv(request, fichier):
    """Import CSV borné, validé et atomique par ligne ; les erreurs internes ne sont jamais exposées."""
    from decimal import Decimal, InvalidOperation

    from django.core.exceptions import ValidationError
    from django.db import IntegrityError, transaction
    from django.utils.dateparse import parse_date

    erreurs = []
    crees = 0
    taille = getattr(fichier, "size", None)
    if taille is not None and taille > 5 * 1024 * 1024:
        return {"crees": 0, "erreurs": ["Fichier trop volumineux (maximum : 5 Mo)."]}

    try:
        try:
            donnees = fichier.read(5 * 1024 * 1024 + 1)
        except (
            TypeError
        ):  # compatibilité avec les objets fichier simples utilisés dans les tests
            donnees = fichier.read()
        contenu = donnees.decode("utf-8-sig")
    except (UnicodeDecodeError, AttributeError):
        return {"crees": 0, "erreurs": ["Fichier illisible : encodage attendu UTF-8."]}
    if len(contenu.encode("utf-8")) > 5 * 1024 * 1024:
        return {"crees": 0, "erreurs": ["Fichier trop volumineux (maximum : 5 Mo)."]}

    lecteur = csv.DictReader(io.StringIO(contenu))
    colonnes_requises = {"nom", "type", "numero_serie"}
    if not lecteur.fieldnames or not colonnes_requises.issubset(
        set(lecteur.fieldnames)
    ):
        return {
            "crees": 0,
            "erreurs": [
                "En-têtes invalides : nom, type et numero_serie sont obligatoires."
            ],
        }

    for i, ligne in enumerate(lecteur, start=2):
        if i > 1001:
            erreurs.append("Import interrompu : maximum 1 000 lignes par fichier.")
            break

        nom = (ligne.get("nom") or "").strip()
        type_ = (ligne.get("type") or "").strip()
        numero_serie = (ligne.get("numero_serie") or "").strip()
        if not (nom and type_ and numero_serie):
            erreurs.append(f"Ligne {i} : nom, type et numero_serie sont obligatoires.")
            continue
        if type_ not in dict(Appareil.TYPE_CHOICES):
            erreurs.append(f"Ligne {i} : type d'appareil invalide.")
            continue
        if Appareil.objects.filter(numero_serie=numero_serie).exists():
            erreurs.append(
                f"Ligne {i} : numéro de série « {numero_serie} » déjà existant, ignoré."
            )
            continue

        etat = (ligne.get("etat") or "Disponible").strip()
        if etat not in dict(Appareil.ETAT_CHOICES):
            erreurs.append(f"Ligne {i} : état d'appareil invalide.")
            continue

        try:
            acquisition_raw = (ligne.get("date_acquisition") or "").strip()
            garantie_raw = (ligne.get("date_fin_garantie") or "").strip()
            acquisition = parse_date(acquisition_raw) if acquisition_raw else None
            garantie = parse_date(garantie_raw) if garantie_raw else None
            if acquisition_raw and acquisition is None:
                raise ValueError("date d'acquisition invalide")
            if garantie_raw and garantie is None:
                raise ValueError("date de garantie invalide")
            prix_raw = (ligne.get("prix_achat") or "").strip()
            prix = Decimal(prix_raw) if prix_raw else None
            if prix is not None and prix < 0:
                raise ValueError("prix négatif")

            localisation = None
            local_raw = (ligne.get("localisation") or "").strip()
            if local_raw:
                localisation = Local.objects.filter(nom=local_raw).first()
                if not localisation:
                    raise ValueError("localisation inconnue")

            utilisateur = None
            email_raw = (ligne.get("utilisateur") or "").strip()
            if email_raw:
                utilisateur = Utilisateur.objects.filter(
                    email__iexact=email_raw
                ).first()
                if not utilisateur:
                    raise ValueError("utilisateur inconnu")

            appareil = Appareil(
                nom=nom,
                type=type_,
                marque=(ligne.get("marque") or "").strip(),
                modele=(ligne.get("modele") or "").strip(),
                numero_serie=numero_serie,
                etat=etat,
                date_acquisition=acquisition,
                fournisseur=(ligne.get("fournisseur") or "").strip(),
                prix_achat=prix,
                date_fin_garantie=garantie,
                localisation=localisation,
                utilisateur=utilisateur,
            )
            appareil.full_clean()
            with transaction.atomic():
                appareil.save()
                if utilisateur:
                    HistoriqueAffectation.objects.create(
                        appareil=appareil,
                        utilisateur=utilisateur,
                        date_debut=acquisition or now().date(),
                    )
            crees += 1
        except (ValidationError, ValueError, InvalidOperation, IntegrityError):
            erreurs.append(
                f"Ligne {i} : données invalides ou numéro de série déjà utilisé."
            )
            continue

    if crees:
        journaliser(
            request,
            "action",
            Appareil,
            details=f"Import CSV : {crees} appareil(s) créé(s)",
        )
    return {"crees": crees, "erreurs": erreurs}


def qr_code_appareil(request, appareil_id):
    """
    PNG généré à la volée (pas de service tiers, tout reste interne) — pointe
    vers la fiche appareil, pour un scan rapide depuis un mobile.
    Nécessite le package `qrcode` (voir INSTRUCTIONS_INTEGRATION.md).
    """
    import qrcode
    from django.urls import reverse

    appareil = get_object_or_404(Appareil, pk=appareil_id)
    url = request.build_absolute_uri(
        reverse("parc_informatique:afficher_appareil", args=[appareil.id])
    )
    img = qrcode.make(url, box_size=6, border=2)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------


@role_required(ADMIN, GESTIONNAIRE)
def statistiques(request):
    maintenances_terminees = HistoriqueMaintenance.objects.filter(
        statut="Réparé", date_reparation__isnull=False
    )

    duree_moyenne = None
    if maintenances_terminees.exists():
        total_jours = sum(
            m.duree_jours for m in maintenances_terminees if m.duree_jours is not None
        )
        nb = sum(1 for m in maintenances_terminees if m.duree_jours is not None)
        duree_moyenne = round(total_jours / nb, 1) if nb else None

    cout_total = (
        HistoriqueMaintenance.objects.aggregate(total=Sum("cout"))["total"] or 0
    )

    top_appareils_couteux = (
        Appareil.objects.annotate(
            cout_maintenance=Sum("maintenances__cout"),
            nb_interventions=Count("maintenances"),
        )
        .filter(cout_maintenance__isnull=False)
        .order_by("-cout_maintenance")[:8]
    )

    repartition_par_type = (
        Appareil.objects.values("type").annotate(total=Count("id")).order_by("-total")
    )

    context = {
        "duree_moyenne_reparation": duree_moyenne,
        "cout_total_maintenance": cout_total,
        "top_appareils_couteux": top_appareils_couteux,
        "repartition_par_type": repartition_par_type,
        "nb_maintenances_terminees": maintenances_terminees.count(),
        "nb_appareils_garantie_expiree": sum(
            1 for a in Appareil.objects.all() if a.garantie_expiree
        ),
    }
    return render(request, "parc_informatique/statistiques.html", context)


# ---------------------------------------------------------------------------
# Journal d'audit
# ---------------------------------------------------------------------------


@role_required(ADMIN)
def liste_journal_audit(request):
    entrees_list = JournalAudit.objects.select_related("utilisateur").order_by(
        "-horodatage"
    )
    paginator = Paginator(entrees_list, JOURNAL_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {"entrees": page_obj, "page_obj": page_obj}
    return render(request, "parc_informatique/journal_audit.html", context)
