# Gestion de Parc Informatique

Application web développée avec **Django** permettant de gérer un parc informatique.
Elle facilite le suivi des appareils, leur affectation, leur localisation, leur état ainsi que leur historique de maintenance.

## Fonctionnalités

### Gestion des appareils

* Ajouter, modifier et supprimer des appareils.
* Associer un appareil à un utilisateur et une localisation.
* Suivre l'état des appareils :

  * Disponible
  * En maintenance
  * Obsolète

### Gestion des affectations

* Affecter un appareil à un utilisateur.
* Consulter l'historique des affectations.
* Suivre les changements d'utilisateur ou de localisation.

### Historique de maintenance

* Enregistrer les interventions effectuées sur les appareils.
* Ajouter des informations de maintenance :

  * Description de l'intervention.
  * Technicien responsable.
  * Statut de réparation.

### Localisation

* Associer les appareils à des locaux spécifiques.
* Faciliter la recherche des équipements par emplacement.

---

## Technologies utilisées

* **Python**
* **Django**
* **SQLite** (base de données par défaut)
* **HTML / CSS / JavaScript**
* **uv** (gestionnaire d'environnement et de dépendances)
* **pytest** (tests)
* **flake8** (analyse du code)

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

Créer l'environnement virtuel et installer les dépendances :

```bash
uv sync
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

## Configuration de la base de données

Appliquer les migrations :

```bash
uv run python manage.py migrate
```

Créer un compte administrateur :

```bash
uv run python manage.py createsuperuser
```

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

---

## Tests

Lancer les tests :

```bash
uv run pytest
```

---

## Vérification du code

Lancer l'analyse avec flake8 :

```bash
uv run flake8 .
```

---

## Structure du projet

```text
gestion_de_parc_informatique/
│
├── gestion_parc/              # Configuration principale Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── parc_informatique/         # Application principale
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── templates/
│   └── static/
│
├── manage.py                  # Commandes Django
├── pyproject.toml             # Configuration du projet et dépendances
├── uv.lock                    # Verrouillage des versions
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

4. Créer un commit :

```bash
git commit -m "Ajout d'une nouvelle fonctionnalité"
```

5. Envoyer la branche :

```bash
git push origin nouvelle-fonctionnalite
```

6. Créer une Pull Request.

---

## Licence

Ce projet est distribué sous licence MIT.
Voir le fichier [LICENSE](LICENSE) pour plus d'informations.

---

**Auteur :** Saadou Habou
