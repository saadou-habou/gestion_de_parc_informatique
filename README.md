# Gestion de Parc Informatique

[![CI](https://github.com/saadou-habou/gestion_de_parc_informatique/actions/workflows/django-ci.yml/badge.svg)](https://github.com/saadou-habou/gestion_de_parc_informatique/actions/workflows/django-ci.yml)

Application web développée avec **Django** permettant de gérer un parc informatique.
Elle couvre le suivi des appareils, leur affectation, leur localisation, leur état, leur
historique de maintenance, ainsi que l'authentification, les rôles utilisateurs, les
notifications automatiques et une API REST sécurisée par JWT.

## Fonctionnalités

### Gestion des appareils
* Ajouter, modifier et supprimer des appareils.
* Associer un appareil à un utilisateur et une localisation.
* Suivre l'état des appareils : Disponible, En réparation, Obsolète.
* Fournisseur, prix d'achat et date de fin de garantie (alerte automatique en cas
  d'expiration proche ou dépassée).
* QR code généré à la volée pour chaque appareil (ouvre sa fiche depuis un mobile).
* Export CSV de l'inventaire et import CSV en masse.
* Recherche instantanée, filtres par statut, pagination.

### Gestion des affectations
* Affecter un appareil à un utilisateur (ou le désaffecter).
* Historique complet des affectations passées et en cours (`HistoriqueAffectation`),
  pas seulement l'affectation actuelle.

### Historique de maintenance
* Enregistrer les interventions : description, technicien, statut, coût.
* Clôturer une intervention ("Terminer") : remet automatiquement l'appareil
  "Disponible" s'il n'a plus d'autre maintenance ouverte.
* Techniciens gérés comme une véritable entité (CRUD dédié), avec possibilité de les
  relier à un compte de connexion pour un accès "Mes interventions" personnel.
* Export CSV de l'historique de maintenance.

### Localisation & utilisateurs
* CRUD complet pour les locaux et pour les utilisateurs (auparavant gérables
  uniquement depuis `/admin/`).
* Recherche des équipements par emplacement.

### Authentification & rôles
* Connexion / déconnexion, changement de mot de passe, mot de passe oublié
  (email de réinitialisation).
* Trois rôles (**Admin**, **Gestionnaire**, **Technicien**) basés sur les groupes
  Django natifs, avec des permissions différenciées :

  | Action | Admin | Gestionnaire | Technicien |
  |---|:---:|:---:|:---:|
  | Consulter (dashboard, appareils, utilisateurs, maintenances…) | ✅ | ✅ | ✅ |
  | Ajouter / modifier un appareil, affecter à un utilisateur | ✅ | ✅ | ❌ |
  | Supprimer un appareil ou un technicien | ✅ | ❌ | ❌ |
  | Envoyer en maintenance / terminer une maintenance | ✅ | ✅ | ✅ |

* Journal d'audit des actions sensibles (création, modification, suppression,
  changement d'affectation…), consultable par les administrateurs.

### Notifications
* Générées automatiquement à partir de règles métier (idempotentes, sans doublon) :
  maintenance non résolue depuis plusieurs jours, appareil obsolète, garantie
  bientôt expirée ou expirée.
* Cloche de notification dans la navbar avec compteur de non-lus.

### Statistiques
* Durée moyenne de réparation, coût total de maintenance, appareils les plus
  coûteux à entretenir, répartition du parc par type, garanties expirées.

### API REST (JWT)
* API sécurisée par jeton JWT (`djangorestframework-simplejwt`), pensée pour un
  client externe (application mobile, frontend séparé) indépendant du site Django.
* Ressources : appareils, locaux, utilisateurs, techniciens, maintenances,
  affectations — avec les mêmes règles de rôle que le site.
* Documentation interactive (Swagger) une fois le serveur lancé :
  `http://127.0.0.1:8000/api/v1/docs/`

---

## Technologies utilisées

* **Python** / **Django**
* **Django REST Framework** + **djangorestframework-simplejwt** (API JWT)
* **drf-spectacular** (documentation OpenAPI / Swagger)
* **SQLite** (base de données par défaut)
* **Bootstrap 5**, **Font Awesome**, **Chart.js**, **SweetAlert2** (interface)
* **qrcode** (génération de QR codes)
* **uv** (gestionnaire d'environnement et de dépendances)
* **flake8** (analyse du code)
* Tests via le framework de test intégré de Django (`manage.py test`)

---

## Prérequis

Avant de commencer, installez :
* Python 3.10 ou supérieur
* Git
* uv

Installation de uv :
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/saadou-habou/gestion_de_parc_informatique.git
```

### 2. Accéder au projet
```bash
cd gestion_de_parc_informatique
```

### 3. Installer les dépendances
Créer l'environnement virtuel et installer les dépendances (y compris les
dépendances de développement comme flake8) :
```bash
uv sync --group dev
```

### 4. Activer l'environnement virtuel (optionnel)
Linux/macOS :
```bash
source .venv/bin/activate
```
Windows :
```bash
.venv\Scripts\activate
```

---

## Configuration

### Email (mot de passe oublié)
En développement, les emails de réinitialisation de mot de passe s'affichent
simplement dans le terminal (`EMAIL_BACKEND` console, déjà configuré dans
`settings.py`). En production, configurez un vrai backend SMTP
(`EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, etc.).

### Clé secrète
`SECRET_KEY` est définie en clair dans `settings.py` pour le développement local.
**Avant tout déploiement en production**, remplacez-la par une variable
d'environnement et changez `DEBUG = False`.

---

## Configuration de la base de données

Appliquer les migrations :
```bash
uv run python manage.py migrate
```

Créer un compte administrateur :
```bash
uv run python manage.py createsuperuser
```

Créer les groupes de rôles (Admin, Gestionnaire, Technicien) :
```bash
uv run python manage.py setup_roles
```
Assignez ensuite un rôle à chaque utilisateur depuis `/admin/` (Utilisateurs →
modifier → section Permissions → Groups). Un compte `createsuperuser` a accès à
tout, quel que soit son groupe.

---

## Lancer l'application

Démarrer le serveur Django :
```bash
uv run python manage.py runserver
```

L'application est disponible à :
```
http://127.0.0.1:8000
```

La documentation interactive de l'API est disponible à :
```
http://127.0.0.1:8000/api/v1/docs/
```

---

## Tests

Lancer les tests :
```bash
uv run python manage.py test parc_informatique
```

---

## Vérification du code

Lancer l'analyse avec flake8 :
```bash
uv run flake8 .
```

---

## Intégration continue

Chaque push et pull request vers `master` déclenche une CI GitHub Actions
(`.github/workflows/django-ci.yml`) qui installe les dépendances avec `uv`,
exécute flake8, vérifie qu'aucune migration n'est manquante, puis lance les tests.

---

## Structure du projet

```text
gestion_de_parc_informatique/
│
├── .github/
│   └── workflows/
│       └── django-ci.yml      # Lint + tests automatiques (uv)
│
├── gestion_parc/               # Configuration principale Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── parc_informatique/          # Application principale
│   ├── models.py                # Appareil, Utilisateur, Local, Technicien,
│   │                             # HistoriqueMaintenance, HistoriqueAffectation,
│   │                             # Notification, JournalAudit
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   ├── middleware.py             # Connexion obligatoire (hors API et login)
│   ├── roles.py                  # Logique de rôles, partagée site + API
│   ├── decorators.py             # @role_required
│   ├── context_processors.py     # Rôles + notifications dans les templates
│   ├── notifications.py          # Génération des alertes (règles métier)
│   ├── audit.py                  # Journalisation des actions sensibles
│   ├── tests.py
│   ├── management/commands/      # setup_roles, generer_notifications,
│   │                              # backfill_affectations
│   ├── api/                      # API REST JWT (DRF + SimpleJWT)
│   │   ├── serializers.py
│   │   ├── permissions.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── migrations/
│   ├── templates/
│   └── static/
│
├── manage.py                   # Commandes Django
├── pyproject.toml              # Configuration du projet et dépendances
├── uv.lock                     # Verrouillage des versions
├── README.md
└── LICENSE
```

---

## Contribution

Les contributions sont les bienvenues.

Pour contribuer :

1. Forker le projet.
2. Créer une branche :
```bash
git checkout -b nouvelle-fonctionnalite
```
3. Effectuer les modifications.
4. Vérifier que les tests et le lint passent :
```bash
uv run python manage.py test parc_informatique
uv run flake8 .
```
5. Créer un commit :
```bash
git commit -m "Ajout d'une nouvelle fonctionnalité"
```
6. Envoyer la branche :
```bash
git push origin nouvelle-fonctionnalite
```
7. Créer une Pull Request.

---

## Licence

Ce projet est distribué sous licence MIT.
Voir le fichier [LICENSE](LICENSE) pour plus d'informations.

---

**Auteur :** Saadou Habou
