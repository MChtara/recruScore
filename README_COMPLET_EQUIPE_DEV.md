# 🎯 JobMatch Pro - Documentation Technique Complète

**Plateforme de Matching d'Emplois avec ATS Intelligent**

Version: 2.0 | Date: 2025-11-13 | Équipe: Développement & Intégration

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#-vue-densemble)
2. [Architecture du Projet](#-architecture-du-projet)
3. [Structure des Fichiers](#-structure-des-fichiers---utilité-détaillée)
4. [Technologies Utilisées](#-technologies-utilisées)
5. [Installation](#-installation)
6. [Configuration](#-configuration)
7. [Workflows Principaux](#-workflows-principaux)
8. [API et Endpoints](#-api-et-endpoints)
9. [Base de Données](#-base-de-données)
10. [Déploiement](#-déploiement)
11. [Maintenance](#-maintenance)

---

## 🎯 Vue d'Ensemble

### Fonctionnalités Principales

**JobMatch Pro** est une plateforme complète qui combine:

1. **Scraping Multi-Sources** d'offres d'emploi (Google Jobs, LinkedIn, Pôle Emploi, Tunisie Travail)
2. **Analyse ATS** (Applicant Tracking System) avec IA pour matcher CV ↔ Offres
3. **Recommandation de Cours Coursera** via recherche vectorielle (ChromaDB)
4. **Génération de Tests Techniques** personnalisés basés sur le CV
5. **Vérification de Documents** (certificats, attestations) via Vision AI
6. **Dashboard Statistiques** temps réel avec visualisations

### Points Forts

- ✅ **16,416 cours Coursera** pré-scrapés avec embeddings vectoriels
- ✅ **Recherche 10x plus rapide** grâce à ChromaDB (< 1 seconde)
- ✅ **Analyse automatique** du CV dès l'upload
- ✅ **Multi-sources** de scraping avec déduplication intelligente
- ✅ **Vision AI** pour vérification automatique des preuves

---

## 🏗️ Architecture du Projet

```
┌────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Bootstrap 5)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Templates Jinja2 + Chart.js + JavaScript Vanilla        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    BACKEND (Flask 3.0)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Routes REST API + Session Management + File Uploads     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────┬──────────────────────┬─────────────────────┐
│   JOB SCRAPERS      │   ATS SCORER (AI)    │  COURSE RECOMMENDER │
│                     │                      │                     │
│ • Google Jobs API   │ • Groq AI (Llama)    │ • ChromaDB          │
│ • LinkedIn (Free)   │ • CV Parsing         │ • Sentence-BERT     │
│ • Pôle Emploi API   │ • Skill Extraction   │ • Coursera Scraper  │
│ • Tunisie Travail   │ • Vision AI (VLM)    │ • Quiz Generator    │
└─────────────────────┴──────────────────────┴─────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    STOCKAGE DE DONNÉES                          │
│  ┌─────────────┬──────────────┬─────────────┬─────────────────┐│
│  │  jobs.db    │ coursera_    │  chroma_db/ │  user_cvs/      ││
│  │  (SQLite)   │  fast.db     │  (Vector    │  user_proofs/   ││
│  │             │  (16,416     │   Store)    │  (Files)        ││
│  │  15 MB      │   cours)     │             │                 ││
│  └─────────────┴──────────────┴─────────────┴─────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

---

## 📁 Structure des Fichiers - Utilité Détaillée

### 📂 Racine du Projet

```
CV/
├── 📄 app.py                          (1,971 lignes)
│   └─ Application Flask principale
│      • Routes HTTP (/, /job/<id>, /stats, /api/*, etc.)
│      • Gestion de sessions utilisateur
│      • Upload/Analyse de CV automatique
│      • Intégration avec tous les modules
│      • Administration ChromaDB & Scraping
│      CRITIQUE: Cœur de l'application
│
├── 📄 ats_scorer.py                   (134 KB)
│   └─ Module d'analyse ATS avec IA
│      • analyser_cv_avec_offre(): Matching CV ↔ Job (score 0-100%)
│      • extraire_competences_techniques(): Extraction skills du CV
│      • recommander_cours(): Recherche vectorielle ChromaDB
│      • generer_quiz_coursera(): Génération tests personnalisés
│      • verifier_document_vlm(): Vision AI pour preuves
│      • Intégration Groq AI (Llama 3.1 70B)
│      CRITIQUE: Intelligence artificielle du système
│
├── 📄 requirements.txt                (750 bytes)
│   └─ Dépendances Python
│      • Flask 3.0.0, pandas, requests
│      • PyPDF2, python-docx, Pillow
│      • beautifulsoup4, selenium
│      • sentence-transformers, chromadb
│      ESSENTIEL: Installation des librairies
│
├── 📄 .env                            (70 bytes)
│   └─ Variables d'environnement (SENSIBLE)
│      • ATS_API_KEY=gsk_xxx (Groq AI)
│      • SECRET_KEY=xxx (Flask session)
│      ⚠️  NE JAMAIS COMMITTER CE FICHIER
│
├── 📄 .gitignore                      (158 bytes)
│   └─ Fichiers exclus du versioning
│      • __pycache__/, .env, user_cvs/
│      • user_proofs/, uploads/, nul
│
├── 📄 START_APP.bat                   (211 bytes)
│   └─ Script de démarrage Windows
│      • Lance "python app.py" avec interface jolie
│      UTILE: Pour utilisateurs non-techniques
│
├── 📄 jobs.db                         (15.6 MB)
│   └─ Base de données SQLite des offres d'emploi
│      • Table "jobs" avec ~5000+ offres scrapées
│      • Colonnes: title, company, location, description, etc.
│      • Index optimisés pour recherche rapide
│      CRITIQUE: Stockage des offres d'emploi
│
└── 📄 README.md                       (15.5 KB)
    └─ Documentation utilisateur existante
       • Guide d'installation et utilisation
       • Exemples de configuration
       À REMPLACER ou COMPLÉTER par ce README
```

---

### 📂 job_scraper/ - Module de Scraping d'Offres

```
job_scraper/
├── 📄 db_manager.py
│   └─ Gestionnaire de base de données jobs.db
│      • Classe JobDatabase avec méthodes CRUD
│      • bulk_insert_jobs(): Insertion en masse avec déduplication
│      • search_jobs(): Recherche avec filtres multiples
│      • get_statistics(): Statistiques par source/entreprise
│      • export_to_csv(): Export des données
│      CRITIQUE: Interface unique pour tous les scrapers
│
├── 📄 google_jobs.py
│   └─ Scraper Google Jobs via API officielle
│      • scrape_google_jobs(query, api_key, max_results)
│      • Support multi-pays/langues
│      • Extraction complète (titre, entreprise, description, URL)
│      AVANTAGE: API officielle, données structurées
│
├── 📄 Linkedin.py
│   └─ Scraper LinkedIn (méthode libre sans API payante)
│      • scrape_linkedin_jobs_free(keywords, location, pages)
│      • Parsing HTML avec BeautifulSoup
│      • Gestion du rate limiting (délais entre requêtes)
│      NOTE: Peut nécessiter ajustements si LinkedIn change HTML
│
├── 📄 france_travail.py
│   └─ Scraper API Pôle Emploi (France Travail)
│      • scrape_france_travail(client_id, secret, days)
│      • Authentification OAuth2
│      • Filtres: localisation, type de contrat, secteur
│      AVANTAGE: API officielle avec données certifiées
│
├── 📄 tunisietravail.py
│   └─ Scraper site Tunisie Travail
│      • scrape_tunisie_travail(ville, secteur, max_pages)
│      • Parsing HTML spécifique au site tunisien
│      • Extraction: titre, entreprise, date, URL
│
└── 📄 config.json
    └─ Configuration des scrapers
       • Activation/désactivation par source
       • Paramètres: queries, keywords, API keys, limites
       FORMAT: JSON modifiable via interface admin
```

**Workflow du Scraping:**
```
1. Admin lance scraping via /admin/scraping
2. Chaque scraper retourne liste de jobs (format standardisé)
3. db_manager.bulk_insert_jobs() déduplique et insère
4. jobs.db se met à jour en temps réel
5. Interface utilisateur affiche instantanément les nouvelles offres
```

---

### 📂 course_scraper/ - Recommandation de Cours Coursera

```
course_scraper/
├── 📄 coursera_fast.db                (31 MB)
│   └─ Base SQLite avec 16,416 cours Coursera
│      • Table "courses": id, title, description, difficulty, url, partner
│      • Index sur: course_id, difficulty, title
│      • Données pré-scrapées (gain de temps énorme)
│      CRITIQUE: Base de connaissance pour recommandations
│
├── 📄 course_embedding_store.py       (16 KB)
│   └─ Gestionnaire ChromaDB (Vector Store)
│      • Classe CourseEmbeddingStore
│      • search_similar_courses(query, n_results, where)
│        → Recherche vectorielle < 1 seconde
│      • add_courses_batch(): Ajout en masse avec embeddings
│      • sync_from_sqlite(): Synchronisation SQLite → ChromaDB
│      • Sentence-BERT (all-MiniLM-L6-v2) 384 dimensions
│      CRITIQUE: Cœur de l'optimisation 10x
│
├── 📂 chroma_db/                      (dossier persistant)
│   └─ chroma.sqlite3 + index HNSW
│      • 16,416 embeddings pré-calculés
│      • Algorithme: Hierarchical Navigable Small World
│      • Métrique: Similarité cosinus
│      ⚠️  À générer au premier déploiement
│
├── 📄 coursera_scraper_simple.py      (11 KB)
│   └─ Scraper Coursera rapide
│      • scrape_courses(max_courses, sync_chromadb=True)
│      • Extraction via API interne Coursera
│      • Synchronisation automatique ChromaDB
│      USAGE: Mise à jour hebdomadaire (weekly_update.py)
│
├── 📄 coursera_scraper_utils.py       (25 KB)
│   └─ Utilitaires scraping détaillé des cours
│      • scrape_what_you_learn(course_url)
│        → Extrait "What you'll learn" (objectifs)
│      • scrape_course_modules_details(course_url)
│        → Scrape modules complets (nom, topics, durée)
│      • format_modules_for_quiz_context()
│        → Formate pour génération de quiz IA
│      USAGE: Génération de tests techniques précis
│
├── 📄 weekly_update.py                (12 KB)
│   └─ Script de mise à jour hebdomadaire
│      • Détecte nouveaux cours Coursera (scraping intelligent)
│      • Arrêt auto: 3 batchs consécutifs sans nouveaux cours
│      • Synchronise ChromaDB automatiquement
│      • Génère rapport (update_log.txt)
│      CRON: À exécuter 1x par semaine (dimanche 2h AM)
│
├── 📄 migrate_embeddings_chromadb.py  (4 KB)
│   └─ Script de migration initiale ChromaDB
│      • Charge tous les cours depuis coursera_fast.db
│      • Génère embeddings Sentence-BERT
│      • Stocke dans chroma_db/
│      ⚠️  EXÉCUTER UNE SEULE FOIS au premier déploiement
│      Temps: ~5-10 minutes pour 16,416 cours
│
├── 📄 benchmark_chromadb.py           (7 KB)
│   └─ Benchmark ChromaDB vs méthode classique
│      • Compare temps de recherche
│      • Vérifie qualité des résultats
│      USAGE: Tests de performance (optionnel)
│
├── 📄 test_chromadb_setup.py          (3 KB)
│   └─ Test d'installation ChromaDB
│      • Vérifie connexion, compte embeddings
│      • Test recherche simple
│      USAGE: Validation post-installation
│
└── 📄 Documentation (3 fichiers .md)
    ├─ README_CHROMADB.md              (7.8 KB)
    │  └─ Documentation complète ChromaDB
    ├─ QUICK_START.md                  (3 KB)
    │  └─ Guide démarrage rapide
    └─ INSTALLATION_CHROMADB.md        (5.2 KB)
       └─ Guide d'installation détaillé
```

**Workflow Recommandation de Cours:**
```
1. Utilisateur uploade CV → ATS extrait compétences
2. Pour chaque compétence manquante:
   a. ats_scorer.recommander_cours(competence, niveau, contexte)
   b. CourseEmbeddingStore.search_similar_courses() [ChromaDB]
   c. Scoring hybride: 60% sémantique + 40% correspondance nom
   d. Filtrage par niveau avec fallback intelligent
3. Résultats retournés en < 1 seconde (vs 5-10s avant)
4. Top 3 cours par compétence affichés à l'utilisateur
```

---

### 📂 templates/ - Templates HTML Jinja2

```
templates/
├── 📄 base.html
│   └─ Template de base (extends par tous les autres)
│      • Header avec navigation
│      • Footer
│      • Inclusion Bootstrap 5, Chart.js
│      • Flash messages
│
├── 📄 index.html
│   └─ Page d'accueil / Recherche d'emplois
│      • Barre de recherche multi-critères
│      • Filtres avancés (localisation, entreprise, date, etc.)
│      • Liste des offres avec pagination
│      • Statistiques en temps réel
│
├── 📄 job_detail.html
│   └─ Détail d'une offre + Analyse ATS automatique
│      • Affichage offre complète
│      • SI CV uploadé: Analyse automatique dès chargement
│      • Score de compatibilité (0-100%)
│      • Recommandations de cours pour skills manquantes
│      • Bouton "Postuler" vers l'URL originale
│
├── 📄 stats.html
│   └─ Dashboard statistiques avec Chart.js
│      • Graphiques: Offres par ville, par entreprise, par type
│      • Tendances temporelles
│      • Distribution des contrats
│      • Sources de scraping
│
├── 📄 upload_cv_page.html
│   └─ Page de gestion du CV utilisateur
│      • Upload CV (PDF, DOCX, TXT)
│      • Preview du nom de fichier
│      • Bouton suppression
│      • Liens vers: Vérification preuves, Tests techniques
│
├── 📄 technical_tests.html
│   └─ Génération et passage de tests techniques
│      • Liste des compétences extraites du CV
│      • Génération de quiz personnalisé (10 QCM)
│      • Passage du test avec timer
│      • Évaluation automatique + feedback
│      • Mise à jour du niveau de compétence
│
├── 📄 verify_credentials.html
│   └─ Vérification des certificats/attestations
│      • Liste des certificats extraits du CV
│      • Upload de preuves (PDF, images)
│      • Vérification automatique via Vision AI
│      • Statut: Confirmé, Partiellement confirmé, Non confirmé
│
├── 📄 admin_scraping.html
│   └─ Dashboard admin pour scraping
│      • Configuration des scrapers (activation, params)
│      • Lancement manuel par source
│      • Suivi temps réel (progression, logs)
│      • Statistiques: Total jobs, par source, doublons
│      • Export CSV
│
├── 📄 admin_chromadb.html
│   └─ Dashboard admin ChromaDB
│      • Statut: Nombre d'embeddings vs cours en DB
│      • Migration initiale (bouton "Migrer")
│      • Progression en temps réel
│      • Vérification santé du vector store
│
├── 📄 cv_analysis.html
│   └─ Affichage résultat analyse ATS détaillée
│      • Score global, breakdown par catégorie
│      • Skills trouvées vs manquantes
│      • Recommandations personnalisées
│
├── 📄 cv_upload.html
│   └─ Formulaire upload CV (route /analyze-cv/<job_id>)
│      • Upload pour une offre spécifique
│      • Analyse immédiate après upload
│
└── 📄 test_jobs.html
    └─ Page de test pour développement
       • Debug: Affichage brut des offres
```

---

### 📂 static/ - Fichiers Statiques

```
static/
├── css/
│   ├── 📄 main.css
│   │   └─ Styles principaux de l'application
│   │      • Layout, colors, typography
│   │      • Composants personnalisés (cards, badges)
│   │      • Responsive design
│   │
│   └── 📄 style.css
│       └─ Styles additionnels/overrides
│
└── js/
    ├── 📄 main.js
    │   └─ JavaScript principal
    │      • Gestion des filtres de recherche
    │      • Pagination AJAX
    │      • Upload de fichiers avec preview
    │      • Flash messages animés
    │
    └── 📄 app.js
        └─ JavaScript applicatif
           • Intégration Chart.js pour graphiques
           • Appels API AJAX (/api/search, /api/recommend-courses)
           • Gestion des tests techniques (timer, soumission)
           • Vérification de documents (upload + VLM)
```

---

### 📂 Dossiers de Données Utilisateur

```
user_cvs/
└─ CVs uploadés par les utilisateurs
   • Noms: <session_id>.pdf/.docx
   • Stockage persistant (non versionné Git)
   ⚠️  À sauvegarder régulièrement

user_proofs/
└─ Preuves (certificats, attestations) uploadées
   • Structure: <session_id>/<categorie>/<item_index>_filename.pdf
   • Utilisé pour vérification VLM
   ⚠️  À sauvegarder régulièrement

uploads/
└─ Fichiers temporaires (intermédiaires)
   • Nettoyage automatique recommandé
```

---

### 🗑️ Fichiers À SUPPRIMER (Non Essentiels)

```
❌ nul                                  (56 bytes)
   → Fichier vide/erreur Windows

❌ updates.txt                          (5.6 KB)
   → Notes de développement (déjà dans .gitignore)

❌ check_db_courses.py                  (663 bytes)
   → Script de test (usage unique)

❌ test_scraper_topics.py               (1 KB)
   → Script de test (usage unique)

❌ tests_indisponibles.log              (2 bytes)
   → Log vide

❌ templates/job_detail.html.backup
   → Backup temporaire

❌ EXPLICATION_SCRAPING_GENERATION_TESTS.md (29 KB)
   → Documentation technique (redondante avec ce README)

❌ cours_recommandation_semantic.py     (7.5 KB)
   → Ancien script OBSOLÈTE (remplacé par ChromaDB)

❌ course_scraper/migrate_embeddings.py (10 KB)
   → Ancienne version migration (remplacée par migrate_embeddings_chromadb.py)
```

**Action recommandée:**
```bash
# Supprimer les fichiers non essentiels
rm nul updates.txt check_db_courses.py test_scraper_topics.py tests_indisponibles.log
rm templates/job_detail.html.backup cours_recommandation_semantic.py
rm EXPLICATION_SCRAPING_GENERATION_TESTS.md
rm course_scraper/migrate_embeddings.py
```

---

## 🛠️ Technologies Utilisées

### Backend

| Technologie | Version | Rôle |
|-------------|---------|------|
| **Python** | 3.8+ | Langage principal |
| **Flask** | 3.0.0 | Framework web |
| **Pandas** | 2.1.4 | Manipulation de données |
| **SQLite** | 3.x | Base de données |
| **Sentence-Transformers** | Latest | Embeddings sémantiques |
| **ChromaDB** | Latest | Vector database |
| **Groq AI** | API | LLM (Llama 3.1 70B) |
| **BeautifulSoup4** | 4.12.2 | Web scraping HTML |
| **Selenium** | 4.16.0 | Scraping dynamique (optionnel) |
| **PyPDF2** | 3.0.1 | Extraction texte PDF |
| **python-docx** | 1.1.0 | Extraction texte Word |
| **Pillow** | 10.1.0 | Traitement d'images |

### Frontend

| Technologie | CDN | Rôle |
|-------------|-----|------|
| **Bootstrap** | 5.3 | Framework CSS |
| **Chart.js** | 4.4.0 | Graphiques interactifs |
| **JavaScript Vanilla** | ES6 | Interactivité |
| **Jinja2** | (Flask) | Templating |

### APIs Externes

| Service | Usage | Requis? |
|---------|-------|---------|
| **Groq AI** | Analyse ATS, extraction skills, quiz | ✅ OUI |
| **Google Jobs API** | Scraping offres Google | ❌ Optionnel |
| **France Travail API** | Scraping Pôle Emploi | ❌ Optionnel |

---

## 🚀 Installation

### Prérequis

- **Python 3.8+** installé
- **pip** (gestionnaire de packages Python)
- **Git** pour clonage du repository
- **Clé API Groq** (gratuite) : https://console.groq.com/

### Étapes d'Installation

#### 1. Cloner le Repository

```bash
git clone <URL_DU_REPO>
cd CV
```

#### 2. Créer un Environnement Virtuel

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Installer les Dépendances

```bash
pip install -r requirements.txt
```

**Vérification:**
```bash
pip list | grep -E "Flask|chromadb|sentence-transformers|pandas"
```

#### 4. Configuration des Variables d'Environnement

Créer le fichier `.env` à la racine:

```bash
# Windows
copy NUL .env

# Linux/Mac
touch .env
```

Éditer `.env` et ajouter:

```env
# OBLIGATOIRE
ATS_API_KEY=gsk_votre_cle_groq_ici

# OPTIONNEL (si scraping Google Jobs)
GOOGLE_JOBS_API_KEY=votre_cle_google

# OPTIONNEL (si scraping France Travail)
FRANCE_TRAVAIL_CLIENT_ID=votre_client_id
FRANCE_TRAVAIL_CLIENT_SECRET=votre_secret

# Flask (générer une clé aléatoire)
SECRET_KEY=votre_cle_secrete_aleatoire
```

**Générer une SECRET_KEY:**
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 5. Initialiser ChromaDB (IMPORTANT)

**Étape cruciale** - À exécuter une seule fois:

```bash
cd course_scraper
python migrate_embeddings_chromadb.py
```

**Attendu:**
```
Migration terminée avec succès!
- Cours ajoutés: 16416
- Total dans ChromaDB: 16416
```

**Temps:** ~5-10 minutes

**Vérification:**
```bash
python -c "from course_embedding_store import CourseEmbeddingStore; print(f'Embeddings: {CourseEmbeddingStore().get_count()}')"
```

#### 6. Lancer l'Application

```bash
# Retourner à la racine
cd ..

# Lancer Flask
python app.py
```

**Ou avec le script Windows:**
```bash
START_APP.bat
```

**Sortie attendue:**
```
======================================================================
 PLATEFORME DE MATCHING D'EMPLOIS AVEC ATS
======================================================================
  Application principale: http://localhost:5000
  Dashboard ATS: http://localhost:5000
  Admin Scraping: http://localhost:5000/admin/scraping
  Module de scraping: ACTIVE
======================================================================

✅ CHROMADB PRÊT: 16416/16416 embeddings

 * Running on http://0.0.0.0:5000
```

#### 7. Accéder à l'Application

Ouvrir dans le navigateur:
- **Interface Principale:** http://localhost:5000
- **Statistiques:** http://localhost:5000/stats
- **Admin Scraping:** http://localhost:5000/admin/scraping
- **Admin ChromaDB:** http://localhost:5000/admin/chromadb

---

## ⚙️ Configuration

### Configuration des Scrapers

Éditer `job_scraper/config.json`:

```json
{
  "scrapers": {
    "google_jobs": {
      "enabled": true,
      "api_key": "",
      "queries": ["python developer tunisia", "data scientist"],
      "max_results": 200,
      "country": "tn",
      "language": "fr"
    },
    "linkedin": {
      "enabled": true,
      "keywords": ["python", "data science", "devops"],
      "location": "Tunisia",
      "pages": 2,
      "get_descriptions": false
    },
    "france_travail": {
      "enabled": false,
      "client_id": "",
      "client_secret": "",
      "days": 7
    },
    "tunisie_travail": {
      "enabled": true,
      "ville": "tunis",
      "secteur": "informatique",
      "max_pages": 3
    }
  }
}
```

**Ou via l'interface admin:**
1. Aller sur http://localhost:5000/admin/scraping
2. Modifier la configuration
3. Cliquer "Sauvegarder"

### Configuration Flask

Éditer `app.py` (lignes 32-36):

```python
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'changez_moi_en_production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
```

---

## 🔄 Workflows Principaux

### Workflow 1: Recherche d'Emploi avec Analyse ATS

```
1. Utilisateur uploade CV (Mon CV)
   ↓
2. Session stocke CV (user_cvs/<session_id>.pdf)
   ↓
3. Utilisateur recherche offres (/ ou filtres)
   ↓
4. Clic sur une offre (/job/<id>)
   ↓
5. SI CV uploadé:
   a. Extraction texte CV (ats_scorer.extraire_texte_fichier)
   b. Analyse automatique (ats_scorer.analyser_cv_avec_offre)
   c. Génération rapport HTML (score, skills, recommandations)
   ↓
6. Affichage:
   - Détail de l'offre
   - Score de compatibilité (0-100%)
   - Skills trouvées vs manquantes
   - Recommandations de cours Coursera (via ChromaDB)
```

### Workflow 2: Recommandation de Cours Coursera

```
1. Analyse ATS identifie skills manquantes
   ↓
2. Pour chaque skill:
   a. Appel /api/recommend-courses (POST)
   b. ats_scorer.recommander_cours(skill, niveau, contexte)
   c. course_embedding_store.search_similar_courses(query)
      → Recherche vectorielle ChromaDB (< 1 sec)
   d. Scoring hybride:
      - 60% similarité sémantique (Sentence-BERT)
      - 40% correspondance nom exact
   e. Filtrage par niveau avec fallback intelligent
   ↓
3. Top 3 cours par skill retournés
   ↓
4. Affichage avec:
   - Titre, description, organisme
   - Difficulté, durée
   - Lien Coursera
   - Score de similarité
```

### Workflow 3: Génération de Tests Techniques

```
1. Utilisateur va sur "Tests Techniques"
   ↓
2. Extraction skills du CV (ats_scorer.extraire_competences_techniques)
   ↓
3. Affichage liste de compétences avec niveaux
   ↓
4. Clic "Générer Test" pour une skill:
   a. Appel /generate-test/<category>/<index> (POST)
   b. ats_scorer.generer_quiz_coursera(competence, niveau, cv_text)
   c. Récupération modules Coursera (coursera_scraper_utils.scrape_course_modules_details)
   d. Génération 10 QCM via Groq AI basés sur modules
   e. Distribution: 30% facile, 50% intermédiaire, 20% difficile
   ↓
5. Affichage du test (10 QCM)
   ↓
6. Utilisateur répond et soumet
   ↓
7. Évaluation automatique:
   a. Calcul score (0-100%)
   b. Détermination niveau réel (novice → expert)
   c. Feedback détaillé par question
   ↓
8. Mise à jour du niveau de compétence dans session
```

### Workflow 4: Vérification de Documents (Vision AI)

```
1. Utilisateur va sur "Vérifier Compétences"
   ↓
2. Extraction certificats/attestations du CV
   (ats_scorer.extraire_certificats_attestations via Groq AI)
   ↓
3. Affichage liste (Certifications, Formations, Langues)
   ↓
4. Upload preuve (PDF ou image) pour un élément
   ↓
5. Conversion PDF → Image si nécessaire (ats_scorer.pdf_to_image)
   ↓
6. Vérification via Vision AI:
   a. Appel /verify-proof/<category>/<index> (POST)
   b. ats_scorer.verifier_document_vlm(claim, proof_path)
   c. Groq Vision API analyse l'image
   d. Comparaison claim CV ↔ texte extrait de l'image
   ↓
7. Résultat:
   - Statut: Confirmé, Partiellement confirmé, Non confirmé
   - Score de confiance (0-100%)
   - Éléments confirmés vs manquants
   - Commentaire détaillé
   - Recommandation: Accepter, Demander clarification, Rejeter
```

### Workflow 5: Scraping d'Offres d'Emploi

```
1. Admin va sur /admin/scraping
   ↓
2. Configuration des sources (config.json)
   ↓
3. Clic "Scraper" pour une source (ex: LinkedIn)
   ↓
4. Appel /api/scraping/source/linkedin (POST)
   ↓
5. Thread en arrière-plan:
   a. Chargement config (keywords, location, pages)
   b. Scraping via job_scraper/Linkedin.py
   c. Retour liste de jobs (format standardisé)
   d. Insertion via db_manager.bulk_insert_jobs()
      → Déduplication par URL + date
   e. Mise à jour jobs.db
   ↓
6. Suivi temps réel:
   - Statut: running → completed/error
   - Progression (%)
   - Jobs trouvés vs doublons
   ↓
7. Rechargement automatique de job_platform.df
   ↓
8. Nouvelles offres visibles sur / instantanément
```

---

## 📡 API et Endpoints

### Endpoints Publics

#### **GET /** - Page d'accueil
```
Paramètres Query:
- keyword: str (recherche titre/description)
- location: str (filtrage localisation)
- company: str (filtrage entreprise)
- job_type: str (CDI, CDD, Stage, etc.)
- contract_type: str (Temps plein, Temps partiel)
- source: str (google_jobs, linkedin, etc.)
- date_range: str (1day, 1week, 1month, 3months, thisyear, all)
- page: int (pagination)

Retour: HTML avec liste d'offres + filtres
```

#### **GET /job/<int:job_id>** - Détail d'une offre
```
Paramètres:
- job_id: Index de l'offre dans jobs.db

Comportement:
- SI CV uploadé: Analyse automatique dès chargement
- SINON: Affichage simple de l'offre

Retour: HTML avec détail + analyse ATS (si CV)
```

#### **GET /api/search** - Recherche AJAX
```
Paramètres Query: (mêmes que GET /)

Retour JSON:
{
  "success": true,
  "jobs": [...],
  "stats": {
    "total_jobs": 150,
    "total_pages": 8,
    "current_page": 1,
    "per_page": 20
  }
}
```

#### **POST /api/recommend-courses** - Recommandations Coursera
```
Body JSON:
{
  "missing_skills": ["Python", "Docker", "PostgreSQL"],
  "job_id": 123
}

Retour JSON:
{
  "success": true,
  "recommendations": [
    {
      "title": "Python for Data Science",
      "description": "...",
      "partner": "Stanford University",
      "url": "https://coursera.org/...",
      "difficulty": "INTERMEDIATE",
      "duration": "4 weeks",
      "language": "en",
      "matched_skill": "Python",
      "score_similarite": 87.5
    },
    ...
  ],
  "missing_skills": ["Python", "Docker", "PostgreSQL"],
  "total_skills": 3,
  "total_courses": 9,
  "used_chromadb": true
}
```

### Endpoints CV

#### **POST /upload-cv** - Upload CV
```
Multipart Form:
- cv_file: File (PDF, DOCX, TXT)

Retour JSON:
{
  "success": true,
  "message": "CV uploadé avec succès",
  "filename": "mon_cv.pdf"
}

Comportement:
- Génère session_id (UUID) si pas existant
- Sauvegarde: user_cvs/<session_id>.pdf
- Extraction texte pour validation (min 50 chars)
- Stockage en session: cv_uploaded, cv_filename, cv_path
```

#### **POST /remove-cv** - Supprimer CV
```
Retour JSON:
{
  "success": true,
  "message": "CV supprimé avec succès"
}

Comportement:
- Supprime fichier physique
- Clear session (cv_uploaded, cv_filename, cv_path, cv_text)
```

#### **GET /check-cv** - Vérifier présence CV
```
Retour JSON:
{
  "cv_uploaded": true,
  "cv_filename": "mon_cv.pdf"
}
```

### Endpoints Tests Techniques

#### **GET /technical-tests** - Page tests
```
Comportement:
- Extraction compétences du CV via Groq AI
- Sauvegarde en session: technical_skills
- Affichage liste compétences avec boutons "Générer Test"

Retour: HTML
```

#### **POST /generate-test/<category>/<int:skill_index>**
```
Paramètres:
- category: "competences_techniques" ou autre
- skill_index: Index dans la liste de compétences

Body JSON (optionnel):
{
  "difficulte": "moyen|facile|difficile"
}

Retour JSON:
{
  "success": true,
  "test": {
    "competence_testee": "Python",
    "niveau_difficulte": "intermédiaire",
    "questions": [
      {
        "numero": 1,
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "reponse_correcte": "2",
        "explication": "...",
        "difficulte": "facile"
      },
      ...
    ],
    "bareme": {
      "total_points": 100,
      "seuil_reussite": 80,
      "excellent": 90
    }
  }
}

Comportement:
- Recommande cours Coursera pour la compétence
- Scrape modules du meilleur cours
- Génère 10 QCM basés sur les modules via Groq AI
- Sauvegarde test en session: generated_tests[test_key]
```

#### **POST /submit-test/<category>/<int:skill_index>**
```
Body JSON:
{
  "reponses": {
    "q_0": "2",
    "q_1": "0",
    ...
  }
}

Retour JSON:
{
  "success": true,
  "evaluation": {
    "score_total": 85,
    "max_points": 100,
    "pourcentage": 85.0,
    "niveau_reel": "avancé",
    "statut": "reussi",
    "message": "Compétence validée avec succès!",
    "resultats_detailles": [...]
  }
}

Comportement:
- Évalue chaque réponse (correcte/incorrecte)
- Calcule score total et %
- Détermine niveau réel basé sur score:
  - 90-100%: expert
  - 75-89%: avancé
  - 60-74%: intermédiaire
  - 40-59%: débutant
  - 0-39%: novice
- Met à jour technical_skills en session
- Sauvegarde résultat: test_results[test_key]
```

### Endpoints Vérification Documents

#### **GET /verify-cv** - Page vérification
```
Comportement:
- Extraction certificats/attestations du CV via Groq AI
- Sauvegarde en session: credentials_extracted
- Affichage liste avec boutons "Upload Preuve"

Retour: HTML
```

#### **POST /upload-proof/<category>/<int:item_index>**
```
Paramètres:
- category: "certifications", "formations", "langues"
- item_index: Index dans la liste

Multipart Form:
- proof_file: File (PDF, JPG, PNG)

Retour JSON:
{
  "success": true,
  "message": "Preuve uploadée avec succès",
  "filename": "0_certificat.pdf",
  "has_preview": true
}

Comportement:
- Sauvegarde: user_proofs/<session_id>/<category>/<item_index>_filename.pdf
- Si PDF: Conversion → image preview (Pillow)
- Stockage en session: uploaded_proofs[proof_key]
```

#### **POST /verify-proof/<category>/<int:item_index>**
```
Retour JSON:
{
  "success": true,
  "verification": {
    "statut": "confirmé|partiellement_confirmé|non_confirmé|insuffisant",
    "score_confiance": 95,
    "elements_confirmes": ["Nom correct", "Organisme validé"],
    "elements_manquants": [],
    "divergences": [],
    "commentaire": "Le certificat confirme l'obtention de...",
    "recommandation": "accepter|demander_clarification|rejeter"
  }
}

Comportement:
- Récupère claim original du CV
- Récupère preuve uploadée
- Appel ats_scorer.verifier_document_vlm(claim, proof_path, category)
  → Groq Vision API analyse l'image
  → Compare claim vs texte extrait
- Sauvegarde résultat: verification_results[proof_key]
```

### Endpoints Admin Scraping

#### **GET /admin/scraping** - Dashboard
```
Retour: HTML avec:
- Statistiques (total jobs, par source, par entreprise)
- Configuration des scrapers
- Boutons lancement par source
- Logs en temps réel
```

#### **POST /api/scraping/source/<source_name>**
```
Paramètres:
- source_name: google_jobs|linkedin|france_travail|tunisie_travail

Retour JSON:
{
  "success": true,
  "message": "Scraping de linkedin démarré"
}

Comportement:
- Lance scraping en thread daemon
- Met à jour scraping_status global
- Insertion bulk dans jobs.db via db_manager
```

#### **GET /api/scraping/status**
```
Retour JSON:
{
  "is_running": true,
  "current_source": "linkedin",
  "sources_status": {
    "linkedin": {
      "status": "running",
      "jobs_found": 45,
      "message": "Keyword 2/3: data science",
      "progress": 66
    },
    ...
  },
  "total_jobs": 45,
  "start_time": "2025-11-13T14:30:00",
  "end_time": null
}
```

#### **GET /api/scraping/stats**
```
Retour JSON:
{
  "total_jobs": 5234,
  "by_source": {
    "linkedin": 2100,
    "google_jobs": 1800,
    "tunisie_travail": 1334
  },
  "by_company": {
    "Microsoft": 45,
    "Google": 38,
    ...
  },
  "date_range": {
    "oldest": "2025-01-01",
    "newest": "2025-11-13"
  }
}
```

### Endpoints Admin ChromaDB

#### **GET /admin/chromadb** - Dashboard
```
Retour: HTML avec:
- Statut: Embeddings count vs Total courses
- Migration needed? (boolean)
- Bouton "Migrer" si nécessaire
- Dernière vérification
```

#### **GET /api/chromadb/status**
```
Retour JSON:
{
  "initialized": true,
  "embeddings_count": 16416,
  "total_courses": 16416,
  "migration_needed": false,
  "migration_running": false,
  "migration_progress": 0,
  "last_check": "2025-11-13T14:00:00",
  "error": null
}
```

#### **POST /api/chromadb/migrate**
```
Retour JSON:
{
  "success": true,
  "message": "Migration démarrée en arrière-plan"
}

Comportement:
- Lance migration en thread daemon
- Charge tous les cours depuis coursera_fast.db
- Génère embeddings Sentence-BERT
- Stocke dans chroma_db/
- Met à jour chromadb_status global avec progression
```

---

## 🗄️ Base de Données

### jobs.db (SQLite)

#### Table: jobs

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT,
    job_url TEXT UNIQUE,
    date TEXT,
    job_type TEXT,
    salary TEXT,
    contrat TEXT,
    source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_url ON jobs(job_url);
CREATE INDEX idx_source ON jobs(source);
CREATE INDEX idx_date ON jobs(date);
CREATE INDEX idx_location ON jobs(location);
```

**Colonnes:**
- `id`: Clé primaire auto-incrémentée
- `title`: Titre de l'offre (ex: "Data Scientist Senior")
- `company`: Nom de l'entreprise (ex: "Microsoft")
- `location`: Localisation (ex: "Tunis, Tunisia")
- `description`: Description complète du poste (HTML ou texte brut)
- `job_url`: URL unique de l'offre (contrainte UNIQUE pour déduplication)
- `date`: Date de publication (format: "DD/MM/YYYY" ou "YYYY-MM-DD")
- `job_type`: Type de poste (ex: "Temps plein", "Temps partiel")
- `salary`: Salaire (ex: "50000 EUR/an", optionnel)
- `contrat`: Type de contrat (ex: "CDI", "CDD", "Stage")
- `source`: Source du scraping (ex: "linkedin", "google_jobs")
- `created_at`: Date d'insertion en DB

**Volume:** ~5000+ offres (15.6 MB)

**Déduplication:** Par `job_url` (insertion ignorée si doublon)

---

### course_scraper/coursera_fast.db (SQLite)

#### Table: courses

```sql
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT UNIQUE,
    slug TEXT,
    title TEXT NOT NULL,
    description TEXT,
    partner_name TEXT,
    url TEXT,
    categories TEXT,
    difficulty TEXT,
    duration TEXT,
    language TEXT
);

CREATE INDEX idx_course_id ON courses(course_id);
CREATE INDEX idx_difficulty ON courses(difficulty);
CREATE INDEX idx_title ON courses(title);
```

**Colonnes:**
- `id`: Clé primaire
- `course_id`: ID unique Coursera (ex: "python-fundamentals")
- `slug`: Slug URL (ex: "learn/python-fundamentals")
- `title`: Titre du cours (ex: "Python for Data Science")
- `description`: Description complète du cours
- `partner_name`: Organisme (ex: "Stanford University", "Google")
- `url`: URL complète Coursera
- `categories`: Catégories (format JSON array stringifié)
- `difficulty`: Niveau (BEGINNER, INTERMEDIATE, ADVANCED)
- `duration`: Durée estimée (ex: "4 weeks", "20 hours")
- `language`: Langue (ex: "en", "fr")

**Volume:** 16,416 cours (31 MB)

**Mise à jour:** Hebdomadaire via `weekly_update.py`

---

### course_scraper/chroma_db/ (ChromaDB)

#### Collection: coursera_courses

**Structure:**
```python
{
  "ids": ["course_id_1", "course_id_2", ...],
  "embeddings": [
    [0.123, -0.456, ...],  # 384 dimensions (Sentence-BERT)
    [0.789, 0.012, ...],
    ...
  ],
  "metadatas": [
    {
      "title": "Python for Data Science",
      "difficulty": "INTERMEDIATE",
      "duration": "4 weeks",
      "partner_name": "Stanford University",
      "url": "https://coursera.org/..."
    },
    ...
  ],
  "documents": [
    "Python for Data Science - Learn Python programming...",
    ...
  ]
}
```

**Modèle d'Embeddings:** Sentence-BERT (`all-MiniLM-L6-v2`)
- Dimensions: 384
- Type: Dense vector
- Métrique: Cosinus similarity

**Index:** HNSW (Hierarchical Navigable Small World)
- Complexité: O(log N) pour recherche
- Performance: < 1 sec pour 16,416 vecteurs

**Persistance:** Automatique dans `chroma_db/chroma.sqlite3`

---

## 🚀 Déploiement

### Déploiement sur VPS (Ubuntu/Debian)

#### 1. Préparer le Serveur

```bash
# Connexion SSH
ssh user@votre-serveur.com

# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Python et dépendances
sudo apt install python3 python3-pip python3-venv nginx -y
```

#### 2. Cloner et Configurer le Projet

```bash
# Cloner le repository
git clone <URL_REPO> /var/www/jobmatch
cd /var/www/jobmatch

# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt
pip install gunicorn  # Serveur WSGI production
```

#### 3. Configuration .env

```bash
# Créer .env avec vos vraies clés
nano .env
```

```env
ATS_API_KEY=gsk_VOTRE_CLE_GROQ_PRODUCTION
SECRET_KEY=GENERER_UNE_CLE_ALEATOIRE_LONGUE
FLASK_ENV=production
FLASK_DEBUG=False
```

#### 4. Initialiser ChromaDB

```bash
cd course_scraper
python migrate_embeddings_chromadb.py
cd ..
```

#### 5. Configuration Gunicorn

Créer `/var/www/jobmatch/gunicorn_config.py`:

```python
bind = "127.0.0.1:8000"
workers = 4  # 2 × CPU cores
worker_class = "sync"
timeout = 120
keepalive = 5
errorlog = "/var/log/jobmatch/error.log"
accesslog = "/var/log/jobmatch/access.log"
loglevel = "info"
```

Créer dossier logs:
```bash
sudo mkdir -p /var/log/jobmatch
sudo chown -R www-data:www-data /var/log/jobmatch
```

#### 6. Service Systemd

Créer `/etc/systemd/system/jobmatch.service`:

```ini
[Unit]
Description=JobMatch Pro - Plateforme de Matching d'Emplois
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/jobmatch
Environment="PATH=/var/www/jobmatch/venv/bin"
ExecStart=/var/www/jobmatch/venv/bin/gunicorn -c /var/www/jobmatch/gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activer et démarrer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jobmatch
sudo systemctl start jobmatch
sudo systemctl status jobmatch
```

#### 7. Configuration Nginx

Créer `/etc/nginx/sites-available/jobmatch`:

```nginx
server {
    listen 80;
    server_name jobmatch.votredomaine.com;

    # Logs
    access_log /var/log/nginx/jobmatch_access.log;
    error_log /var/log/nginx/jobmatch_error.log;

    # Limite upload (CVs, preuves)
    client_max_body_size 50M;

    # Proxy vers Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Timeouts pour analyse ATS (peut être long)
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Fichiers statiques (CSS, JS)
    location /static {
        alias /var/www/jobmatch/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Fichiers uploadés (CVs, preuves)
    location /user_cvs {
        internal;
        alias /var/www/jobmatch/user_cvs;
    }
}
```

Activer le site:
```bash
sudo ln -s /etc/nginx/sites-available/jobmatch /etc/nginx/sites-enabled/
sudo nginx -t  # Vérifier config
sudo systemctl reload nginx
```

#### 8. SSL avec Let's Encrypt

```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx -y

# Générer certificat SSL
sudo certbot --nginx -d jobmatch.votredomaine.com

# Renouvellement automatique (cron)
sudo certbot renew --dry-run
```

#### 9. Permissions

```bash
# Définir propriétaire
sudo chown -R www-data:www-data /var/www/jobmatch

# Permissions
sudo chmod -R 755 /var/www/jobmatch
sudo chmod -R 770 /var/www/jobmatch/user_cvs
sudo chmod -R 770 /var/www/jobmatch/user_proofs
```

#### 10. Vérification

```bash
# Logs Gunicorn
tail -f /var/log/jobmatch/error.log

# Logs Nginx
tail -f /var/log/nginx/jobmatch_error.log

# Status service
sudo systemctl status jobmatch
```

Tester: https://jobmatch.votredomaine.com

---

### Déploiement Docker (Optionnel)

#### Dockerfile

Créer `Dockerfile` à la racine:

```dockerfile
FROM python:3.10-slim

# Installer dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Dossier de travail
WORKDIR /app

# Copier fichiers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Créer dossiers nécessaires
RUN mkdir -p uploads user_cvs user_proofs

# Exposer port
EXPOSE 5000

# Variables d'environnement
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Commande de démarrage
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "--timeout", "120", "app:app"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  jobmatch:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./user_cvs:/app/user_cvs
      - ./user_proofs:/app/user_proofs
      - ./jobs.db:/app/jobs.db
      - ./course_scraper:/app/course_scraper
    environment:
      - ATS_API_KEY=${ATS_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
```

#### Commandes Docker

```bash
# Build
docker-compose build

# Démarrer
docker-compose up -d

# Logs
docker-compose logs -f

# Arrêter
docker-compose down
```

---

## 🔧 Maintenance

### Mise à Jour Hebdomadaire des Cours Coursera

#### Automatisation avec Cron (Linux)

Créer script `/var/www/jobmatch/scripts/weekly_coursera_update.sh`:

```bash
#!/bin/bash
cd /var/www/jobmatch/course_scraper
source ../venv/bin/activate
python weekly_update.py >> /var/log/jobmatch/coursera_update.log 2>&1
```

Rendre exécutable:
```bash
chmod +x /var/www/jobmatch/scripts/weekly_coursera_update.sh
```

Ajouter à crontab:
```bash
sudo crontab -e
```

Ajouter ligne:
```cron
# Mise à jour Coursera tous les dimanches à 2h AM
0 2 * * 0 /var/www/jobmatch/scripts/weekly_coursera_update.sh
```

#### Automatisation avec Task Scheduler (Windows)

1. Ouvrir Task Scheduler
2. Créer une tâche de base:
   - **Nom:** Coursera Weekly Update
   - **Trigger:** Hebdomadaire, dimanche 2h AM
   - **Action:** Démarrer un programme
   - **Programme:** `C:\chemin\vers\venv\Scripts\python.exe`
   - **Arguments:** `C:\chemin\vers\CV\course_scraper\weekly_update.py`

---

### Sauvegarde des Données

#### Script de Backup

Créer `/var/www/jobmatch/scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/jobmatch"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/var/www/jobmatch"

# Créer dossier backup
mkdir -p $BACKUP_DIR

# Backup jobs.db
cp $APP_DIR/jobs.db $BACKUP_DIR/jobs_${DATE}.db

# Backup coursera_fast.db
cp $APP_DIR/course_scraper/coursera_fast.db $BACKUP_DIR/coursera_${DATE}.db

# Backup ChromaDB
tar -czf $BACKUP_DIR/chroma_db_${DATE}.tar.gz -C $APP_DIR/course_scraper chroma_db

# Backup CVs et preuves utilisateurs
tar -czf $BACKUP_DIR/user_files_${DATE}.tar.gz -C $APP_DIR user_cvs user_proofs

# Supprimer backups > 30 jours
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup terminé: $DATE" >> /var/log/jobmatch/backup.log
```

Rendre exécutable:
```bash
chmod +x /var/www/jobmatch/scripts/backup.sh
```

Automatiser (cron quotidien à 3h AM):
```cron
0 3 * * * /var/www/jobmatch/scripts/backup.sh
```

---

### Monitoring et Logs

#### Logs à Surveiller

| Fichier | Contenu |
|---------|---------|
| `/var/log/jobmatch/error.log` | Erreurs Gunicorn/Flask |
| `/var/log/jobmatch/access.log` | Requêtes HTTP |
| `/var/log/nginx/jobmatch_error.log` | Erreurs Nginx |
| `/var/log/jobmatch/coursera_update.log` | Mise à jour cours |
| `/var/log/jobmatch/backup.log` | Historique backups |

#### Commandes Utiles

```bash
# Logs en temps réel
tail -f /var/log/jobmatch/error.log

# 50 dernières erreurs
tail -n 50 /var/log/jobmatch/error.log

# Rechercher erreur spécifique
grep "ERROR" /var/log/jobmatch/error.log

# Taille des logs
du -sh /var/log/jobmatch/*

# Rotation des logs (logrotate)
sudo nano /etc/logrotate.d/jobmatch
```

Contenu `/etc/logrotate.d/jobmatch`:
```
/var/log/jobmatch/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload jobmatch > /dev/null 2>&1 || true
    endscript
}
```

---

### Nettoyage des Fichiers Temporaires

#### Script de Nettoyage

Créer `/var/www/jobmatch/scripts/cleanup.sh`:

```bash
#!/bin/bash
APP_DIR="/var/www/jobmatch"

# Supprimer fichiers uploads/ > 24h
find $APP_DIR/uploads -type f -mtime +1 -delete

# Supprimer CVs orphelins > 30 jours
# (CVs sans session active)
find $APP_DIR/user_cvs -type f -mtime +30 -delete

# Supprimer preuves orphelines > 30 jours
find $APP_DIR/user_proofs -type d -mtime +30 -exec rm -rf {} +

# Nettoyer cache Python
find $APP_DIR -type d -name "__pycache__" -exec rm -rf {} +

echo "Nettoyage terminé: $(date)" >> /var/log/jobmatch/cleanup.log
```

Automatiser (cron quotidien à 4h AM):
```cron
0 4 * * * /var/www/jobmatch/scripts/cleanup.sh
```

---

### Surveillance des Performances

#### Vérifier Utilisation Ressources

```bash
# CPU/RAM
htop

# Espace disque
df -h

# Taille base de données
du -sh /var/www/jobmatch/*.db
du -sh /var/www/jobmatch/course_scraper/*.db

# Nombre de CVs stockés
ls -1 /var/www/jobmatch/user_cvs | wc -l
```

#### Optimisation ChromaDB

Si ChromaDB devient lent:

```bash
cd /var/www/jobmatch/course_scraper
source ../venv/bin/activate

# Réinitialiser et reconstruire
python -c "
from course_embedding_store import CourseEmbeddingStore
store = CourseEmbeddingStore()
store.reset()
print('ChromaDB réinitialisé')
"

# Resynchroniser
python migrate_embeddings_chromadb.py
```

---

## 📞 Support et Contact

### Issues et Bugs

Pour signaler un bug ou demander une fonctionnalité:
1. Ouvrir une issue sur GitHub
2. Fournir:
   - Description du problème
   - Steps to reproduce
   - Logs d'erreur
   - Configuration (OS, Python version)

### Documentation Complémentaire

- **README.md** : Documentation utilisateur
- **course_scraper/README_CHROMADB.md** : Guide ChromaDB
- **course_scraper/QUICK_START.md** : Démarrage rapide ChromaDB
- **Ce fichier** : Documentation technique complète

---

## 📊 Statistiques du Projet

| Métrique | Valeur |
|----------|--------|
| **Lignes de Code Python** | ~3,500+ |
| **Fichiers Python** | 15 |
| **Templates HTML** | 12 |
| **Fichiers JavaScript** | 2 |
| **Fichiers CSS** | 2 |
| **Sources de Scraping** | 4 (Google Jobs, LinkedIn, Pôle Emploi, Tunisie Travail) |
| **API Endpoints** | 25+ |
| **Cours Coursera** | 16,416 |
| **Embeddings ChromaDB** | 16,416 vecteurs 384D |
| **Taille jobs.db** | 15.6 MB |
| **Taille coursera_fast.db** | 31 MB |
| **Gain performance ChromaDB** | **10x plus rapide** (< 1 sec vs 5-10 sec) |

---

## 🎯 Roadmap Futur

### Version 2.1 (Q1 2026)
- [ ] Authentification utilisateur (login/register)
- [ ] Sauvegarde des recherches favorites
- [ ] Notifications email (nouvelles offres matchant profil)
- [ ] Dashboard candidat amélioré (historique analyses)

### Version 2.2 (Q2 2026)
- [ ] API REST complète avec Swagger documentation
- [ ] Nouveaux scrapers (Indeed, Monster, Welcome to the Jungle)
- [ ] Analyse CV multilingue (français, anglais, arabe)
- [ ] Recommandations personnalisées via machine learning

### Version 3.0 (Q3 2026)
- [ ] Application mobile (React Native / Flutter)
- [ ] Mode multi-tenants (entreprises)
- [ ] Analytics avancés (Tableau de bord RH)
- [ ] Intégration calendriers (planification entretiens)
- [ ] Système de chat (candidat ↔ recruteur)

---

## 🙏 Remerciements

- **Groq AI** : Pour l'API d'analyse ATS et Vision AI
- **Coursera** : Pour les 16,000+ cours accessibles
- **Bootstrap** : Framework CSS
- **Chart.js** : Bibliothèque de graphiques
- **Flask** : Framework web Python
- **ChromaDB** : Vector database performante
- **Sentence-Transformers** : Embeddings sémantiques de qualité

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

**Développé avec ❤️ par l'équipe JobMatch Pro**

*Dernière mise à jour : 2025-11-13*
