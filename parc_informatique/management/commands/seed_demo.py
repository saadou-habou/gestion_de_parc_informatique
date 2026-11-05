"""Génère des données de démonstration pour le parc informatique."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from parc_informatique.models import (
    Appareil,
    HistoriqueMaintenance,
    Local,
    Notification,
    Technicien,
    Utilisateur,
)
from parc_informatique.notifications import generer_notifications
from parc_informatique.roles import (
    ADMIN,
    GESTIONNAIRE,
    TECHNICIEN as ROLE_TECHNICIEN,
)
from parc_informatique.services.assignments import changer_affectation
from parc_informatique.services.maintenance import (
    ouvrir_maintenance,
    terminer_maintenance,
)


class Command(BaseCommand):
    help = "Génère des données de démonstration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="DemoParc2026!",
            help="Mot de passe des comptes nouvellement créés.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]

        if len(password) < 8:
            self.stderr.write(
                self.style.ERROR("Le mot de passe doit contenir au moins 8 caractères.")
            )
            return

        self.stdout.write("Création des groupes et comptes...")

        groupes = {
            nom: Group.objects.get_or_create(name=nom)[0]
            for nom in (ADMIN, GESTIONNAIRE, ROLE_TECHNICIEN)
        }

        User = get_user_model()

        comptes = [
            ("demo_admin", "admin.demo@parc.local", "Admin", True),
            (
                "demo_gestionnaire",
                "gestionnaire.demo@parc.local",
                GESTIONNAIRE,
                False,
            ),
            (
                "demo_technicien",
                "technicien.demo@parc.local",
                ROLE_TECHNICIEN,
                False,
            ),
        ]

        utilisateurs_comptes = {}

        for username, email, role, is_staff in comptes:
            compte, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "is_staff": is_staff,
                    "is_active": True,
                },
            )

            if created:
                compte.set_password(password)
                compte.save(update_fields=["password"])
            else:
                compte.email = email
                compte.is_active = True

                if is_staff:
                    compte.is_staff = True

                compte.save(update_fields=["email", "is_active", "is_staff"])

            compte.groups.add(groupes[role])
            utilisateurs_comptes[username] = compte

        today = timezone.localdate()

        # --------------------------------------------------
        # LOCAUX
        # --------------------------------------------------

        locaux_data = [
            ("Direction générale", "1er", "Bâtiment A"),
            ("Service informatique", "2e", "Bâtiment A"),
            ("Comptabilité", "1er", "Bâtiment B"),
            ("Salle de formation", "RDC", "Bâtiment C"),
        ]

        locaux = {}

        for nom, etage, batiment in locaux_data:
            local, _ = Local.objects.get_or_create(
                nom=nom,
                etage=etage,
                batiment=batiment,
            )
            locaux[nom] = local

        # --------------------------------------------------
        # UTILISATEURS MÉTIER
        # --------------------------------------------------

        personnes_data = [
            ("Moussa", "Abdou", "moussa.abdou@parc.local", "90000001", "Directeur"),
            ("Aïchatou", "Issa", "aichatou.issa@parc.local", "90000002", "Comptable"),
            (
                "Ibrahim",
                "Mahamadou",
                "ibrahim.mahamadou@parc.local",
                "90000003",
                "Secrétaire",
            ),
            (
                "Fatima",
                "Oumarou",
                "fatima.oumarou@parc.local",
                "90000004",
                "Formatrice",
            ),
            (
                "Aboubacar",
                "Adamou",
                "aboubacar.adamou@parc.local",
                "90000005",
                "Assistant administratif",
            ),
            ("Zara", "Moussa", "zara.moussa@parc.local", "90000006", "Responsable RH"),
        ]

        personnes = {}

        for nom, prenom, email, telephone, poste in personnes_data:
            personne, _ = Utilisateur.objects.update_or_create(
                email=email,
                defaults={
                    "nom": nom,
                    "prenom": prenom,
                    "telephone": telephone,
                    "poste": poste,
                },
            )
            personnes[email] = personne

        # --------------------------------------------------
        # TECHNICIENS
        # --------------------------------------------------

        technicien_data = [
            (
                "Amadou",
                "Garba",
                "amadou.garba@parc.local",
                "91000001",
                "Maintenance matérielle",
                True,
                None,
            ),
            (
                "Hassane",
                "Moussa",
                "hassane.moussa@parc.local",
                "91000002",
                "Réseaux",
                True,
                utilisateurs_comptes["demo_technicien"],
            ),
            (
                "Salifou",
                "Issoufou",
                "salifou.issoufou@parc.local",
                "91000003",
                "Support logiciel",
                True,
                None,
            ),
        ]

        techniciens = {}

        for nom, prenom, email, telephone, specialite, actif, compte in technicien_data:
            technicien, _ = Technicien.objects.update_or_create(
                nom=nom,
                prenom=prenom,
                defaults={
                    "email": email,
                    "telephone": telephone,
                    "specialite": specialite,
                    "actif": actif,
                    "compte_utilisateur": compte,
                },
            )
            techniciens[email] = technicien

        # --------------------------------------------------
        # APPAREILS
        # --------------------------------------------------

        appareils_data = [
            (
                "Ordinateur bureautique DG",
                "Desktop",
                "Dell",
                "OptiPlex 7090",
                "DEMO-PC-001",
                "Disponible",
                2024,
                "Direction générale",
                "moussa.abdou@parc.local",
                450000,
                2027,
                8,
            ),
            (
                "Portable comptabilité",
                "Laptop",
                "HP",
                "ProBook 450 G8",
                "DEMO-PC-002",
                "Disponible",
                2023,
                "Comptabilité",
                "aichatou.issa@parc.local",
                520000,
                2026,
                45,
            ),
            (
                "Portable direction",
                "Laptop",
                "Lenovo",
                "ThinkPad E14",
                "DEMO-PC-003",
                "Disponible",
                2025,
                "Direction générale",
                "ibrahim.mahamadou@parc.local",
                610000,
                2028,
                12,
            ),
            (
                "Poste formation 01",
                "Desktop",
                "HP",
                "ProDesk 400 G6",
                "DEMO-PC-004",
                "Disponible",
                2022,
                "Salle de formation",
                "fatima.oumarou@parc.local",
                390000,
                2025,
                0,
            ),
            (
                "Poste formation 02",
                "Desktop",
                "Dell",
                "Vostro 3681",
                "DEMO-PC-005",
                "Disponible",
                2022,
                "Salle de formation",
                "aboubacar.adamou@parc.local",
                375000,
                2025,
                0,
            ),
            (
                "Imprimante réseau",
                "Périphérique",
                "Brother",
                "MFC-L8900CDW",
                "DEMO-PR-006",
                "Disponible",
                2024,
                "Comptabilité",
                None,
                280000,
                2027,
                20,
            ),
            (
                "Ordinateur support",
                "Desktop",
                "Lenovo",
                "ThinkCentre M720",
                "DEMO-PC-007",
                "En réparation",
                2021,
                "Service informatique",
                None,
                330000,
                2024,
                10,
            ),
            (
                "Portable technicien",
                "Laptop",
                "Dell",
                "Latitude 5420",
                "DEMO-PC-008",
                "Disponible",
                2023,
                "Service informatique",
                None,
                570000,
                2026,
                60,
            ),
            (
                "Scanner administratif",
                "Périphérique",
                "Canon",
                "imageFORMULA DR-C240",
                "DEMO-SC-009",
                "Obsolète",
                2018,
                "Direction générale",
                None,
                190000,
                2021,
                0,
            ),
            (
                "Portable RH",
                "Laptop",
                "Acer",
                "TravelMate P2",
                "DEMO-PC-010",
                "Disponible",
                2024,
                "Direction générale",
                "zara.moussa@parc.local",
                485000,
                2027,
                25,
            ),
            (
                "Écran salle formation",
                "Périphérique",
                "Samsung",
                "S24R350",
                "DEMO-MON-011",
                "Disponible",
                2023,
                "Salle de formation",
                None,
                95000,
                2026,
                75,
            ),
            (
                "Routeur principal",
                "Périphérique",
                "MikroTik",
                "RB4011",
                "DEMO-NET-012",
                "Disponible",
                2024,
                "Service informatique",
                None,
                210000,
                2027,
                90,
            ),
        ]

        appareils = {}

        for (
            nom,
            type_app,
            marque,
            modele,
            serie,
            etat,
            annee,
            local_nom,
            email_personne,
            prix,
            garantie_annee,
            garantie_jours,
        ) in appareils_data:

            acquisition = today.replace(
                year=annee,
                day=min(today.day, 28),
            )

            if garantie_jours:
                garantie = today + timedelta(days=garantie_jours)
            else:
                garantie = today.replace(
                    year=garantie_annee,
                    month=12,
                    day=31,
                )

            appareil, _ = Appareil.objects.update_or_create(
                numero_serie=serie,
                defaults={
                    "nom": nom,
                    "type": type_app,
                    "marque": marque,
                    "modele": modele,
                    "etat": "Disponible" if etat == "En réparation" else etat,
                    "date_acquisition": acquisition,
                    "fournisseur": "Fournitures Informatiques du Sahel",
                    "prix_achat": Decimal(prix),
                    "date_fin_garantie": garantie,
                    "localisation": locaux[local_nom],
                },
            )

            appareils[serie] = appareil

            if email_personne:
                changer_affectation(
                    appareil_id=appareil.pk,
                    utilisateur=personnes[email_personne],
                    date_debut=acquisition,
                )

        # --------------------------------------------------
        # MAINTENANCE OUVERTE
        # --------------------------------------------------

        appareil_reparation = appareils["DEMO-PC-007"]

        description_ouverte = (
            "Diagnostic : démarrage intermittent et contrôle de l'alimentation."
        )

        maintenance_ouverte = HistoriqueMaintenance.objects.filter(
            appareil=appareil_reparation,
            description=description_ouverte,
        ).first()

        if maintenance_ouverte is None:
            ouvrir_maintenance(
                appareil_id=appareil_reparation.pk,
                description=description_ouverte,
                technicien=techniciens["hassane.moussa@parc.local"],
                cout=Decimal("25000.00"),
                date_intervention=today - timedelta(days=8),
            )
        else:
            if maintenance_ouverte.statut == "Réparé":
                maintenance_ouverte.statut = "Non réparé"
                maintenance_ouverte.date_reparation = None
                maintenance_ouverte.save(update_fields=["statut", "date_reparation"])

            appareil_reparation.etat = "En réparation"
            appareil_reparation.save(update_fields=["etat"])

        # --------------------------------------------------
        # MAINTENANCES TERMINÉES
        # --------------------------------------------------

        historiques = [
            (
                "DEMO-PC-002",
                "Remplacement du ventilateur et nettoyage interne.",
                32,
                "amadou.garba@parc.local",
                "45000.00",
            ),
            (
                "DEMO-PC-008",
                "Réinstallation du système et mise à jour des pilotes.",
                18,
                "salifou.issoufou@parc.local",
                "15000.00",
            ),
            (
                "DEMO-PR-006",
                "Débourrage papier et entretien du mécanisme d'impression.",
                12,
                "amadou.garba@parc.local",
                "12000.00",
            ),
        ]

        for serie, description, jours, tech_email, cout in historiques:
            date_intervention = today - timedelta(days=jours)

            maintenance, _ = HistoriqueMaintenance.objects.get_or_create(
                appareil=appareils[serie],
                description=description,
                defaults={
                    "date_intervention": date_intervention,
                    "technicien": techniciens[tech_email],
                    "statut": "Réparé",
                    "date_reparation": date_intervention + timedelta(days=2),
                    "cout": Decimal(cout),
                },
            )

            if maintenance.statut != "Réparé":
                terminer_maintenance(
                    maintenance_id=maintenance.pk,
                    date_reparation=date_intervention + timedelta(days=2),
                )

        # --------------------------------------------------
        # NOTIFICATIONS
        # --------------------------------------------------

        generer_notifications()

        # --------------------------------------------------
        # RÉSUMÉ
        # --------------------------------------------------

        self.stdout.write(
            self.style.SUCCESS("Jeu de données de démonstration créé / synchronisé.")
        )

        self.stdout.write(
            f"Locaux : {Local.objects.filter(nom__in=[x[0] for x in locaux_data]).count()}"
        )
        self.stdout.write(f"Utilisateurs métier : {len(personnes)}")
        self.stdout.write(f"Techniciens : {len(techniciens)}")
        self.stdout.write(f"Appareils : {len(appareils)}")

        self.stdout.write(
            f"Maintenances : "
            f"{HistoriqueMaintenance.objects.filter(appareil__numero_serie__startswith='DEMO-').count()}"
        )

        self.stdout.write(
            f"Notifications actives : "
            f"{Notification.objects.filter(resolue=False).count()}"
        )

        self.stdout.write("\nComptes de démonstration :")

        for username, _email, role, _staff in comptes:
            self.stdout.write(
                f"  - {username} / rôle {role} / mot de passe : {password}"
            )

        self.stdout.write(
            self.style.WARNING(
                "Ces comptes sont réservés au développement. "
                "Ne les utilisez jamais en production."
            )
        )
