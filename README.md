# Gestion de Parc Informatique

Ce projet est une application web développée avec Django pour gérer un parc informatique. Il permet de suivre les appareils, leur localisation, leur état, ainsi que leur historique de maintenance.

## Fonctionnalités

- **Gestion des appareils** :

  - Ajouter, modifier et supprimer des appareils.
  - Associer un appareil à une localisation et à un utilisateur.
  - Suivre l'état des appareils (disponible, en réparation, obsolète).

- **Historique de maintenance** :

  - Suivi des interventions sur les appareils.
  - Ajout de maintenances avec des détails comme la description, le technicien responsable, et le statut (réparé ou non).

- **Localisation des appareils** :

  - Permet d'assigner un appareil à un local spécifique.

## Prérequis

Avant de commencer, assurez-vous d'avoir les outils suivants installés sur votre machine :

- Python 3.9 ou plus
- Django (installé via pip)
- Git

## Installation

1. Clonez le dépôt sur votre machine locale :

   ```bash
   git clone https://github.com/saadou-habou/gestion_de_parc_informatique.git
   ```

2. Accédez au dossier du projet :

   ```bash
   cd gestion_de_parc_informatique
   ```

3. Créez et activez un environnement virtuel Python :

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Sur Windows : venv\Scripts\activate
   ```

# Gestion de Parc Informatique

Ce projet est une application web développée avec Django pour gérer un parc informatique. Il permet de suivre les appareils, leur localisation, leur état, ainsi que leur historique de maintenance.

## Fonctionnalités

- **Gestion des appareils** :

- Ajouter, modifier et supprimer des appareils.
- Associer un appareil à une localisation et à un utilisateur.
- Suivre l'état des appareils (disponible, en réparation, obsolète).

- **Historique de maintenance** :

  - Suivi des interventions sur les appareils.
  - Ajout de maintenances avec des détails comme la description, le technicien responsable, et le statut (réparé ou non).

- **Localisation des appareils** :

  - Permet d'assigner un appareil à un local spécifique.

## Prérequis

Avant de commencer, assurez-vous d'avoir les outils suivants installés sur votre machine :

- Python 3.9 ou plus
- Django (installé via pip)
- Git

## Installation

1. Clonez le dépôt sur votre machine locale :

    ```bash
    git clone https://github.com/saadou-habou/gestion_de_parc_informatique.git
    ```

2. Accédez au dossier du projet :

    ```bash
    cd gestion_de_parc_informatique
    ```

3. Créez et activez un environnement virtuel Python :

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Sur Windows : venv\Scripts\activate
    ```

4. Installez les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

5. Appliquez les migrations pour configurer la base de données :

   ```bash
   python manage.py migrate
   ```

6. Créez un superutilisateur pour accéder à l'interface d'administration :

   ```bash
   python manage.py createsuperuser
   ```

7. Lancez le serveur de développement :

   ```bash
   python manage.py runserver
   ```

8. Accédez à l'application dans votre navigateur à l'adresse suivante :
   [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Structure du Projet

- **appareils/** : Gestion des appareils.
- **historique_maintenance/** : Gestion des historiques de maintenance.
- **templates/** : Dossiers des templates HTML.
- **static/** : Fichiers statiques comme CSS, JavaScript, et images.
- **parc_informatique/** : Application principale du projet.

## Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le projet.
2. Créez une branche pour votre fonctionnalité :

   ```bash
   git checkout -b nouvelle-fonctionnalite
   ```

3. Faites vos modifications et validez-les :

   ```bash
   git commit -m "Ajout d'une nouvelle fonctionnalité"
   ```

4. Poussez votre branche :

   ```bash
   git push origin nouvelle-fonctionnalite
   ```

5. Créez une Pull Request sur le dépôt principal.

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

**Auteur** : Artilleur
