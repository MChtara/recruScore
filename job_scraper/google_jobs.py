import requests
import json
import time
from datetime import datetime, timedelta
import re


def parse_relative_date(relative_str, scrape_date):
    """
    Convertit "il y a X jours/heures/mois" en date précise
    
    Exemples:
    - "il y a 28 jours" → "2025-09-03"
    - "il y a 10 heures" → "2025-10-01"
    - "il y a 2 mois" → "2025-08-01"
    """
    if not relative_str or relative_str == 'N/A':
        return 'N/A'
    
    # Extraire le nombre
    match = re.search(r'(\d+)', relative_str)
    if not match:
        return relative_str
    
    number = int(match.group(1))
    text_lower = relative_str.lower()
    
    # Calculer la date
    if 'heure' in text_lower:
        date_posted = scrape_date - timedelta(hours=number)
    elif 'jour' in text_lower:
        date_posted = scrape_date - timedelta(days=number)
    elif 'semaine' in text_lower:
        date_posted = scrape_date - timedelta(weeks=number)
    elif 'mois' in text_lower:
        date_posted = scrape_date - timedelta(days=number*30)
    else:
        return relative_str
    
    return date_posted.strftime("%Y-%m-%d")


def normalize_google_job(raw_job, scrape_date=None):
    """
    Transforme un job Google Jobs vers un format unifié
    Gère extensions et CONVERTIT "il y a X jours" en date réelle
    """
    if scrape_date is None:
        scrape_date = datetime.now()
    
    # Extraire les informations essentielles
    title = raw_job.get('title', 'N/A')
    company = raw_job.get('company_name', 'N/A')
    location = raw_job.get('location', 'N/A')
    description = raw_job.get('description', 'N/A')
    
    # URL de candidature
    job_url = 'N/A'
    if raw_job.get('apply_options') and len(raw_job['apply_options']) > 0:
        job_url = raw_job['apply_options'][0].get('link', 'N/A')
    
    # Initialisation
    date_posted = 'N/A'
    salary = 'N/A'
    job_type = 'N/A'
    
    # Parcourir extensions UN PAR UN
    if raw_job.get('extensions'):
        for ext in raw_job['extensions']:
            ext_lower = ext.lower()
            
            # 1. C'est une DATE ?
            if any(word in ext for word in ['jour', 'jours', 'semaine', 'mois', 'heure', 'heures']):
                date_posted = parse_relative_date(ext, scrape_date)
                continue
            
            # 2. C'est un SALAIRE ?
            if any(currency in ext for currency in ['DT', 'dt', 'kDT', 'k DT', 'EUR', 'USD', 'TND', 'par mois', 'par an', 'dinars']):
                salary = ext
                continue
            
            # 3. C'est un TYPE DE CONTRAT ?
            if 'cdi' in ext_lower:
                job_type = 'CDI'
            elif 'cdd' in ext_lower:
                job_type = 'CDD'
            elif 'stage' in ext_lower or 'internship' in ext_lower:
                job_type = 'Stage'
            elif 'alternance' in ext_lower or 'apprentissage' in ext_lower:
                job_type = 'Alternance'
            elif 'freelance' in ext_lower or 'indépendant' in ext_lower:
                job_type = 'Freelance'
            elif 'intérim' in ext_lower or 'interim' in ext_lower or 'temporaire' in ext_lower:
                job_type = 'Intérim'
            elif 'plein temps' in ext_lower or 'temps plein' in ext_lower or 'full time' in ext_lower:
                job_type = 'Temps plein'
            elif 'temps partiel' in ext_lower or 'partiel' in ext_lower or 'part time' in ext_lower:
                job_type = 'Temps partiel'
            elif 'contrat pro' in ext_lower or 'professionnalisation' in ext_lower:
                job_type = 'Contrat pro'
            elif 'saisonnier' in ext_lower or 'seasonal' in ext_lower:
                job_type = 'Saisonnier'
    
    # Format unifié
    unified_job = {
        'title': title,
        'company': company,
        'location': location,
        'description': description,
        'job_url': job_url,
        'date_posted': date_posted,
        'job_type': job_type,
        'salary': salary,
        'source': 'Google Jobs'
    }
    
    return unified_job


def scrape_google_jobs(api_key, query, max_results=200, country="tn", language="fr"):
    """
    Scrape Google Jobs via API ScrapingDog
    
    Args:
        api_key: Clé API ScrapingDog
        query: Requête de recherche (ex: "Tunis informatique")
        max_results: Nombre maximum de résultats (défaut: 200)
        country: Code pays (défaut: "tn")
        language: Code langue (défaut: "fr")
    
    Returns:
        Liste des offres d'emploi normalisées
    """
    
    print(f"Début du scraping Google Jobs pour: '{query}'")
    
    base_url = "https://api.scrapingdog.com/google_jobs"
    scrape_date = datetime.now()
    
    all_jobs = []
    results_per_page = 50
    max_pages = max_results // results_per_page
    
    print(f"Pages à scraper: {max_pages}")
    
    for page in range(1, max_pages + 1):
        print(f"\nPage {page}/{max_pages}...")
        
        params = {
            "api_key": api_key,
            "query": query,
            "results": results_per_page,
            "page": page,
            "country": country,
            "language": language,
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"   ❌ Erreur HTTP: {response.status_code}")
                if response.status_code == 401:
                    print("   ⚠️ API key invalide ou quota dépassé")
                elif response.status_code == 403:
                    try:
                        error_msg = response.json().get('message', 'Accès refusé')
                        print(f"   ⚠️ {error_msg}")
                    except:
                        print("   ⚠️ Quota API dépassé ou accès refusé")
                continue
            
            data = response.json()
            jobs = data.get('jobs_results', [])
            
            if isinstance(jobs, list) and len(jobs) > 0:
                for job in jobs:
                    if isinstance(job, dict):
                        # Normaliser avec calcul de date
                        unified_job = normalize_google_job(job, scrape_date)
                        all_jobs.append(unified_job)
                
                print(f"   ✓ {len(jobs)} offres normalisées - Total: {len(all_jobs)}")
            else:
                print(f"   ⚠️ Aucune offre sur cette page")
                break
        
        except requests.exceptions.Timeout:
            print(f"   ❌ Timeout sur la page {page}")
            continue
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            continue
        
        time.sleep(2)  # Pause entre requêtes
    
    print(f"\n✅ Scraping terminé: {len(all_jobs)} offres récupérées")
    return all_jobs


def save_jobs(jobs, filename="google_jobs.json"):
    """Sauvegarde les offres en JSON"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        print(f"💾 {len(jobs)} offres sauvegardées dans {filename}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")


# === Utilisation en tant que script autonome ===
if __name__ == "__main__":
    print("="*60)
    print("Scraping Google Jobs - Format Unifié")
    print("="*60)
    
    # Configuration
    API_KEY = "680b5540fbb24d6b6ff694b8"
    QUERY = "Tunis informatique"
    MAX_RESULTS = 200
    
    # Scraping
    jobs = scrape_google_jobs(
        api_key=API_KEY,
        query=QUERY,
        max_results=MAX_RESULTS,
        country="tn",
        language="fr"
    )
    
    # Sauvegarde
    if jobs:
        save_jobs(jobs)
        
        # Aperçu
        print("\n📋 Aperçu du format unifié (première offre):")
        print(json.dumps(jobs[0], indent=2, ensure_ascii=False))
    else:
        print("\n⚠️ Aucune offre récupérée")