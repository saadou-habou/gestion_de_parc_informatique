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
    Notification,
    Technicien,
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


class TechnicienCompteConnexionTests(TestCase):
    """Option B : créer le compte de connexion depuis le formulaire technicien."""

    DONNEES_BASE = {
        "nom": "Durand",
        "prenom": "Marc",
        "email": "marc@exemple.test",
        "telephone": "",
        "specialite": "Réseau",
        "actif": "on",
    }

    def setUp(self):
        creer_utilisateur_avec_role("bob_gestionnaire", GESTIONNAIRE)
        self.client.login(username="bob_gestionnaire", password="motdepasse123")
        self.url_ajout = reverse("parc_informatique:ajouter_technicien")

    def _poster(self, **extra):
        donnees = dict(self.DONNEES_BASE)
        donnees.update(extra)
        return self.client.post(self.url_ajout, donnees)

    def test_creation_avec_compte_cree_user_groupe_et_lien(self):
        reponse = self._poster(
            creer_compte="on", identifiant="m.durand", mot_de_passe="Zx9!kLm_42qW"
        )
        self.assertEqual(reponse.status_code, 302)

        technicien = Technicien.objects.get(nom="Durand")
        utilisateur = User.objects.get(username="m.durand")
        self.assertEqual(technicien.compte_utilisateur, utilisateur)
        self.assertTrue(utilisateur.groups.filter(name=TECHNICIEN).exists())
        # Uniquement le rôle Technicien : jamais plus que ça.
        self.assertEqual(utilisateur.groups.count(), 1)
        self.assertFalse(utilisateur.is_superuser)
        # Le mot de passe est stocké haché, pas en clair.
        self.assertNotEqual(utilisateur.password, "Zx9!kLm_42qW")
        self.assertTrue(utilisateur.check_password("Zx9!kLm_42qW"))

    def test_le_technicien_peut_ensuite_se_connecter_et_voir_ses_interventions(self):
        self._poster(creer_compte="on", identifiant="m.durand", mot_de_passe="Zx9!kLm_42qW")

        autre_client = self.client_class()
        self.assertTrue(autre_client.login(username="m.durand", password="Zx9!kLm_42qW"))
        reponse = autre_client.get(reverse("parc_informatique:mes_interventions"))
        self.assertEqual(reponse.status_code, 200)

    def test_sans_case_cochee_aucun_compte_cree(self):
        # Même si identifiant/mot de passe sont envoyés, la case décide.
        self._poster(identifiant="fantome", mot_de_passe="Zx9!kLm_42qW")
        self.assertTrue(Technicien.objects.filter(nom="Durand").exists())
        self.assertFalse(User.objects.filter(username="fantome").exists())

    def test_identifiant_deja_pris_refuse_sans_casse(self):
        User.objects.create_user("Marc", password="Autre!mdp_77xY")
        reponse = self._poster(creer_compte="on", identifiant="marc", mot_de_passe="Zx9!kLm_42qW")
        self.assertEqual(reponse.status_code, 200)  # formulaire ré-affiché avec erreur
        self.assertContains(reponse, "déjà utilisé")
        self.assertFalse(Technicien.objects.filter(nom="Durand").exists())

    def test_mot_de_passe_trop_faible_refuse(self):
        reponse = self._poster(creer_compte="on", identifiant="m.durand", mot_de_passe="1234")
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(User.objects.filter(username="m.durand").exists())
        # Rien n'est créé à moitié : ni compte, ni fiche.
        self.assertFalse(Technicien.objects.filter(nom="Durand").exists())

    def test_identifiant_et_mot_de_passe_obligatoires_si_case_cochee(self):
        reponse = self._poster(creer_compte="on")
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Obligatoire pour créer un compte")
        self.assertFalse(Technicien.objects.filter(nom="Durand").exists())

    def test_compte_existant_et_creation_simultanes_refuses(self):
        existant = User.objects.create_user("existant", password="Autre!mdp_77xY")
        reponse = self._poster(
            compte_utilisateur=existant.pk,
            creer_compte="on", identifiant="m.durand", mot_de_passe="Zx9!kLm_42qW",
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "pas les deux")
        self.assertFalse(User.objects.filter(username="m.durand").exists())

    def test_technicien_deja_relie_ne_propose_plus_la_creation(self):
        utilisateur = User.objects.create_user("deja.lie", password="Autre!mdp_77xY")
        technicien = Technicien.objects.create(nom="Petit", prenom="Julie", compte_utilisateur=utilisateur)
        reponse = self.client.get(
            reverse("parc_informatique:modifier_technicien", args=[technicien.id])
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, 'id="id_identifiant"')
        self.assertContains(reponse, "deja.lie")

    def test_creation_de_compte_sur_technicien_existant_via_modification(self):
        technicien = Technicien.objects.create(nom="Petit", prenom="Julie")
        reponse = self.client.post(
            reverse("parc_informatique:modifier_technicien", args=[technicien.id]),
            {
                "nom": "Petit", "prenom": "Julie", "email": "", "telephone": "",
                "specialite": "", "actif": "on",
                "creer_compte": "on", "identifiant": "j.petit", "mot_de_passe": "Zx9!kLm_42qW",
            },
        )
        self.assertEqual(reponse.status_code, 302)
        technicien.refresh_from_db()
        self.assertEqual(technicien.compte_utilisateur.username, "j.petit")

    def test_audit_mentionne_le_compte_mais_jamais_le_mot_de_passe(self):
        from parc_informatique.models import JournalAudit

        self._poster(creer_compte="on", identifiant="m.durand", mot_de_passe="Zx9!kLm_42qW")
        entree = JournalAudit.objects.filter(modele="Technicien", action="creation").first()
        self.assertIn("m.durand", entree.details)
        self.assertNotIn("Zx9!kLm_42qW", entree.details)

    def test_un_technicien_ne_peut_pas_creer_de_comptes(self):
        creer_utilisateur_avec_role("eve_technicien", TECHNICIEN)
        autre_client = self.client_class()
        autre_client.login(username="eve_technicien", password="motdepasse123")
        reponse = autre_client.post(
            self.url_ajout,
            {**self.DONNEES_BASE, "creer_compte": "on",
             "identifiant": "intrus", "mot_de_passe": "Zx9!kLm_42qW"},
        )
        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(User.objects.filter(username="intrus").exists())


