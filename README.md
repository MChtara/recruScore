# 🎯 JobMatch Pro - Plateforme de Matching d'Emplois avec ATS

Une plateforme intelligente de recherche d'emploi avec analyse automatique de CV par ATS (Applicant Tracking System), scraping multi-sources, et système de vérification des compétences.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [API Documentation](#-api-documentation)
- [Structure du Projet](#-structure-du-projet)
- [Développement](#-développement)
- [Déploiement](#-déploiement)
- [Sécurité](#-sécurité)
- [Contribution](#-contribution)

---

## ✨ Fonctionnalités

### 🔍 Recherche et Matching
- **Recherche Multi-critères** : Recherche par mot-clé, localisation, type de contrat, entreprise
- **Filtres Avancés** : Filtrage par date, source, type d'emploi
- **Pagination** : Navigation optimisée à travers les résultats

### 🤖 Analyse ATS Intelligente
- **Analyse CV vs Offre** : Scoring automatique de compatibilité (0-100%)
- **Vision Language Model (VLM)** : Vérification automatique des certificats et attestations
- **Extraction Intelligente** : Extraction automatique des compétences techniques
- **Tests Techniques Personnalisés** : Génération de tests adaptés au profil

### 🌐 Web Scraping Multi-sources
- **Google Jobs API** : Scraping via API officielle
- **LinkedIn** : Extraction d'offres sans API (méthode libre)
- **France Travail** : API officielle Pôle Emploi
- **Tunisie Travail** : Scraping du site tunisien

### 📊 Statistiques et Visualisation
- **Dashboard Temps Réel** : Visualisation des tendances du marché
- **Graphiques Interactifs** : Chart.js pour les statistiques
- **Export de Données** : Export CSV des résultats

### 🔐 Sécurité et Vérification
- **Vérification de Documents** : Validation automatique des preuves (PDF/Images)
- **Vision API** : Analyse d'images de certificats
- **Gestion Sécurisée** : Variables d'environnement pour les secrets

---

## 🏗️ Architecture

```
JobMatch Pro
├── Frontend (Bootstrap 5 + Chart.js)
│   ├── Templates Jinja2
│   └── Interface Responsive
│
├── Backend (Flask)
│   ├── Routes REST API
│   ├── Session Management
│   └── File Upload Handling
│
├── Base de Données (SQLite)
│   ├── jobs.db (Offres d'emploi)
│   └── Indexes optimisés
│
├── Services
│   ├── ATS Scorer (Groq AI)
│   ├── Job Scrapers
│   └── VLM Document Verification
│
└── Storage
    ├── user_cvs/ (CVs uploadés)
    ├── user_proofs/ (Preuves/Certificats)
    └── uploads/ (Fichiers temporaires)
```

---

## 📦 Prérequis

### Logiciels Requis
- **Python** : 3.8 ou supérieur
- **pip** : Gestionnaire de paquets Python
- **Git** : Pour le versioning

### Comptes et API Keys
- **Groq API** : Clé API pour l'analyse ATS (gratuit)
  - Inscription : https://console.groq.com/
- **Google Jobs API** *(optionnel)* : Pour le scraping Google Jobs
- **France Travail API** *(optionnel)* : Client ID + Secret

---

## 🚀 Installation

### 1. Cloner le Repository

```bash
git clone https://github.com/MChtara/recruScore.git
cd recruScore
```

### 2. Créer un Environnement Virtuel

**Windows :**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac :**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les Dépendances

```bash
pip install -r requirements.txt
```

**Dépendances Principales :**
- `flask` : Framework web
- `pandas` : Manipulation de données
- `requests` : Requêtes HTTP
- `python-dotenv` : Gestion des variables d'environnement
- `PyPDF2` ou `pdfplumber` : Extraction de texte PDF
- `python-docx` : Lecture de fichiers Word
- `Pillow` : Traitement d'images
- `beautifulsoup4` : Web scraping
- `selenium` *(optionnel)* : Scraping dynamique

---

## ⚙️ Configuration

### 1. Fichier d'Environnement

Créer un fichier `.env` à la racine du projet :

Éditer `.env` et remplir vos clés :

```env
# Groq API Key (OBLIGATOIRE)
ATS_API_KEY=gsk_votre_cle_api_ici
```

### 2. Configuration des Scrapers

Le fichier `job_scraper/config.json` contient la configuration des scrapers :

```json
{
  "scrapers": {
    "google_jobs": {
      "enabled": true,
      "api_key": "",
      "queries": ["développeur python tunisie", "data scientist"],
      "max_results": 200,
      "country": "tn",
      "language": "fr"
    },
    "linkedin": {
      "enabled": true,
      "keywords": ["python", "data science"],
      "location": "Tunisia",
      "pages": 2
    }
  }
}
```

### 3. Initialiser la Base de Données

La base de données SQLite sera créée automatiquement au premier lancement :

```bash
python app.py
```

---

## 💻 Utilisation

### Démarrer l'Application

```bash
python app.py
```

L'application sera accessible sur :
- **Interface Principale** : http://localhost:5000
- **Statistiques** : http://localhost:5000/stats
- **Admin Scraping** : http://localhost:5000/admin/scraping

### Workflow Utilisateur

1. **Upload de CV** :
   - Aller sur "Mon CV"
   - Uploader un fichier PDF/DOCX

2. **Recherche d'Emplois** :
   - Utiliser la barre de recherche
   - Appliquer des filtres

3. **Analyse ATS** :
   - Cliquer sur une offre
   - L'analyse se fait automatiquement si un CV est uploadé

4. **Vérification de Compétences** :
   - Aller sur "Tests Techniques"
   - Sélectionner une compétence
   - Passer le test généré

### Workflow Admin

1. **Configuration du Scraping** :
   - Aller sur `/admin/scraping`
   - Configurer les sources

2. **Lancer le Scraping** :
   - Cliquer sur "Scraper" pour une source
   - Suivre la progression en temps réel

3. **Exporter les Données** :
   - Utiliser le bouton "Export CSV"

---

## 📡 API Documentation

### Endpoints Principaux

#### Recherche d'Emplois
```http
GET /api/search?keyword=python&location=tunis&page=1
```

**Réponse :**
```json
{
  "jobs": [...],
  "stats": {
    "total_jobs": 150,
    "total_pages": 8,
    "current_page": 1
  }
}
```

#### Upload de CV
```http
POST /upload-cv
Content-Type: multipart/form-data

cv_file: <file>
```

**Réponse :**
```json
{
  "success": true,
  "message": "CV uploadé avec succès",
  "filename": "mon_cv.pdf"
}
```

#### Analyse ATS
```http
GET /job/<job_id>
```

Retourne l'analyse automatique si un CV est uploadé.

#### Scraping Status
```http
GET /api/scraping/status
```

**Réponse :**
```json
{
  "is_running": true,
  "current_source": "linkedin",
  "sources_status": {...}
}
```

---

## 📁 Structure du Projet

```
CV/
├── app.py                          # Application Flask principale
├── ats_scorer.py                   # Module d'analyse ATS
├── .env                            # Variables d'environnement (non versionné)
├── .env.example                    # Template des variables
├── requirements.txt                # Dépendances Python
├── jobs.db                         # Base de données SQLite
│
├── job_scraper/                    # Modules de scraping
│   ├── db_manager.py              # Gestionnaire de base de données
│   ├── google_jobs.py             # Scraper Google Jobs
│   ├── Linkedin.py                # Scraper LinkedIn
│   ├── france_travail.py          # API France Travail
│   ├── tunisietravail.py          # Scraper Tunisie Travail
│   └── config.json                # Configuration des scrapers
│
├── templates/                      # Templates HTML (Jinja2)
│   ├── base.html                  # Template de base
│   ├── index.html                 # Page d'accueil / Recherche
│   ├── job_detail.html            # Détail d'une offre + ATS
│   ├── stats.html                 # Dashboard statistiques
│   ├── upload_cv_page.html        # Gestion du CV
│   ├── verify_credentials.html    # Vérification des certificats
│   ├── technical_tests.html       # Tests techniques
│   └── admin_scraping.html        # Administration du scraping
│
├── static/                         # Fichiers statiques
│   ├── css/
│   └── js/
│       ├── main.js
│       └── app.js
│
├── user_cvs/                       # CVs uploadés (non versionné)
├── user_proofs/                    # Preuves/Certificats (non versionné)
└── uploads/                        # Fichiers temporaires (non versionné)
```

---

## 🛠️ Développement

### Installation en Mode Développement

```bash
# Activer le mode debug dans .env
FLASK_DEBUG=True

# Lancer avec rechargement automatique
python app.py
```

### Ajouter un Nouveau Scraper

1. Créer un fichier dans `job_scraper/` :

```python
# job_scraper/nouveau_scraper.py

def scrape_nouveau_site(keyword: str, location: str):
    """Scraper pour un nouveau site"""
    jobs = []

    # Logique de scraping ici
    # ...

    return jobs  # Liste de dictionnaires
```

2. Format de retour :

```python
job = {
    'title': 'Titre du poste',
    'company': 'Nom entreprise',
    'location': 'Ville, Pays',
    'description': 'Description complète',
    'job_url': 'https://...',
    'date': '2025-01-15',
    'job_type': 'CDI/CDD/Stage',
    'salary': '50000 EUR/an',
    'contrat': 'CDI'
}
```

3. Ajouter dans `config.json` :

```json
"nouveau_scraper": {
  "enabled": true,
  "param1": "valeur"
}
```

4. Intégrer dans `app.py` :

```python
elif source_name == 'nouveau_scraper':
    from nouveau_scraper import scrape_nouveau_site
    jobs = scrape_nouveau_site(...)
```

### Tests

```bash
# Tester le gestionnaire de base de données
python job_scraper/db_manager.py

# Tester l'ATS Scorer
python ats_scorer.py

# Tester un scraper spécifique
python job_scraper/linkedin.py
```

---

## 🚀 Déploiement

### Déploiement sur un VPS (Ubuntu/Debian)

```bash
# 1. Installer les dépendances système
sudo apt update
sudo apt install python3-pip python3-venv nginx

# 2. Cloner le projet
git clone <repo_url>
cd recruScore

# 3. Configuration
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# 4. Créer le fichier .env en production
cp .env.example .env
nano .env  # Éditer avec vos clés

# 5. Lancer avec Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Configuration Nginx

```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /chemin/vers/recruScore/static;
    }
}
```

### Service Systemd

Créer `/etc/systemd/system/jobmatch.service` :

```ini
[Unit]
Description=JobMatch Pro Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/chemin/vers/recruScore
Environment="PATH=/chemin/vers/recruScore/venv/bin"
ExecStart=/chemin/vers/recruScore/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start jobmatch
sudo systemctl enable jobmatch
```

---

## 🔒 Sécurité

### Bonnes Pratiques Implémentées

✅ **Variables d'Environnement** : Toutes les clés API sont dans `.env`
✅ **Gitignore** : Fichiers sensibles exclus du versioning
✅ **Validation des Fichiers** : Vérification des extensions uploadées
✅ **Session Management** : Sessions Flask sécurisées
✅ **SQL Injection Protection** : Requêtes paramétrées (SQLite)

### Recommandations de Production

⚠️ **Changez la SECRET_KEY** dans `.env`
⚠️ **Désactivez FLASK_DEBUG** en production
⚠️ **Utilisez HTTPS** (Let's Encrypt)
⚠️ **Limitez les uploads** (taille de fichier)
⚠️ **Backup régulier** de `jobs.db`
⚠️ **Rate Limiting** sur les API endpoints

### Révocation des Clés API

Si une clé API est compromise :

1. **Groq API** : https://console.groq.com/keys → Supprimer la clé
2. **Générer une nouvelle clé**
3. **Mettre à jour `.env`**
4. **Redémarrer l'application**

---

## 🤝 Contribution

### Workflow Git

```bash
# 1. Créer une branche feature
git checkout -b feature/nouvelle-fonctionnalite

# 2. Faire vos modifications
git add .
git commit -m "feat: Description de la fonctionnalité"

# 3. Pousser et créer une Pull Request
git push origin feature/nouvelle-fonctionnalite
```

### Convention de Commits

- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `docs:` Documentation
- `style:` Formatage (pas de changement de code)
- `refactor:` Refactorisation
- `test:` Ajout de tests
- `chore:` Maintenance

### Code Review Checklist

- [ ] Le code suit les conventions Python (PEP 8)
- [ ] Les secrets ne sont pas commitées
- [ ] Les fonctions ont des docstrings
- [ ] Les imports sont organisés
- [ ] Les erreurs sont gérées (try/except)
- [ ] Les logs sont informatifs

---

## 📝 License

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 👥 Équipe de Développement

**Maintainers :**
- [@MChtara](https://github.com/MChtara) - Lead Developer

**Contributors :**
- Voir [CONTRIBUTORS.md](CONTRIBUTORS.md)

---

## 📞 Support

**Issues** : [GitHub Issues](https://github.com/MChtara/recruScore/issues)
**Documentation** : [Wiki](https://github.com/MChtara/recruScore/wiki)
**Email** : support@jobmatchpro.com

---

## 🗺️ Roadmap

### Version 1.1 (Q1 2025)
- [ ] Authentification utilisateur (Login/Register)
- [ ] Sauvegarde des recherches favorites
- [ ] Notifications par email
- [ ] Dashboard candidat amélioré

### Version 1.2 (Q2 2025)
- [ ] API REST complète avec documentation Swagger
- [ ] Intégration de nouveaux scrapers (Indeed, Monster)
- [ ] Analyse de CV par IA améliorée
- [ ] Recommandations personnalisées

### Version 2.0 (Q3 2025)
- [ ] Application mobile (React Native)
- [ ] Mode multi-tenants (entreprises)
- [ ] Analytics avancés
- [ ] Intégration avec calendriers (entretiens)

---

## 📊 Statistiques du Projet

- **Lignes de Code** : ~3,500
- **Modules Python** : 8
- **Templates HTML** : 11
- **Sources de Scraping** : 4
- **API Endpoints** : 15+

---

## 🙏 Remerciements

- **Groq AI** : Pour l'API d'analyse ATS
- **Bootstrap** : Framework CSS
- **Chart.js** : Bibliothèque de graphiques
- **Flask** : Framework web Python
- **SQLite** : Base de données légère

---

**Fait avec ❤️ par l'équipe JobMatch Pro**
