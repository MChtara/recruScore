# app.py - Application Flask pour la plateforme de matching d'emplois avec ATS

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import pandas as pd
import os
import json
import requests
from datetime import datetime
import tempfile
from werkzeug.utils import secure_filename
from ats_scorer import ATSScorer
import threading
import time
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Importer le gestionnaire de base de données pour le scraping
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'job_scraper'))
try:
    from job_scraper.db_manager import JobDatabase
    SCRAPING_ENABLED = True
except ImportError:
    SCRAPING_ENABLED = False
    print("Warning: Job scraping module not found. Scraping features disabled.")

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici_changez_moi'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size (augmenté pour les preuves)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['CV_FOLDER'] = 'user_cvs'  # Dossier pour stocker les CVs des utilisateurs
app.config['PROOFS_FOLDER'] = 'user_proofs'  # Dossier pour les preuves (certificats, attestations)

# Créer les dossiers nécessaires
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CV_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROOFS_FOLDER'], exist_ok=True)

# Initialiser l'analyseur ATS
ATS_API_KEY = os.getenv('ATS_API_KEY')
if not ATS_API_KEY:
    raise ValueError("❌ ERREUR: ATS_API_KEY non trouvée dans .env. Veuillez créer un fichier .env avec votre clé API Groq.")
ats_scorer = ATSScorer(ATS_API_KEY)

# ==================== CHROMADB STATUS ====================
chromadb_status = {
    'initialized': False,
    'embeddings_count': 0,
    'total_courses': 0,
    'migration_needed': False,
    'migration_running': False,
    'migration_progress': 0,
    'last_check': None,
    'error': None
}