class MotDePasseOublieTests(TestCase):
    """Le parcours "mot de passe oublié" doit être accessible SANS être connecté
    (sinon il est inutilisable : régression corrigée dans middleware.py)."""

    def test_pages_publiques_accessibles_sans_connexion(self):
        for nom in ("password_reset", "password_reset_done", "password_reset_complete"):
            reponse = self.client.get(reverse(f"parc_informatique:{nom}"))
            self.assertEqual(reponse.status_code, 200, nom)

    def test_lien_invalide_affiche_la_page_sans_rediriger_vers_login(self):
        url = reverse("parc_informatique:password_reset_confirm", args=["abc", "def"])
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "n'est plus valide")

    def test_les_autres_pages_restent_protegees(self):
        for nom in ("index", "dashboard", "statistiques", "liste_techniciens"):
            reponse = self.client.get(reverse(f"parc_informatique:{nom}"))
            self.assertEqual(reponse.status_code, 302, nom)
            self.assertIn("login", reponse.url)

    def test_parcours_complet_de_reinitialisation(self):
        import re
        from django.core import mail

        User.objects.create_user("oublieux", email="o@exemple.test", password="Ancien!mdp_55zZ")

        reponse = self.client.post(
            reverse("parc_informatique:password_reset"), {"email": "o@exemple.test"}
        )
        self.assertRedirects(
            reponse, reverse("parc_informatique:password_reset_done"), fetch_redirect_response=False
        )
        self.assertEqual(len(mail.outbox), 1)

        lien = re.search(r"https?://[^/]+(/\S+)", mail.outbox[0].body).group(1)
        reponse = self.client.get(lien, follow=True)  # Django redirige vers l'URL "set-password"
        self.assertEqual(reponse.status_code, 200)

        reponse = self.client.post(
            reponse.request["PATH_INFO"],
            {"new_password1": "Nouveau!mdp_88kK", "new_password2": "Nouveau!mdp_88kK"},
        )
        self.assertRedirects(
            reponse, reverse("parc_informatique:password_reset_complete"), fetch_redirect_response=False
        )
        self.assertTrue(self.client_class().login(username="oublieux", password="Nouveau!mdp_88kK"))


class ApiPermissionsParRoleTests(TestCase):
    """L'API doit appliquer les mêmes règles que le site (voir api/permissions.py)."""

    def _client(self, role):
        from rest_framework.test import APIClient

        user = creer_utilisateur_avec_role(f"api_{role.lower()}", role)
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_gestionnaire_ne_peut_supprimer_aucune_ressource_via_api(self):
        from parc_informatique.models import Local, Utilisateur

        client = self._client(GESTIONNAIRE)
        cibles = {
            "appareils": creer_appareil(),
            "techniciens": Technicien.objects.create(nom="T"),
            "utilisateurs": Utilisateur.objects.create(nom="N", prenom="P", email="n@x.test"),
            "locaux": Local.objects.create(nom="L"),
        }
        for ressource, objet in cibles.items():
            reponse = client.delete(f"/api/v1/{ressource}/{objet.pk}/")
            self.assertEqual(reponse.status_code, 403, ressource)
            self.assertTrue(type(objet).objects.filter(pk=objet.pk).exists(), ressource)

    def test_admin_peut_supprimer_via_api(self):
        reponse = self._client(ADMIN).delete(f"/api/v1/appareils/{creer_appareil().pk}/")
        self.assertEqual(reponse.status_code, 204)

    def test_gestionnaire_peut_creer_un_appareil_via_api(self):
        reponse = self._client(GESTIONNAIRE).post(
            "/api/v1/appareils/",
            {"nom": "PC-API", "type": "Desktop", "numero_serie": "API-1", "etat": "Disponible"},
            format="json",
        )
        self.assertEqual(reponse.status_code, 201)

    def test_technicien_ne_peut_ni_creer_ni_supprimer_un_appareil_via_api(self):
        client = self._client(TECHNICIEN)
        reponse = client.post(
            "/api/v1/appareils/",
            {"nom": "PC-API", "type": "Desktop", "numero_serie": "API-2"},
            format="json",
        )
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(client.delete(f"/api/v1/appareils/{creer_appareil().pk}/").status_code, 403)

    def test_technicien_peut_creer_une_maintenance_via_api(self):
        appareil = creer_appareil()
        reponse = self._client(TECHNICIEN).post(
            "/api/v1/maintenances/",
            {"appareil": appareil.pk, "description": "Panne écran", "statut": "Non réparé"},
            format="json",
        )
        self.assertEqual(reponse.status_code, 201)
        appareil.refresh_from_db()
        self.assertEqual(appareil.etat, "En réparation")

    def test_sans_role_aucun_acces_api(self):
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(User.objects.create_user("sans_role", password="x"))
        self.assertEqual(client.get("/api/v1/appareils/").status_code, 403)

    def test_anonyme_refuse_sur_api(self):
        from rest_framework.test import APIClient

        self.assertEqual(APIClient().get("/api/v1/appareils/").status_code, 401)
