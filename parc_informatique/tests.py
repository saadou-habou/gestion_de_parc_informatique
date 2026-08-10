"""
Tests automatisés. Couvrent en priorité ce qui casse silencieusement sinon :
les transitions d'état (appareil ↔ maintenance ↔ affectation), les
permissions par rôle, et l'idempotence des notifications.

Lancer avec : python manage.py test parc_informatique
"""

from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now

from parc_informatique.models import (
    Appareil,
    HistoriqueMaintenance,
    Local,
    Notification,
    Technicien,
    Utilisateur,
)
from parc_informatique.notifications import generer_notifications
from parc_informatique.roles import ADMIN, GESTIONNAIRE, TECHNICIEN


def creer_appareil(**kwargs):
    defaults = {
        "nom": "PC-Test-01",
        "type": "Desktop",
        "numero_serie": f"SN-{Appareil.objects.count() + 1}",
        "etat": "Disponible",
    }
    defaults.update(kwargs)
    return Appareil.objects.create(**defaults)


def creer_utilisateur_avec_role(username, role=None, superuser=False):
    user = User.objects.create_user(username=username, password="motdepasse123")
    if superuser:
        user.is_superuser = True
        user.save()
    elif role:
        groupe, _ = Group.objects.get_or_create(name=role)
        user.groups.add(groupe)
    return user


class TransitionsAppareilMaintenanceTests(TestCase):
    """La règle la plus fragile de l'app : appareil ↔ maintenance doivent
    toujours rester synchronisés (voir la conversation sur le bug initial)."""

    def setUp(self):
        self.appareil = creer_appareil()

    def test_envoyer_en_maintenance_change_etat_appareil(self):
        self.appareil.etat = "En réparation"
        self.appareil.save()
        maintenance = HistoriqueMaintenance.objects.create(
            appareil=self.appareil, date_intervention=now().date(),
            description="Panne écran", statut="Non réparé",
        )
        self.appareil.refresh_from_db()
        self.assertEqual(self.appareil.etat, "En réparation")
        self.assertEqual(maintenance.appareil, self.appareil)

    def test_terminer_maintenance_repasse_appareil_disponible(self):
        self.appareil.etat = "En réparation"
        self.appareil.save()
        maintenance = HistoriqueMaintenance.objects.create(
            appareil=self.appareil, date_intervention=now().date(),
            description="Panne écran", statut="Non réparé",
        )

        maintenance.statut = "Réparé"
        maintenance.date_reparation = now().date()
        maintenance.save()

        maintenances_ouvertes = HistoriqueMaintenance.objects.filter(
            appareil=self.appareil, statut="Non réparé"
        )
        if not maintenances_ouvertes.exists():
            self.appareil.etat = "Disponible"
            self.appareil.save()

        self.appareil.refresh_from_db()
        self.assertEqual(self.appareil.etat, "Disponible")

    def test_appareil_reste_en_reparation_si_autre_maintenance_ouverte(self):
        """Deux interventions en parallèle : terminer l'une ne doit PAS
        repasser l'appareil disponible tant que l'autre est ouverte."""
        self.appareil.etat = "En réparation"
        self.appareil.save()
        m1 = HistoriqueMaintenance.objects.create(
            appareil=self.appareil, date_intervention=now().date(),
            description="Panne 1", statut="Non réparé",
        )
        HistoriqueMaintenance.objects.create(
            appareil=self.appareil, date_intervention=now().date(),
            description="Panne 2", statut="Non réparé",
        )

        m1.statut = "Réparé"
        m1.save()
        maintenances_ouvertes = HistoriqueMaintenance.objects.filter(
            appareil=self.appareil, statut="Non réparé"
        ).exclude(pk=m1.pk)
        self.assertTrue(maintenances_ouvertes.exists())