def check_chromadb_status():
    """Vérifier le statut de ChromaDB au démarrage"""
    global chromadb_status
    try:
        # Vérifier que la base Coursera existe
        coursera_db_path = os.path.join('course_scraper', 'coursera_fast.db')
        if not os.path.exists(coursera_db_path):
            chromadb_status['error'] = 'Base de données Coursera non trouvée'
            return

        # Compter les cours dans SQLite
        import sqlite3
        conn = sqlite3.connect(coursera_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM courses")
        total_courses = cursor.fetchone()[0]
        conn.close()
        chromadb_status['total_courses'] = total_courses

        # Vérifier ChromaDB
        try:
            from course_scraper.course_embedding_store import CourseEmbeddingStore
            chroma_path = os.path.join('course_scraper', 'chroma_db')
            store = CourseEmbeddingStore(
                db_path=coursera_db_path,
                chroma_path=chroma_path
            )
            embeddings_count = store.get_count()
            chromadb_status['embeddings_count'] = embeddings_count
            chromadb_status['initialized'] = True
            chromadb_status['migration_needed'] = (embeddings_count == 0 and total_courses > 0)
            chromadb_status['last_check'] = datetime.now().isoformat()

            if chromadb_status['migration_needed']:
                print(f"\n⚠️  CHROMADB VIDE: {total_courses} cours disponibles mais 0 embeddings")
                print(f"   Allez sur http://localhost:5000/admin/chromadb pour migrer\n")
            else:
                print(f"\n✅ CHROMADB PRÊT: {embeddings_count}/{total_courses} embeddings\n")

        except ImportError:
            chromadb_status['error'] = 'Module ChromaDB non installé'
        except Exception as e:
            chromadb_status['error'] = str(e)

    except Exception as e:
        chromadb_status['error'] = str(e)
        print(f"[ERROR] Vérification ChromaDB échouée: {e}")

# Vérifier ChromaDB au démarrage
check_chromadb_status()

# Initialiser le gestionnaire de scraping
if SCRAPING_ENABLED:
    scraping_db = JobDatabase()
    # Statut global du scraping
    scraping_status = {
        'is_running': False,
        'current_source': None,
        'sources_status': {
            'google_jobs': {'status': 'idle', 'jobs_found': 0, 'message': '', 'progress': 0},
            'linkedin': {'status': 'idle', 'jobs_found': 0, 'message': '', 'progress': 0},
            'france_travail': {'status': 'idle', 'jobs_found': 0, 'message': '', 'progress': 0},
            'tunisie_travail': {'status': 'idle', 'jobs_found': 0, 'message': '', 'progress': 0}
        },
        'total_jobs': 0,
        'start_time': None,
        'end_time': None
    }
else:
    scraping_db = None
    scraping_status = {}

def load_scraping_config():
    """Charge la configuration de scraping depuis config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'job_scraper', 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "scrapers": {
                "google_jobs": {
                    "enabled": True,
                    "api_key": "",
                    "queries": [],
                    "max_results": 200,
                    "country": "tn",
                    "language": "fr"
                },
                "linkedin": {
                    "enabled": True,
                    "keywords": [],
                    "location": "Tunisia",
                    "pages": 2,
                    "get_descriptions": False
                },
                "france_travail": {
                    "enabled": True,
                    "client_id": "",
                    "client_secret": "",
                    "days": 7
                },
                "tunisie_travail": {
                    "enabled": True,
                    "ville": "tunis",
                    "secteur": "informatique",
                    "max_pages": 3
                }
            }
        }

def save_scraping_config(config):
    """Sauvegarde la configuration de scraping"""
    config_path = os.path.join(os.path.dirname(__file__), 'job_scraper', 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

class JobPlatform:
    def __init__(self):
        self.df = None
        self.db = JobDatabase() if SCRAPING_ENABLED else None
        self.load_data()

    def load_data(self):
        """Charger les données depuis la base de données jobs.db"""
        try:
            if not SCRAPING_ENABLED or self.db is None:
                print("WARNING: Scraping module non disponible, DataFrame vide")
                self.df = pd.DataFrame()
                return

            # Charger TOUS les jobs depuis jobs.db
            jobs = self.db.search_jobs(limit=50000)  # Augmenter la limite pour tout charger

            if not jobs:
                print("WARNING: Aucun job trouvé dans jobs.db")
                self.df = pd.DataFrame()
                return

            # Convertir en DataFrame pandas
            self.df = pd.DataFrame(jobs)
            
            # Nettoyer les données
            self.df = self.df.fillna('')
            
            # Nettoyer les colonnes salary pour éviter les erreurs
            self.df['salary'] = self.df['salary'].astype(str)
            
            print(f"Donnees chargees: {len(self.df)} offres d'emploi")
            print(f"Colonnes: {list(self.df.columns)}")

            # Ne pas valider les dates pour éviter les erreurs d'encodage
            # self._validate_dates()

        except Exception as e:
            print(f"Erreur lors du chargement des donnees: {e}")
            # Créer un DataFrame vide en cas d'erreur
            self.df = pd.DataFrame()
    
    def _validate_dates(self):
        """Valider et analyser les formats de dates"""
        if self.df.empty or 'date' not in self.df.columns:
            print("WARNING: Colonne 'date' non trouvee")
            return
        
        try:
            # Analyser les dates avec le format français
            dates_original = self.df['date'].dropna()
            dates_converted = pd.to_datetime(dates_original, errors='coerce', dayfirst=True)
            
            total_dates = len(dates_original)
            valid_dates = len(dates_converted.dropna())
            
            print(f"Validation des dates:")
            print(f"   Total: {total_dates}")
            print(f"   Valides: {valid_dates} ({(valid_dates/total_dates)*100:.1f}%)")
            
            if valid_dates > 0:
                valid_dates_series = dates_converted.dropna()
                min_date = valid_dates_series.min()
                max_date = valid_dates_series.max()
                
                print(f"   Plage: {min_date.strftime('%d/%m/%Y')} → {max_date.strftime('%d/%m/%Y')}")
                
                # Analyser la distribution
                from datetime import datetime, timedelta
                today = datetime.now()
                
                recent_counts = {
                    "24h": len(valid_dates_series[valid_dates_series >= pd.Timestamp(today - timedelta(days=1))]),
                    "7j": len(valid_dates_series[valid_dates_series >= pd.Timestamp(today - timedelta(days=7))]),
                    "30j": len(valid_dates_series[valid_dates_series >= pd.Timestamp(today - timedelta(days=30))]),
                    "90j": len(valid_dates_series[valid_dates_series >= pd.Timestamp(today - timedelta(days=90))])
                }
                
                print(f"   Répartition récente: 24h={recent_counts['24h']}, 7j={recent_counts['7j']}, 30j={recent_counts['30j']}, 90j={recent_counts['90j']}")
            else:
                print("   WARNING: Aucune date valide detectee")
                
        except Exception as e:
            print(f"ERROR: Erreur validation dates: {e}")
    
    def get_filter_options(self):
        """Obtenir les options disponibles pour chaque filtre"""
        if self.df.empty:
            return {}
            
        filters = {}
        
        # Locations uniques (limiter pour éviter les problèmes de performance)
        locations = self.df['location'].value_counts().head(20)
        filters['locations'] = list(locations.index) if not locations.empty else []
        
        # Companies uniques
        companies = self.df['company'].value_counts().head(30)
        filters['companies'] = list(companies.index) if not companies.empty else []
        
        # Job types
        job_types = self.df['job_type'].value_counts()
        filters['job_types'] = list(job_types.index) if not job_types.empty else []
        
        # Contract types
        contract_types = self.df['contrat'].value_counts().head(15)
        filters['contract_types'] = list(contract_types.index) if not contract_types.empty else []
        
        # Sources
        sources = self.df['source'].value_counts()
        filters['sources'] = list(sources.index) if not sources.empty else []
        
        # Date ranges - Analyser les dates disponibles
        filters['date_ranges'] = self._get_date_ranges()
        
        return filters
    
    def _get_date_ranges(self):
        """Générer les options de filtres par date"""
        if self.df.empty or 'date' not in self.df.columns:
            return []
        
        from datetime import datetime, timedelta
        
        try:
            # Convertir les dates en format datetime avec format français
            dates_series = pd.to_datetime(self.df['date'], errors='coerce', dayfirst=True)
            dates_series = dates_series.dropna()
            
            if dates_series.empty:
                return []
            
            # Date la plus récente et la plus ancienne
            max_date = dates_series.max()
            min_date = dates_series.min()
            today = datetime.now()
            
            # Générer les options de filtre
            ranges = []
            
            # Dernières 24h
            yesterday = today - timedelta(days=1)
            if max_date >= pd.Timestamp(yesterday):
                count_24h = len(dates_series[dates_series >= pd.Timestamp(yesterday)])
                ranges.append({
                    'label': f'🆕 Dernières 24h ({count_24h})',
                    'value': '1day',
                    'start': yesterday.strftime('%Y-%m-%d'),
                    'end': today.strftime('%Y-%m-%d')
                })
            
            # Dernière semaine
            week_ago = today - timedelta(days=7)
            if max_date >= pd.Timestamp(week_ago):
                count_week = len(dates_series[dates_series >= pd.Timestamp(week_ago)])
                ranges.append({
                    'label': f'📅 Cette semaine ({count_week})',
                    'value': '1week',
                    'start': week_ago.strftime('%Y-%m-%d'),
                    'end': today.strftime('%Y-%m-%d')
                })
            
            # Dernier mois
            month_ago = today - timedelta(days=30)
            if max_date >= pd.Timestamp(month_ago):
                count_month = len(dates_series[dates_series >= pd.Timestamp(month_ago)])
                ranges.append({
                    'label': f'📆 Ce mois ({count_month})',
                    'value': '1month',
                    'start': month_ago.strftime('%Y-%m-%d'),
                    'end': today.strftime('%Y-%m-%d')
                })
            
            # Derniers 3 mois
            three_months_ago = today - timedelta(days=90)
            if max_date >= pd.Timestamp(three_months_ago):
                count_3months = len(dates_series[dates_series >= pd.Timestamp(three_months_ago)])
                ranges.append({
                    'label': f'🗓️ 3 mois ({count_3months})',
                    'value': '3months',
                    'start': three_months_ago.strftime('%Y-%m-%d'),
                    'end': today.strftime('%Y-%m-%d')
                })
            
            # Cette année
            year_start = datetime(today.year, 1, 1)
            if max_date >= pd.Timestamp(year_start):
                count_year = len(dates_series[dates_series >= pd.Timestamp(year_start)])
                ranges.append({
                    'label': f'📅 {today.year} ({count_year})',
                    'value': 'thisyear',
                    'start': year_start.strftime('%Y-%m-%d'),
                    'end': today.strftime('%Y-%m-%d')
                })
            
            # Toutes les dates
            ranges.append({
                'label': f'🗓️ Toutes les dates ({len(dates_series)})',
                'value': 'all',
                'start': min_date.strftime('%Y-%m-%d'),
                'end': max_date.strftime('%Y-%m-%d')
            })
            
            return ranges
            
        except Exception as e:
            print(f"Erreur calcul date ranges: {e}")
            return []
    
    def get_job_by_index(self, index: int) -> dict:
        """Récupérer une offre par son index"""
        if self.df.empty:
            return None
            
        try:
            # Vérifier si l'index existe dans le DataFrame
            if index in self.df.index:
                job = self.df.loc[index].to_dict()
                return job
            elif 0 <= index < len(self.df):
                # Fallback: utiliser l'index positionnel
                job = self.df.iloc[index].to_dict()
                return job
            else:
                return None
        except (IndexError, KeyError):
            return None
    
    def search_jobs(self, keyword='', location='', company='', job_type='', 
                   contract_type='', source='', date_range='', custom_start_date='', 
                   custom_end_date='', page=1, per_page=20):
        """Rechercher et filtrer les offres d'emploi"""
        
        if self.df.empty:
            return [], 0, {}
        
        try:
            # Copie du DataFrame pour filtrer
            filtered_df = self.df.copy()
            
            # Filtre par mot-clé (titre et description)
            if keyword:
                keyword_lower = keyword.lower()
                mask = (
                    filtered_df['title'].str.lower().str.contains(keyword_lower, na=False) |
                    filtered_df['description'].str.lower().str.contains(keyword_lower, na=False)
                )
                filtered_df = filtered_df[mask]
            
            # Filtre par localisation
            if location:
                filtered_df = filtered_df[filtered_df['location'].str.contains(location, na=False)]
            
            # Filtre par entreprise
            if company:
                filtered_df = filtered_df[filtered_df['company'] == company]
            
            # Filtre par type d'emploi
            if job_type:
                filtered_df = filtered_df[filtered_df['job_type'] == job_type]
            
            # Filtre par type de contrat
            if contract_type:
                filtered_df = filtered_df[filtered_df['contrat'] == contract_type]
            
            # Filtre par source
            if source:
                filtered_df = filtered_df[filtered_df['source'] == source]
            
            # Filtre par date
            filtered_df = self._apply_date_filter(filtered_df, date_range, custom_start_date, custom_end_date)
            
            # Tri par date (plus récent en premier)
            try:
                # Convertir les dates pour le tri avec format français
                filtered_df['date_parsed'] = pd.to_datetime(filtered_df['date'], errors='coerce', dayfirst=True)
                filtered_df = filtered_df.sort_values('date_parsed', ascending=False, na_position='last')
                # Supprimer la colonne temporaire
                filtered_df = filtered_df.drop('date_parsed', axis=1)
            except Exception as e:
                print(f"Erreur tri par date: {e}")
                pass
            
            # Pagination
            total = len(filtered_df)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            jobs_page = filtered_df.iloc[start_idx:end_idx]
            
            # Convertir en dictionnaire avec indices originaux
            jobs = []
            for idx, (original_idx, job) in enumerate(jobs_page.iterrows()):
                job_dict = job.to_dict()
                # Utiliser l'index pandas directement
                job_dict['original_index'] = original_idx
                # Tronquer la description pour l'affichage
                if len(job_dict['description']) > 300:
                    job_dict['description_short'] = job_dict['description'][:300] + '...'
                else:
                    job_dict['description_short'] = job_dict['description']
                jobs.append(job_dict)
            
            # Statistiques
            stats = {
                'total_jobs': total,
                'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
                'current_page': page,
                'per_page': per_page
            }
            
            return jobs, total, stats
        
        except Exception as e:
            print(f"Erreur dans search_jobs: {e}")
            return [], 0, {
                'total_jobs': 0,
                'total_pages': 1,
                'current_page': 1,
                'per_page': per_page
            }
    
    def _apply_date_filter(self, df, date_range, custom_start_date, custom_end_date):
        """Appliquer le filtre par date avec format français"""
        if df.empty or 'date' not in df.columns:
            return df
        
        try:
            from datetime import datetime, timedelta
            
            # Créer une copie pour éviter les modifications
            df_copy = df.copy()
            
            # Convertir les dates avec format français (dayfirst=True)
            df_copy['date_parsed'] = pd.to_datetime(df_copy['date'], errors='coerce', dayfirst=True)
            
            # Log des conversions pour debugging
            total_dates = len(df_copy)
            valid_dates = len(df_copy.dropna(subset=['date_parsed']))
            if valid_dates < total_dates:
                print(f"WARNING: Dates converties: {valid_dates}/{total_dates} ({(valid_dates/total_dates)*100:.1f}%)")
            
            # Supprimer les lignes avec des dates invalides
            df_copy = df_copy.dropna(subset=['date_parsed'])
            
            if df_copy.empty:
                print("ERROR: Aucune date valide apres conversion")
                return df.iloc[0:0]  # DataFrame vide mais avec les bonnes colonnes
            
            today = datetime.now()
            
            # Appliquer le filtre selon le type
            if date_range and date_range != 'all':
                start_date = None
                end_date = today
                
                if date_range == '1day':
                    start_date = today - timedelta(days=1)
                elif date_range == '1week':
                    start_date = today - timedelta(days=7)
                elif date_range == '1month':
                    start_date = today - timedelta(days=30)
                elif date_range == '3months':
                    start_date = today - timedelta(days=90)
                elif date_range == 'thisyear':
                    start_date = datetime(today.year, 1, 1)
                else:
                    # Format non reconnu - retourner sans filtre
                    print(f"WARNING: Format de date_range non reconnu: {date_range}")
                    return df_copy.drop('date_parsed', axis=1)
                
                if start_date:
                    # Convertir en pandas Timestamp pour la comparaison
                    start_ts = pd.Timestamp(start_date)
                    end_ts = pd.Timestamp(end_date)
                    
                    # Filtrer par la plage de dates
                    mask = (df_copy['date_parsed'] >= start_ts) & (df_copy['date_parsed'] <= end_ts)
                    df_filtered = df_copy[mask]
                    
                    print(f"Filtre {date_range}: {len(df_filtered)} offres trouvees")
                    df_copy = df_filtered
            
            # Filtre par dates personnalisées
            elif custom_start_date or custom_end_date:
                if custom_start_date:
                    try:
                        start_date = datetime.strptime(custom_start_date, '%Y-%m-%d')
                        start_ts = pd.Timestamp(start_date)
                        mask_start = df_copy['date_parsed'] >= start_ts
                        df_copy = df_copy[mask_start]
                        print(f"Filtre depuis {custom_start_date}: {len(df_copy)} offres")
                    except ValueError as e:
                        print(f"ERROR: Date de debut invalide {custom_start_date}: {e}")
                
                if custom_end_date:
                    try:
                        end_date = datetime.strptime(custom_end_date, '%Y-%m-%d')
                        end_ts = pd.Timestamp(end_date)
                        mask_end = df_copy['date_parsed'] <= end_ts
                        df_copy = df_copy[mask_end]
                        print(f"Filtre jusqu'a {custom_end_date}: {len(df_copy)} offres")
                    except ValueError as e:
                        print(f"ERROR: Date de fin invalide {custom_end_date}: {e}")
            
            # Supprimer la colonne temporaire et retourner
            return df_copy.drop('date_parsed', axis=1, errors='ignore')
            
        except Exception as e:
            print(f"ERROR: Erreur dans _apply_date_filter: {e}")
            print(f"   Type d'erreur: {type(e).__name__}")
            return df

# Instance globale
job_platform = JobPlatform()

@app.route('/upload-cv', methods=['POST'])
def upload_cv():
    """Gérer l'upload initial du CV utilisateur"""
    if 'cv_file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    file = request.files['cv_file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    if file and ats_scorer.allowed_file(file.filename):
        try:
            # Générer un ID unique pour cette session
            import uuid
            session_id = session.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
                session['session_id'] = session_id

            # Sauvegarder le fichier avec l'ID de session
            filename = secure_filename(file.filename)
            extension = filename.rsplit('.', 1)[1].lower()
            cv_filename = f"{session_id}.{extension}"
            cv_path = os.path.join(app.config['CV_FOLDER'], cv_filename)

            # Supprimer l'ancien CV si existe
            for old_file in os.listdir(app.config['CV_FOLDER']):
                if old_file.startswith(session_id):
                    os.remove(os.path.join(app.config['CV_FOLDER'], old_file))

            file.save(cv_path)

            # Extraire le texte du CV pour vérification
            cv_texte = ats_scorer.extraire_texte_fichier(cv_path)

            if not cv_texte or len(cv_texte.strip()) < 50:
                os.remove(cv_path)
                return jsonify({'success': False, 'error': 'Impossible d\'extraire le texte du CV ou CV trop court'}), 400

            # Sauvegarder les infos en session (sans le texte pour éviter cookie trop grand)
            session['cv_uploaded'] = True
            session['cv_filename'] = filename
            session['cv_path'] = cv_path
            # Ne PAS stocker cv_text en session (trop volumineux)

            return jsonify({
                'success': True,
                'message': 'CV uploadé avec succès',
                'filename': filename
            })

        except Exception as e:
            return jsonify({'success': False, 'error': f'Erreur lors du traitement: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'error': 'Type de fichier non supporté'}), 400

@app.route('/remove-cv', methods=['POST'])
def remove_cv():
    """Supprimer le CV uploadé"""
    try:
        if 'cv_path' in session and os.path.exists(session['cv_path']):
            os.remove(session['cv_path'])

        session.pop('cv_uploaded', None)
        session.pop('cv_filename', None)
        session.pop('cv_path', None)
        session.pop('cv_text', None)

        return jsonify({'success': True, 'message': 'CV supprimé avec succès'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/check-cv')
def check_cv():
    """Vérifier si un CV est déjà uploadé"""
    return jsonify({
        'cv_uploaded': session.get('cv_uploaded', False),
        'cv_filename': session.get('cv_filename', '')
    })

@app.route('/my-cv')
def my_cv():
    """Page dédiée pour gérer son CV"""
    # Vérifier d'abord l'existence du fichier avant la session
    session_id = session.get('session_id')
    cv_path = session.get('cv_path', '')
    cv_filename = session.get('cv_filename', '')

    # Si on a un session_id, chercher un fichier CV correspondant
    if session_id and not cv_path:
        cv_folder = app.config['CV_FOLDER']
        for file in os.listdir(cv_folder):
            if file.startswith(session_id):
                cv_path = os.path.join(cv_folder, file)
                cv_filename = file.split('_', 1)[1] if '_' in file else file
                session['cv_path'] = cv_path
                session['cv_filename'] = cv_filename
                session['cv_uploaded'] = True
                break

    cv_uploaded = session.get('cv_uploaded', False) or (cv_path and os.path.exists(cv_path))

    return render_template('upload_cv_page.html',
                         cv_uploaded=cv_uploaded,
                         cv_filename=cv_filename)

@app.route('/test-jobs')
def test_jobs():
    """Page de test pour vérifier l'affichage des offres"""
    jobs, total, stats = job_platform.search_jobs(page=1, per_page=10)

    return render_template('test_jobs.html',
                         jobs=jobs,
                         stats=stats)

@app.route('/')
def index():
    """Page d'accueil avec liste des offres"""

    # Récupérer les paramètres de recherche
    keyword = request.args.get('keyword', '')
    location = request.args.get('location', '')
    company = request.args.get('company', '')
    job_type = request.args.get('job_type', '')
    contract_type = request.args.get('contract_type', '')
    source = request.args.get('source', '')
    date_range = request.args.get('date_range', '')
    custom_start_date = request.args.get('custom_start_date', '')
    custom_end_date = request.args.get('custom_end_date', '')
    page = int(request.args.get('page', 1))

    # Rechercher les offres
    jobs, total, stats = job_platform.search_jobs(
        keyword=keyword,
        location=location,
        company=company,
        job_type=job_type,
        contract_type=contract_type,
        source=source,
        date_range=date_range,
        custom_start_date=custom_start_date,
        custom_end_date=custom_end_date,
        page=page
    )

    # Obtenir les options de filtres
    filters = job_platform.get_filter_options()

    # Vérifier si le CV est uploadé
    cv_uploaded = session.get('cv_uploaded', False)
    cv_filename = session.get('cv_filename', '')

    return render_template('index.html',
                         jobs=jobs,
                         total_jobs=total,
                         companies_count=len(filters.get('companies', [])),
                         stats=stats,
                         filters=filters,
                         scraping_enabled=SCRAPING_ENABLED,
                         keyword=keyword,
                         location=location,
                         job_type=job_type,
                         source=source)

@app.route('/api/search')
def api_search():
    """API pour recherche AJAX"""
    
    keyword = request.args.get('keyword', '')
    location = request.args.get('location', '')
    company = request.args.get('company', '')
    job_type = request.args.get('job_type', '')
    contract_type = request.args.get('contract_type', '')
    source = request.args.get('source', '')
    date_range = request.args.get('date_range', '')
    custom_start_date = request.args.get('custom_start_date', '')
    custom_end_date = request.args.get('custom_end_date', '')
    page = int(request.args.get('page', 1))
    
    jobs, total, stats = job_platform.search_jobs(
        keyword=keyword,
        location=location,
        company=company,
        job_type=job_type,
        contract_type=contract_type,
        source=source,
        date_range=date_range,
        custom_start_date=custom_start_date,
        custom_end_date=custom_end_date,
        page=page
    )
    
    return jsonify({
        'jobs': jobs,
        'stats': stats,
        'success': True
    })

@app.route('/api/recommend-courses', methods=['POST'])
def recommend_courses():
    """API pour recommander des cours Coursera basés sur les compétences manquantes - OPTIMISÉ CHROMADB"""
    try:
        data = request.json
        missing_skills = data.get('missing_skills', [])
        job_id = data.get('job_id')

        # DEBUG: Afficher les compétences manquantes reçues
        print(f"\n[DEBUG API] Compétences manquantes reçues: {missing_skills}")
        print(f"[DEBUG API] Nombre de compétences: {len(missing_skills)}")

        if not missing_skills:
            return jsonify({
                'success': False,
                'error': 'Aucune compétence manquante fournie'
            }), 400

        # Vérifier que la base de données Coursera existe
        coursera_db_path = os.path.join('course_scraper', 'coursera_fast.db')
        if not os.path.exists(coursera_db_path):
            return jsonify({
                'success': False,
                'error': 'Base de données Coursera non disponible'
            }), 404

        recommendations = []

        # NOUVEAU : Utiliser la fonction optimisée avec ChromaDB
        # Pour chaque compétence manquante, récupérer TOUS les cours recommandés
        for skill in missing_skills:  # TOUS les compétences (pas de limite)
            try:
                # Utiliser la fonction recommander_cours() qui utilise ChromaDB
                # Récupérer exactement 3 cours par compétence
                print(f"[DEBUG] Recherche de cours pour: {skill}")
                cours_list = ats_scorer.recommander_cours(
                    competence=skill,
                    db_path=coursera_db_path,
                    top_n=3,  # Top 3 cours par compétence comme demandé
                    use_chromadb=True  # Force l'utilisation de ChromaDB
                )
                print(f"[DEBUG] {len(cours_list)} cours trouvés pour '{skill}'")

                # Convertir le format pour l'API
                for cours in cours_list:
                    course = {
                        'title': cours.get('titre', ''),
                        'description': cours.get('description', ''),
                        'partner': cours.get('organisme', 'Coursera'),
                        'url': cours.get('url', ''),
                        'difficulty': cours.get('difficulte', 'Non spécifié'),
                        'duration': cours.get('duree', 'Non spécifié'),
                        'language': 'en',  # Par défaut
                        'matched_skill': skill,
                        'score_similarite': cours.get('score_similarite', 0)
                    }

                    # NOUVEAU: Permettre les doublons entre compétences différentes
                    # Un cours peut être pertinent pour plusieurs compétences
                    # On ne vérifie les doublons QUE pour la même compétence
                    same_skill_courses = [r for r in recommendations if r['matched_skill'] == skill]
                    if not any(r['url'] == course['url'] for r in same_skill_courses):
                        recommendations.append(course)
                        print(f"  [DEBUG] Ajouté: {course['title'][:50]}... pour '{skill}'")

            except Exception as e:
                print(f"[ERROR] Erreur recommandation pour '{skill}': {e}")
                # Continuer avec les autres compétences même en cas d'erreur
                continue

        # Pas de limite globale - on garde tous les cours (3 par compétence)
        # Trier par score de similarité décroissant
        recommendations.sort(key=lambda x: x.get('score_similarite', 0), reverse=True)

        # DEBUG: Afficher le résumé
        print(f"\n[DEBUG API] Résumé des recommandations:")
        print(f"  - Total de compétences traitées: {len(missing_skills)}")
        print(f"  - Total de cours recommandés: {len(recommendations)}")

        # Compter par compétence
        from collections import Counter
        skills_count = Counter([r['matched_skill'] for r in recommendations])
        for skill, count in skills_count.items():
            print(f"  - {skill}: {count} cours")

        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'missing_skills': missing_skills,
            'total_skills': len(missing_skills),
            'total_courses': len(recommendations),
            'used_chromadb': True  # Indiquer qu'on utilise ChromaDB
        })

    except Exception as e:
        import traceback
        print(f"[ERROR] /api/recommend-courses: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    """Page de détail d'une offre avec analyse automatique si CV disponible"""
    job = job_platform.get_job_by_index(job_id)
    if not job:
        flash("Offre d'emploi non trouvée", "error")
        return redirect(url_for('index'))

    # Vérifier si un CV est disponible
    cv_uploaded = session.get('cv_uploaded', False)
    cv_path = session.get('cv_path', '')
    analyse = None
    rapport_html = None

    if cv_uploaded and cv_path and os.path.exists(cv_path):
        # Lire le texte du CV depuis le fichier
        try:
            cv_text = ats_scorer.extraire_texte_fichier(cv_path)
            if cv_text:
                # Analyser automatiquement le CV avec l'offre
                analyse = ats_scorer.analyser_cv_avec_offre(cv_text, job)
                if 'erreur' not in analyse:
                    rapport_html = ats_scorer.generer_rapport_html(analyse)
        except Exception as e:
            flash(f'Erreur lors de l\'analyse automatique: {str(e)}', 'warning')

    return render_template('job_detail.html',
                         job=job,
                         job_id=job_id,
                         cv_uploaded=cv_uploaded,
                         cv_filename=session.get('cv_filename', ''),
                         analyse=analyse,
                         rapport_html=rapport_html)

@app.route('/analyze-cv/<int:job_id>', methods=['GET', 'POST'])
def analyze_cv(job_id):
    """Analyser un CV par rapport à une offre d'emploi"""
    job = job_platform.get_job_by_index(job_id)
    if not job:
        flash("Offre d'emploi non trouvée", "error")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Vérifier si un fichier a été uploadé
        if 'cv_file' not in request.files:
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)
        
        file = request.files['cv_file']
        
        if file.filename == '':
            flash('Aucun fichier sélectionné', 'error')
            return redirect(request.url)
        
        if file and ats_scorer.allowed_file(file.filename):
            try:
                # Sauvegarder le fichier temporairement
                filename = secure_filename(file.filename)
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(temp_path)
                
                # Extraire le texte du CV
                cv_texte = ats_scorer.extraire_texte_fichier(temp_path)
                
                if not cv_texte:
                    flash('Impossible d\'extraire le texte du CV', 'error')
                    os.remove(temp_path)
                    return redirect(request.url)
                
                # Analyser avec l'offre
                analyse = ats_scorer.analyser_cv_avec_offre(cv_texte, job)
                
                # Nettoyer le fichier temporaire
                os.remove(temp_path)
                
                if 'erreur' in analyse:
                    flash(f'Erreur lors de l\'analyse: {analyse["erreur"]}', 'error')
                    return redirect(request.url)
                
                # Générer le rapport HTML
                rapport_html = ats_scorer.generer_rapport_html(analyse)
                
                return render_template('cv_analysis.html', 
                                     job=job, 
                                     job_id=job_id,
                                     analyse=analyse,
                                     rapport_html=rapport_html)
                
            except Exception as e:
                flash(f'Erreur lors du traitement: {str(e)}', 'error')
                # Nettoyer le fichier si il existe
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                return redirect(request.url)
        else:
            flash('Type de fichier non supporté. Utilisez PDF, DOC, DOCX ou TXT', 'error')
            return redirect(request.url)
    
    # GET request - afficher le formulaire d'upload
    return render_template('cv_upload.html', job=job, job_id=job_id)

@app.route('/stats')
def stats():
    """Page de statistiques"""
    if job_platform.df.empty:
        return render_template('stats.html', stats={})
    
    df = job_platform.df
    
    try:
        # Calculs sécurisés pour éviter les erreurs
        locations_data = df['location'].value_counts().head(10)
        companies_data = df['company'].value_counts().head(10)
        job_types_data = df['job_type'].value_counts()
        sources_data = df['source'].value_counts()
        contract_types_data = df['contrat'].value_counts().head(10)
        
        stats_data = {
            'total_jobs': len(df),
            'locations': locations_data.to_dict() if not locations_data.empty else {},
            'companies': companies_data.to_dict() if not companies_data.empty else {},
            'job_types': job_types_data.to_dict() if not job_types_data.empty else {},
            'sources': sources_data.to_dict() if not sources_data.empty else {},
            'contract_types': contract_types_data.to_dict() if not contract_types_data.empty else {}
        }
        
        # Debug: Afficher les données pour vérification
        print(f"📊 Stats calculées:")
        print(f"   Total jobs: {stats_data['total_jobs']}")
        print(f"   Locations: {len(stats_data['locations'])} entries")
        print(f"   Companies: {len(stats_data['companies'])} entries")
        print(f"   Job types: {len(stats_data['job_types'])} entries")
        print(f"   Sources: {len(stats_data['sources'])} entries")
        print(f"   Contracts: {len(stats_data['contract_types'])} entries")
        
        # Vérifier si on a des données - vérifier la longueur des dictionnaires
        has_any_data = bool(
            stats_data['locations'] or
            stats_data['companies'] or
            stats_data['job_types'] or
            stats_data['sources']
        )

        if not has_any_data:
            print("WARNING: Aucune donnee pour les graphiques")
            stats_data['has_data'] = False
        else:
            print(f"✅ Données disponibles pour les graphiques")
            stats_data['has_data'] = True
        
    except Exception as e:
        print(f"ERROR: Erreur calcul stats: {e}")
        stats_data = {
            'total_jobs': len(df) if not df.empty else 0,
            'locations': {},
            'companies': {},
            'job_types': {},
            'sources': {},
            'contract_types': {},
            'has_data': False
        }
    
    return render_template('stats.html', stats=stats_data)

@app.route('/verify-cv', methods=['GET'])
def verify_cv():
    """Extraire et afficher les certificats/attestations du CV pour vérification"""
    # Vérifier d'abord l'existence du fichier avant la session
    session_id = session.get('session_id')
    cv_path = session.get('cv_path', '')

    # Si on a un session_id, chercher un fichier CV correspondant
    if session_id and not cv_path:
        cv_folder = app.config['CV_FOLDER']
        for file in os.listdir(cv_folder):
            if file.startswith(session_id):
                cv_path = os.path.join(cv_folder, file)
                session['cv_path'] = cv_path
                session['cv_uploaded'] = True
                break

    cv_uploaded = session.get('cv_uploaded', False) or (cv_path and os.path.exists(cv_path))

    if not cv_uploaded and not (cv_path and os.path.exists(cv_path)):
        flash('Veuillez d\'abord uploader votre CV', 'warning')
        return redirect(url_for('my_cv'))

    if not cv_path or not os.path.exists(cv_path):
        flash('Fichier CV introuvable', 'error')
        return redirect(url_for('my_cv'))

    try:
        # Extraire le texte du CV
        cv_text = ats_scorer.extraire_texte_fichier(cv_path)

        # Extraire les certificats/attestations via LLM
        credentials = ats_scorer.extraire_certificats_attestations(cv_text)

        if 'erreur' in credentials:
            flash(f'Erreur lors de l\'extraction: {credentials["erreur"]}', 'error')
            return redirect(url_for('my_cv'))

        # Sauvegarder les credentials en session
        session['credentials_extracted'] = credentials

        return render_template('verify_credentials.html',
                             credentials=credentials,
                             cv_filename=session.get('cv_filename', ''))

    except Exception as e:
        flash(f'Erreur lors de la vérification: {str(e)}', 'error')
        return redirect(url_for('my_cv'))

@app.route('/upload-proof/<category>/<int:item_index>', methods=['POST'])
def upload_proof(category, item_index):
    """Gérer l'upload des preuves pour un certificat/attestation spécifique"""
    if 'proof_file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    file = request.files['proof_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    if not ats_scorer.allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Type de fichier non autorisé. Formats acceptés: PDF, JPG, PNG'}), 400

    try:
        # Créer un sous-dossier pour l'utilisateur
        session_id = session.get('session_id', 'default')
        user_proof_folder = os.path.join(app.config['PROOFS_FOLDER'], session_id, category)
        os.makedirs(user_proof_folder, exist_ok=True)

        # Sauvegarder le fichier
        filename = secure_filename(f"{item_index}_{file.filename}")
        filepath = os.path.join(user_proof_folder, filename)
        file.save(filepath)

        # Si c'est un PDF, créer aussi une version image pour l'affichage
        extension = filename.rsplit('.', 1)[1].lower()
        image_preview_path = None

        if extension == 'pdf':
            image_path = ats_scorer.pdf_to_image(filepath)
            if image_path:
                # Sauvegarder l'image de prévisualisation dans le même dossier
                preview_filename = f"{item_index}_preview.png"
                preview_filepath = os.path.join(user_proof_folder, preview_filename)

                # Copier l'image temporaire vers le dossier permanent
                import shutil
                shutil.copy(image_path, preview_filepath)

                # Nettoyer l'image temporaire
                try:
                    os.remove(image_path)
                except:
                    pass

                image_preview_path = preview_filepath

        # Enregistrer dans la session
        if 'uploaded_proofs' not in session:
            session['uploaded_proofs'] = {}

        proof_key = f"{category}_{item_index}"
        session['uploaded_proofs'][proof_key] = {
            'filename': filename,
            'filepath': filepath,
            'image_preview_path': image_preview_path,
            'uploaded_at': datetime.now().isoformat()
        }
        session.modified = True

        return jsonify({
            'success': True,
            'message': 'Preuve uploadée avec succès',
            'filename': filename,
            'has_preview': image_preview_path is not None
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/proof-preview/<category>/<int:item_index>')
def proof_preview(category, item_index):
    """Servir l'image de prévisualisation d'une preuve (image ou PDF converti)"""
    proof_key = f"{category}_{item_index}"
    uploaded_proofs = session.get('uploaded_proofs', {})

    if proof_key not in uploaded_proofs:
        return "Preuve non trouvée", 404

    proof_info = uploaded_proofs[proof_key]

    # Si c'est un PDF et qu'on a une preview
    if proof_info.get('image_preview_path') and os.path.exists(proof_info['image_preview_path']):
        from flask import send_file
        return send_file(proof_info['image_preview_path'], mimetype='image/png')

    # Sinon, servir le fichier original (si c'est déjà une image)
    elif os.path.exists(proof_info['filepath']):
        extension = proof_info['filepath'].rsplit('.', 1)[1].lower()
        if extension in ['jpg', 'jpeg', 'png']:
            from flask import send_file
            mimetype = f'image/{extension}' if extension != 'jpg' else 'image/jpeg'
            return send_file(proof_info['filepath'], mimetype=mimetype)

    return "Aperçu non disponible", 404

@app.route('/verify-proof/<category>/<int:item_index>', methods=['POST'])
def verify_proof(category, item_index):
    """Vérifier automatiquement une preuve uploadée - VERSION AMÉLIORÉE"""
    proof_key = f"{category}_{item_index}"
    uploaded_proofs = session.get('uploaded_proofs', {})

    print(f"\n=== VERIFY PROOF DEBUG ===")
    print(f"Category: {category}, Index: {item_index}")
    print(f"Proof key: {proof_key}")
    print(f"Uploaded proofs keys: {list(uploaded_proofs.keys())}")

    if proof_key not in uploaded_proofs:
        print(f"ERROR: Proof key '{proof_key}' not found in uploaded_proofs!")
        return jsonify({'success': False, 'error': f'Aucune preuve uploadée pour cet élément (clé: {proof_key})'}), 400

    try:
        # Récupérer les informations de la preuve
        proof_info = uploaded_proofs[proof_key]
        proof_filepath = proof_info['filepath']
        print(f"Proof filepath: {proof_filepath}")
        print(f"File exists: {os.path.exists(proof_filepath)}")

        # Récupérer le claim original
        credentials = session.get('credentials_extracted', {})
        category_items = credentials.get(category, [])
        print(f"Category items count: {len(category_items)}")

        if item_index >= len(category_items):
            return jsonify({'success': False, 'error': 'Élément introuvable'}), 400

        claim = category_items[item_index]
        print(f"Claim: {claim.get('nom', 'N/A')}")

        # Vérifier via VLM (Vision Language Model)
        # Accepte PDF ou images directement
        verification_result = ats_scorer.verifier_document_vlm(claim, proof_filepath, category)

        if 'erreur' in verification_result:
            return jsonify({'success': False, 'error': verification_result['erreur']}), 500

        # Enregistrer le résultat
        if 'verification_results' not in session:
            session['verification_results'] = {}

        session['verification_results'][proof_key] = verification_result
        session.modified = True

        return jsonify({
            'success': True,
            'verification': verification_result
        })

    except Exception as e:
        import sys
        print(f"EXCEPTION IN VERIFY_PROOF: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/verify-all-documents', methods=['POST'])
def verify_all_documents():
    """Vérifier TOUS les documents un par un de manière séquentielle"""
    uploaded_proofs = session.get('uploaded_proofs', {})
    credentials = session.get('credentials_extracted', {})

    if not uploaded_proofs:
        return jsonify({'success': False, 'error': 'Aucun document uploadé'}), 400

    if not credentials:
        return jsonify({'success': False, 'error': 'Aucune credential extraite du CV'}), 400

    results = {
        'total_documents': len(uploaded_proofs),
        'verifies': 0,
        'erreurs': 0,
        'details': []
    }

    # Vérifier chaque document UN PAR UN
    for proof_key, proof_info in uploaded_proofs.items():
        try:
            # Parser le proof_key (format: "category_index")
            parts = proof_key.split('_')
            category = '_'.join(parts[:-1])  # Récupérer toute la catégorie
            item_index = int(parts[-1])

            # Récupérer le claim
            category_items = credentials.get(category, [])
            if item_index >= len(category_items):
                results['erreurs'] += 1
                results['details'].append({
                    'proof_key': proof_key,
                    'status': 'error',
                    'message': 'Claim introuvable'
                })
                continue

            claim = category_items[item_index]

            # Vérifier le document avec VLM
            verification = ats_scorer.verifier_document_vlm(claim, proof_info['filepath'], category)

            if 'erreur' in verification:
                results['erreurs'] += 1
                results['details'].append({
                    'proof_key': proof_key,
                    'claim_name': claim.get('nom', 'N/A'),
                    'status': 'error',
                    'message': verification['erreur']
                })
            else:
                results['verifies'] += 1
                results['details'].append({
                    'proof_key': proof_key,
                    'claim_name': claim.get('nom', 'N/A'),
                    'status': 'success',
                    'verification': verification
                })

                # Sauvegarder le résultat en session
                if 'verification_results' not in session:
                    session['verification_results'] = {}
                session['verification_results'][proof_key] = verification

        except Exception as e:
            results['erreurs'] += 1
            results['details'].append({
                'proof_key': proof_key,
                'status': 'error',
                'message': str(e)
            })

    session.modified = True

    return jsonify({
        'success': True,
        'results': results
    })

@app.route('/technical-tests', methods=['GET'])
def technical_tests():
    """Générer et afficher des tests techniques basés sur le CV"""
    # Vérifier d'abord l'existence du fichier avant la session
    session_id = session.get('session_id')
    cv_path = session.get('cv_path', '')

    # Si on a un session_id, chercher un fichier CV correspondant
    if session_id and not cv_path:
        cv_folder = app.config['CV_FOLDER']
        for file in os.listdir(cv_folder):
            if file.startswith(session_id):
                cv_path = os.path.join(cv_folder, file)
                session['cv_path'] = cv_path
                session['cv_uploaded'] = True
                break

    cv_uploaded = session.get('cv_uploaded', False) or (cv_path and os.path.exists(cv_path))

    if not cv_uploaded and not (cv_path and os.path.exists(cv_path)):
        flash('Veuillez d\'abord uploader votre CV', 'warning')
        return redirect(url_for('my_cv'))

    if not cv_path or not os.path.exists(cv_path):
        flash('Fichier CV introuvable', 'error')
        return redirect(url_for('my_cv'))

    try:
        # Extraire le texte du CV
        cv_text = ats_scorer.extraire_texte_fichier(cv_path)

        # Extraire les compétences techniques via LLM
        competences = ats_scorer.extraire_competences_techniques(cv_text)

        if 'erreur' in competences:
            flash(f'Erreur lors de l\'extraction: {competences["erreur"]}', 'error')
            return redirect(url_for('my_cv'))

        # Sauvegarder les compétences en session
        session['technical_skills'] = competences

        return render_template('technical_tests.html',
                             competences=competences,
                             cv_filename=session.get('cv_filename', ''))

    except Exception as e:
        flash(f'Erreur lors de l\'analyse: {str(e)}', 'error')
        return redirect(url_for('my_cv'))

@app.route('/generate-test/<category>/<int:skill_index>', methods=['POST'])
def generate_test(category, skill_index):
    """Générer un test pour une compétence spécifique"""
    technical_skills = session.get('technical_skills', {})

    if category not in technical_skills:
        return jsonify({'success': False, 'error': 'Catégorie introuvable'}), 400

    skills_list = technical_skills.get(category, [])

    if skill_index >= len(skills_list):
        return jsonify({'success': False, 'error': 'Compétence introuvable'}), 400

    try:
        skill = skills_list[skill_index]

        # Récupérer le niveau de difficulté depuis la requête (par défaut: moyen)
        data = request.get_json() or {}
        difficulte = data.get('difficulte', 'moyen')

        # Extraire le nom de la compétence et son niveau
        competence_nom = skill.get('nom', skill.get('name', ''))
        niveau_cv = skill.get('niveau', '')  # Niveau déclaré dans le CV

        # Récupérer le CV pour le contexte
        cv_path = session.get('cv_path', '')
        cv_text = ""
        if cv_path and os.path.exists(cv_path):
            cv_text = ats_scorer.extraire_texte_fichier(cv_path)

        # Générer le quiz basé sur Coursera (SANS matrice de compétences)
        test = ats_scorer.generer_quiz_coursera(
            competence_nom,
            niveau=niveau_cv,  # Niveau du CV
            cv_text=cv_text    # Pour extraction automatique du contexte
        )

        if 'erreur' in test:
            return jsonify({'success': False, 'error': test['erreur']}), 500

        # Sauvegarder le test en session
        if 'generated_tests' not in session:
            session['generated_tests'] = {}

        test_key = f"{category}_{skill_index}"
        session['generated_tests'][test_key] = test
        session.modified = True

        return jsonify({
            'success': True,
            'test': test
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/submit-test/<category>/<int:skill_index>', methods=['POST'])
def submit_test(category, skill_index):
    """Soumettre les réponses d'un test et obtenir l'évaluation"""
    test_key = f"{category}_{skill_index}"
    generated_tests = session.get('generated_tests', {})

    if test_key not in generated_tests:
        return jsonify({'success': False, 'error': 'Test introuvable'}), 400

    try:
        test = generated_tests[test_key]
        reponses = request.json.get('reponses', {})

        # Évaluer les réponses
        evaluation = evaluer_test(test, reponses)

        # Sauvegarder l'évaluation et mettre à jour le niveau de la compétence
        if 'test_results' not in session:
            session['test_results'] = {}

        session['test_results'][test_key] = evaluation

        # Mettre à jour le niveau de la compétence dans technical_skills
        if 'technical_skills' in session:
            technical_skills = session['technical_skills']
            if category in technical_skills:
                skills_list = technical_skills[category]
                if skill_index < len(skills_list):
                    skill = skills_list[skill_index]

                    # Définir l'ordre des niveaux (du plus faible au plus fort)
                    ordre_niveaux = ['novice', 'débutant', 'intermédiaire', 'avancé', 'expert']
                    niveau_actuel = skill.get('niveau', 'novice').lower()
                    nouveau_niveau = evaluation['niveau_reel'].lower()

                    # Garder le meilleur niveau obtenu
                    if niveau_actuel not in ordre_niveaux:
                        niveau_actuel = 'novice'

                    if nouveau_niveau in ordre_niveaux:
                        idx_actuel = ordre_niveaux.index(niveau_actuel) if skill.get('niveau_teste') else -1
                        idx_nouveau = ordre_niveaux.index(nouveau_niveau)

                        # Mettre à jour seulement si le nouveau niveau est meilleur
                        if idx_nouveau > idx_actuel:
                            skills_list[skill_index]['niveau'] = evaluation['niveau_reel']
                            skills_list[skill_index]['score_test'] = evaluation['pourcentage']
                            skills_list[skill_index]['meilleur_score'] = evaluation['pourcentage']
                        else:
                            # Garder le meilleur score même si niveau identique
                            if evaluation['pourcentage'] > skill.get('meilleur_score', 0):
                                skills_list[skill_index]['meilleur_score'] = evaluation['pourcentage']

                    skills_list[skill_index]['niveau_teste'] = True
                    skills_list[skill_index]['difficulte_testee'] = test.get('niveau_difficulte', 'moyen')
                    skills_list[skill_index]['dernier_score'] = evaluation['pourcentage']
                    session['technical_skills'] = technical_skills

        session.modified = True

        return jsonify({
            'success': True,
            'evaluation': evaluation
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def determiner_niveau_par_score(pourcentage: float) -> str:
    """Déterminer le niveau de compétence basé sur le score du test"""
    if pourcentage >= 90:
        return 'expert'
    elif pourcentage >= 75:
        return 'avancé'
    elif pourcentage >= 60:
        return 'intermédiaire'
    elif pourcentage >= 40:
        return 'débutant'
    else:
        return 'novice'

def evaluer_test(test: dict, reponses: dict) -> dict:
    """Évaluer les réponses d'un test"""
    score_total = 0
    max_points = test.get('bareme', {}).get('total_points', 100)
    questions = test.get('questions', [])

    resultats_detailles = []

    # Évaluer les questions QCM
    for i, question in enumerate(questions):
        question_key = f"q_{i}"
        reponse_candidate_index = reponses.get(question_key, '')
        reponse_correcte_index = question.get('reponse_correcte', '')

        # Récupérer le texte des options
        options = question.get('options', [])
        texte_reponse_candidate = 'Non répondu'
        texte_reponse_correcte = 'N/A'

        try:
            if reponse_candidate_index != '' and int(reponse_candidate_index) < len(options):
                texte_reponse_candidate = options[int(reponse_candidate_index)]
        except (ValueError, IndexError):
            pass

        try:
            if reponse_correcte_index != '' and int(reponse_correcte_index) < len(options):
                texte_reponse_correcte = options[int(reponse_correcte_index)]
        except (ValueError, IndexError):
            pass

        est_correcte = str(reponse_candidate_index).strip().lower() == str(reponse_correcte_index).strip().lower()

        points_question = max_points / len(questions) if questions else 0

        if est_correcte:
            score_total += points_question

        resultats_detailles.append({
            'question': question.get('question', ''),
            'votre_reponse': texte_reponse_candidate,
            'votre_reponse_index': reponse_candidate_index,
            'reponse_correcte': texte_reponse_correcte,
            'reponse_correcte_index': reponse_correcte_index,
            'correcte': est_correcte,
            'explication': question.get('explication', ''),
            'points_obtenus': points_question if est_correcte else 0
        })

    # Calculer le pourcentage
    pourcentage = (score_total / max_points) * 100 if max_points > 0 else 0

    # Déterminer le niveau basé sur le score
    niveau_reel = determiner_niveau_par_score(pourcentage)

    # Déterminer le statut
    seuil_reussite = test.get('bareme', {}).get('seuil_reussite', 80)
    seuil_excellent = test.get('bareme', {}).get('excellent', 90)

    if pourcentage >= seuil_excellent:
        statut = 'excellent'
        message = 'Excellente maîtrise de cette compétence!'
    elif pourcentage >= seuil_reussite:
        statut = 'reussi'
        message = 'Compétence validée avec succès!'
    else:
        statut = 'echec'
        message = 'Des efforts supplémentaires sont nécessaires.'

    return {
        'score_total': round(score_total, 2),
        'max_points': max_points,
        'pourcentage': round(pourcentage, 2),
        'niveau_reel': niveau_reel,
        'niveau_difficulte': test.get('niveau_difficulte', 'moyen'),
        'statut': statut,
        'message': message,
        'resultats_detailles': resultats_detailles,
        'competence_testee': test.get('competence_testee', '')
    }

def verify_claim_with_proof(claim: dict, proof_text: str, category: str) -> dict:
    """Vérifier un claim avec sa preuve via LLM"""
    print(f"\n=== VERIFICATION ===")
    print(f"Category: {category}")
    print(f"Claim: {claim}")
    print(f"Proof text length: {len(proof_text)} chars")

    prompt = f"""Tu es un expert en vérification de documents. Compare le claim déclaré avec la preuve fournie.

CLAIM DÉCLARÉ (catégorie: {category}):
{json.dumps(claim, ensure_ascii=False, indent=2)}

PREUVE FOURNIE (texte extrait):
{proof_text[:2000]}

Analyse si la preuve confirme, contredit ou est insuffisante pour valider le claim.

Réponds en JSON avec cette structure EXACTE:
{{
  "statut": "confirmé|partiellement_confirmé|non_confirmé|insuffisant",
  "score_confiance": <0-100>,
  "elements_confirmes": ["liste des éléments du claim confirmés par la preuve"],
  "elements_manquants": ["éléments du claim non trouvés dans la preuve"],
  "divergences": ["différences entre claim et preuve"],
  "commentaire": "analyse détaillée en 2-3 phrases",
  "recommandation": "accepter|demander_clarification|rejeter"
}}

Sois rigoureux et objectif dans ton analyse."""

    try:
        print(f"Calling Groq API...")
        response = requests.post(
            ats_scorer.url,
            headers={
                "Authorization": f"Bearer {ats_scorer.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": ats_scorer.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 1000
            },
            timeout=30
        )

        print(f"API Response status: {response.status_code}")

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"Raw API response: {content[:500]}...")

            # Extraire le JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]

            result = json.loads(content.strip())
            print(f"Parsed result: {result}")
            return result
        else:
            error_msg = f'Erreur API: {response.status_code}'
            print(f"ERROR: {error_msg}")
            return {'erreur': error_msg}

    except Exception as e:
        error_msg = str(e)
        print(f"EXCEPTION: {error_msg}")
        return {'erreur': error_msg}

# ==================== ROUTES D'ADMINISTRATION DU SCRAPING ====================

@app.route('/admin/scraping')
def admin_scraping():
    """Dashboard administrateur pour le scraping"""
    if not SCRAPING_ENABLED:
        flash('Module de scraping non disponible', 'error')
        return redirect(url_for('index'))

    stats = scraping_db.get_statistics()
    config = load_scraping_config()
    return render_template('admin_scraping.html', stats=stats, config=config, scraping_enabled=SCRAPING_ENABLED)

@app.route('/api/scraping/config', methods=['GET'])
def get_scraping_config():
    """Récupère la configuration de scraping actuelle"""
    if not SCRAPING_ENABLED:
        return jsonify({'success': False, 'message': 'Scraping non disponible'}), 400

    config = load_scraping_config()
    return jsonify(config)

@app.route('/api/scraping/config/save', methods=['POST'])
def save_scraping_config_api():
    """Sauvegarde une nouvelle configuration de scraping"""
    if not SCRAPING_ENABLED:
        return jsonify({'success': False, 'message': 'Scraping non disponible'}), 400

    try:
        new_config = request.json
        save_scraping_config(new_config)
        return jsonify({'success': True, 'message': 'Configuration sauvegardée'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/scraping/source/<source_name>', methods=['POST'])
def scrape_single_source(source_name):
    """Lance le scraping pour une seule source"""
    if not SCRAPING_ENABLED:
        return jsonify({'success': False, 'message': 'Scraping non disponible'}), 400

    global scraping_status

    if scraping_status['is_running']:
        return jsonify({
            'success': False,
            'message': 'Un scraping est déjà en cours'
        })

    config = load_scraping_config()
    source_config = config.get('scrapers', {}).get(source_name)

    if not source_config or not source_config.get('enabled'):
        return jsonify({
            'success': False,
            'message': f'Source {source_name} non disponible ou désactivée'
        })

    def run_single_scraping():
        global scraping_status
        scraping_status['is_running'] = True
        scraping_status['current_source'] = source_name
        scraping_status['sources_status'][source_name]['status'] = 'running'
        scraping_status['start_time'] = datetime.now().isoformat()

        # Ajouter le chemin job_scraper au sys.path
        scraper_path = os.path.join(os.path.dirname(__file__), 'job_scraper')
        if scraper_path not in sys.path:
            sys.path.insert(0, scraper_path)

        try:
            jobs = []

            if source_name == 'google_jobs':
                from google_jobs import scrape_google_jobs
                queries = source_config.get('queries', [])
                for i, query in enumerate(queries):
                    scraping_status['sources_status'][source_name]['message'] = f'Query {i+1}/{len(queries)}: {query}'
                    scraping_status['sources_status'][source_name]['progress'] = int((i / len(queries)) * 100)

                    result = scrape_google_jobs(
                        api_key=source_config.get('api_key'),
                        query=query,
                        max_results=source_config.get('max_results', 200),
                        country=source_config.get('country', 'tn'),
                        language=source_config.get('language', 'fr')
                    )
                    jobs.extend(result)
                    time.sleep(2)

            elif source_name == 'linkedin':
                from Linkedin import scrape_linkedin_jobs_free
                keywords = source_config.get('keywords', [])
                for i, keyword in enumerate(keywords):
                    scraping_status['sources_status'][source_name]['message'] = f'Keyword {i+1}/{len(keywords)}: {keyword}'
                    scraping_status['sources_status'][source_name]['progress'] = int((i / len(keywords)) * 100)

                    result = scrape_linkedin_jobs_free(
                        keywords=keyword,
                        location=source_config.get('location', 'Tunisia'),
                        pages=source_config.get('pages', 2),
                        get_descriptions=source_config.get('get_descriptions', False)
                    )
                    jobs.extend(result)
                    time.sleep(3)

            elif source_name == 'france_travail':
                from france_travail import scrape_france_travail
                scraping_status['sources_status'][source_name]['message'] = 'Scraping en cours...'

                jobs = scrape_france_travail(
                    client_id=source_config.get('client_id'),
                    client_secret=source_config.get('client_secret'),
                    days=source_config.get('days', 7)
                )

            elif source_name == 'tunisie_travail':
                from tunisietravail import scrape_tunisie_travail
                scraping_status['sources_status'][source_name]['message'] = 'Scraping en cours...'

                jobs = scrape_tunisie_travail(
                    ville=source_config.get('ville', 'tunis'),
                    secteur=source_config.get('secteur', 'informatique'),
                    max_pages=source_config.get('max_pages', 3)
                )

            # Insérer dans la base de données
            if jobs:
                result = scraping_db.bulk_insert_jobs(jobs, source_name)
                scraping_status['sources_status'][source_name]['jobs_found'] = result['inserted']
                scraping_status['sources_status'][source_name]['status'] = 'completed'
                scraping_status['sources_status'][source_name]['message'] = f"{result['inserted']} nouvelles offres, {result['duplicates']} doublons"
                scraping_status['sources_status'][source_name]['progress'] = 100
            else:
                scraping_status['sources_status'][source_name]['status'] = 'completed'
                scraping_status['sources_status'][source_name]['message'] = 'Aucune offre trouvée'
                scraping_status['sources_status'][source_name]['progress'] = 100

        except Exception as e:
            scraping_status['sources_status'][source_name]['status'] = 'error'
            scraping_status['sources_status'][source_name]['message'] = str(e)[:100]

        finally:
            scraping_status['is_running'] = False
            scraping_status['current_source'] = None
            scraping_status['end_time'] = datetime.now().isoformat()

    thread = threading.Thread(target=run_single_scraping)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': f'Scraping de {source_name} démarré'
    })

@app.route('/api/scraping/status')
def get_scraping_status():
    """Récupère le statut du scraping"""
    if not SCRAPING_ENABLED:
        return jsonify({'success': False, 'message': 'Scraping non disponible'}), 400

    return jsonify(scraping_status)

@app.route('/api/scraping/stats')
def get_scraping_stats():
    """Récupère les statistiques de scraping"""
    if not SCRAPING_ENABLED:
        return jsonify({'success': False, 'message': 'Scraping non disponible'}), 400

    return jsonify(scraping_db.get_statistics())

@app.route('/api/scraping/export/csv')
def export_scraping_csv():
    """Exporte les données scrapées en CSV"""
    if not SCRAPING_ENABLED:
        flash('Module de scraping non disponible', 'error')
        return redirect(url_for('index'))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jobs_scraped_{timestamp}.csv"
    filepath = os.path.join(os.path.dirname(__file__), 'job_scraper', filename)
    scraping_db.export_to_csv(filepath)

    return send_file(filepath,
                    mimetype='text/csv',
                    as_attachment=True,
                    download_name=filename)

# ==================== FIN DES ROUTES DE SCRAPING ====================

# ==================== ROUTES D'ADMINISTRATION CHROMADB ====================

@app.route('/admin/chromadb')
def admin_chromadb():
    """Page d'administration ChromaDB"""
    return render_template('admin_chromadb.html', status=chromadb_status)

@app.route('/api/chromadb/status')
def get_chromadb_status():
    """Obtenir le statut actuel de ChromaDB"""
    return jsonify(chromadb_status)

@app.route('/api/chromadb/migrate', methods=['POST'])
def migrate_chromadb():
    """Lancer la migration ChromaDB en arrière-plan"""
    global chromadb_status

    if chromadb_status['migration_running']:
        return jsonify({
            'success': False,
            'error': 'Une migration est déjà en cours'
        }), 400

    def run_migration():
        global chromadb_status
        chromadb_status['migration_running'] = True
        chromadb_status['migration_progress'] = 0

        try:
            from course_scraper.course_embedding_store import CourseEmbeddingStore

            coursera_db_path = os.path.join('course_scraper', 'coursera_fast.db')
            chroma_path = os.path.join('course_scraper', 'chroma_db')

            store = CourseEmbeddingStore(
                db_path=coursera_db_path,
                chroma_path=chroma_path
            )

            # Charger le modèle
            store.load_model()
            chromadb_status['migration_progress'] = 5

            # Lancer la synchronisation avec callback de progression
            import sqlite3
            conn = sqlite3.connect(coursera_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM courses WHERE NOT EXISTS (SELECT 1 FROM courses c)")

            # Sync depuis SQLite
            added, failed = store.sync_from_sqlite(batch_size=100)

            chromadb_status['embeddings_count'] = store.get_count()
            chromadb_status['migration_progress'] = 100
            chromadb_status['migration_needed'] = False
            chromadb_status['last_check'] = datetime.now().isoformat()

            print(f"\n✅ Migration ChromaDB terminée: {added} ajoutés, {failed} échecs\n")

        except Exception as e:
            chromadb_status['error'] = str(e)
            print(f"\n❌ Erreur migration ChromaDB: {e}\n")
        finally:
            chromadb_status['migration_running'] = False

    # Lancer en arrière-plan
    thread = threading.Thread(target=run_migration)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Migration démarrée en arrière-plan'
    })

# ==================== FIN DES ROUTES CHROMADB ====================

if __name__ == '__main__':
    # Créer les dossiers nécessaires
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('user_cvs', exist_ok=True)

    print("\n" + "="*70)
    print(" PLATEFORME DE MATCHING D'EMPLOIS AVEC ATS")
    print("="*70)
    print("  Application principale: http://localhost:5000")
    print("  Dashboard ATS: http://localhost:5000")
    if SCRAPING_ENABLED:
        print("  Admin Scraping: http://localhost:5000/admin/scraping")
        print("  Module de scraping: ACTIVE")
    else:
        print("  Module de scraping: DESACTIVE")
    print("="*70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)