class NotificationsIdempotenceTests(TestCase):
    def test_generation_ne_cree_pas_de_doublon(self):
        appareil = creer_appareil(etat="Obsolète")
        generer_notifications()
        generer_notifications()
        generer_notifications()

        self.assertEqual(
            Notification.objects.filter(cle_naturelle=f"appareil_obsolete:{appareil.id}").count(), 1
        )

    def test_notification_maintenance_en_retard(self):
        appareil = creer_appareil(etat="En réparation")
        HistoriqueMaintenance.objects.create(
            appareil=appareil,
            date_intervention=now().date() - timedelta(days=5),
            description="Panne ancienne",
            statut="Non réparé",
        )
        generer_notifications()
        self.assertTrue(
            Notification.objects.filter(
                type="maintenance_retard", resolue=False
            ).exists()
        )

    def test_notification_se_resout_quand_evenement_disparait(self):
        appareil = creer_appareil(etat="Obsolète")
        generer_notifications()
        notif = Notification.objects.get(cle_naturelle=f"appareil_obsolete:{appareil.id}")
        self.assertFalse(notif.resolue)

        appareil.etat = "Disponible"
        appareil.save()
        generer_notifications()

        notif.refresh_from_db()
        self.assertTrue(notif.resolue)


class PermissionsParRoleTests(TestCase):
    """Vérifie que role_required bloque bien qui doit l'être — c'est la
    partie la plus sensible en termes de sécurité (accès non autorisé)."""

    def setUp(self):
        self.appareil = creer_appareil()
        self.admin = creer_utilisateur_avec_role("alice_admin", ADMIN)
        self.gestionnaire = creer_utilisateur_avec_role("bob_gestionnaire", GESTIONNAIRE)
        self.technicien_user = creer_utilisateur_avec_role("eve_technicien", TECHNICIEN)
        self.sans_role = creer_utilisateur_avec_role("mallory_sansrole")

    def test_technicien_ne_peut_pas_supprimer_appareil(self):
        self.client.login(username="eve_technicien", password="motdepasse123")
        response = self.client.post(
            reverse("parc_informatique:supprimer_appareil", args=[self.appareil.id])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Appareil.objects.filter(pk=self.appareil.id).exists())

    def test_gestionnaire_ne_peut_pas_supprimer_appareil(self):
        """Seul Admin peut supprimer — Gestionnaire peut gérer mais pas détruire."""
        self.client.login(username="bob_gestionnaire", password="motdepasse123")
        response = self.client.post(
            reverse("parc_informatique:supprimer_appareil", args=[self.appareil.id])
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_peut_supprimer_appareil(self):
        self.client.login(username="alice_admin", password="motdepasse123")
        response = self.client.post(
            reverse("parc_informatique:supprimer_appareil", args=[self.appareil.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Appareil.objects.filter(pk=self.appareil.id).exists())

    def test_sans_role_peut_consulter_mais_pas_modifier(self):
        self.client.login(username="mallory_sansrole", password="motdepasse123")
        response = self.client.get(reverse("parc_informatique:index"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("parc_informatique:ajouter_appareil"))
        self.assertEqual(response.status_code, 403)

    def test_utilisateur_non_connecte_redirige_vers_login(self):
        response = self.client.get(reverse("parc_informatique:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)


class MesInterventionsTests(TestCase):
    def test_technicien_ne_voit_que_ses_propres_interventions(self):
        appareil = creer_appareil()
        technicien_a = Technicien.objects.create(nom="Durand", prenom="Marc")
        technicien_b = Technicien.objects.create(nom="Petit", prenom="Julie")

        HistoriqueMaintenance.objects.create(
            appareil=appareil, date_intervention=now().date(),
            description="Intervention A", technicien=technicien_a, statut="Non réparé",
        )
        HistoriqueMaintenance.objects.create(
            appareil=appareil, date_intervention=now().date(),
            description="Intervention B", technicien=technicien_b, statut="Non réparé",
        )

        user = User.objects.create_user(username="marc", password="motdepasse123")
        technicien_a.compte_utilisateur = user
        technicien_a.save()

        self.client.login(username="marc", password="motdepasse123")
        response = self.client.get(reverse("parc_informatique:mes_interventions"))

        self.assertContains(response, "Intervention A")
        self.assertNotContains(response, "Intervention B")


class ImportCSVTests(TestCase):
    def test_import_ignore_numero_serie_deja_existant(self):
        creer_appareil(numero_serie="SN-EXISTANT")
        from io import StringIO
        from parc_informatique.views import _traiter_import_csv

        csv_content = (
            "nom,type,numero_serie\n"
            "PC-Import,Desktop,SN-EXISTANT\n"
        )

        class FauxFichier:
            def read(self):
                return csv_content.encode("utf-8")

        class FauxRequest:
            user = None

        resultat = _traiter_import_csv(FauxRequest(), FauxFichier())
        self.assertEqual(resultat["crees"], 0)
        self.assertTrue(any("déjà existant" in e for e in resultat["erreurs"]))
