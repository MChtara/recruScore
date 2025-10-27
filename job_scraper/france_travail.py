import requests
import json
import time
from datetime import datetime, timedelta
import hashlib


# === Fonction pour obtenir un nouveau token ===
def get_token(client_id, client_secret):
    """Obtient un token d'accès OAuth"""
    url = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "api_offresdemploiv2 o2dsoffre"
    }
    try:
        r = requests.post(url, data=data, timeout=30)
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception as e:
        print(f"Erreur obtention token: {e}")
        return None


# === Fonction pour créer un ID unique ===
def create_unique_id(offre):
    """Crée un ID unique basé sur le contenu de l'offre"""
    if offre.get("id"):
        return str(offre["id"])
    
    content = f"{offre.get('intitule', '')}-{offre.get('entreprise', {}).get('nom', '')}-{offre.get('lieuTravail', {}).get('libelle', '')}"
    return hashlib.md5(content.encode()).hexdigest()


# === Fonction pour formater la date ===
def format_date(date_string):
    """Extrait seulement la partie date (YYYY-MM-DD)"""
    if not date_string:
        return "Non précisé"
    
    try:
        # Format: "2025-09-17T22:30:02.109Z" → "2025-09-17"
        return date_string.split('T')[0]
    except:
        return date_string


# === Fonction pour obtenir le lien URL ===
def get_job_url(offre):
    """Récupère l'URL de l'offre"""
    # 1. Essayer origineOffre.urlOrigine
    url = offre.get("origineOffre", {}).get("urlOrigine")
    if url:
        return url
    
    # 2. Essayer origineOffre.url
    url = offre.get("origineOffre", {}).get("url")
    if url:
        return url
    
    # 3. Construire l'URL France Travail avec l'ID de l'offre
    offre_id = offre.get("id")
    if offre_id:
        return f"https://candidat.francetravail.fr/offres/recherche/detail/{offre_id}"
    
    return "Non disponible"


# === Fonction principale de scraping ===
def scrape_france_travail(client_id, client_secret, days=7):
    """
    Scrape les offres France Travail
    
    Args:
        client_id: Identifiant client API
        client_secret: Secret client API
        days: Nombre de jours à scraper (défaut: 7)
    
    Returns:
        Liste des offres d'emploi
    """
    
    # Authentification
    access_token = get_token(client_id, client_secret)
    if not access_token:
        print("ERREUR: Impossible d'obtenir le token")
        return []
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    # Paramètres de scraping
    search_url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    step = 150
    jour_ref = datetime.today()
    
    all_jobs = []
    seen_ids = set()
    total_duplicates = 0
    
    print(f"Début du scraping France Travail : {days} jours")
    print(f"Du {jour_ref.strftime('%Y-%m-%d')} au {(jour_ref - timedelta(days=days-1)).strftime('%Y-%m-%d')}")
    
    try:
        for jour_offset in range(days):
            date_cible = (jour_ref - timedelta(days=jour_offset)).strftime("%Y-%m-%d")
            offset = 0
            day_jobs_count = 0
            day_duplicates = 0
            
            print(f"\n Jour {jour_offset+1}/{days} - {date_cible}")
            
            while offset <= 3000:
                params = {
                    "range": f"{offset}-{offset + step - 1}",
                    "dateCreation": date_cible
                }
                
                try:
                    r = requests.get(search_url, headers=headers, params=params, timeout=30)
                    
                    # Token expiré
                    if r.status_code == 401:
                        print("REFRESH: Token expiré. Récupération d'un nouveau...")
                        access_token = get_token(client_id, client_secret)
                        if not access_token:
                            break
                        headers["Authorization"] = f"Bearer {access_token}"
                        r = requests.get(search_url, headers=headers, params=params, timeout=30)
                    
                    if r.status_code not in [200, 206]:
                        print(f"ERREUR: Erreur {r.status_code} à l'offset {offset}")
                        break
                    
                    offres = r.json().get("resultats", [])
                    
                    if not offres:
                        print(f"OK: Fin des offres à l'offset {offset}")
                        break
                    
                    # Traitement avec déduplication
                    for offre in offres:
                        unique_id = create_unique_id(offre)
                        
                        if unique_id in seen_ids:
                            day_duplicates += 1
                            total_duplicates += 1
                            continue
                        
                        seen_ids.add(unique_id)
                        
                        # Créer l'objet job normalisé
                        job = {
                            "unique_id": unique_id,
                            "title": offre.get("intitule"),
                            "company": offre.get("entreprise", {}).get("nom"),
                            "location": offre.get("lieuTravail", {}).get("libelle"),
                            "source": "France Travail",
                            "description": offre.get("description") or "Non renseignée",
                            "job_url": get_job_url(offre),
                            "date": format_date(offre.get("dateCreation")),
                            "contrat": offre.get("typeContratLibelle") or "Non précisé",
                            "salary": offre.get("salaire", {}).get("libelle") or "Non précisé",
                            "job_type": offre.get("typeContratLibelle") or "N/A"
                        }
                        all_jobs.append(job)
                        day_jobs_count += 1
                    
                    print(f"+ {len(offres)} offres récupérées, {len(offres) - day_duplicates} nouvelles (offset {offset})")
                    
                    offset += step
                    time.sleep(1)
                
                except Exception as e:
                    print(f"ERREUR: Erreur à {date_cible}, offset {offset} : {e}")
                    break
            
            print(f"STATS: Jour terminé: {day_jobs_count} nouvelles offres, {day_duplicates} doublons ignorés")
    
    except KeyboardInterrupt:
        print(f"\nWARNING: Arrêt manuel détecté!")
    
    # Statistiques finales
    print(f"\nSUCCESS: Scraping terminé!")
    print(f"STATS: Statistiques finales:")
    print(f"   • Période: {days} jours")
    print(f"   • Offres uniques: {len(all_jobs)}")
    print(f"   • Doublons évités: {total_duplicates}")
    print(f"   • Total traité: {len(all_jobs) + total_duplicates}")
    
    return all_jobs


# === Fonction de sauvegarde (optionnelle) ===
def save_jobs(jobs, filename="offres_france_travail.json"):
    """Sauvegarde les offres en JSON"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"OK: {len(jobs)} offres sauvegardées dans {filename}")


# === Utilisation en tant que script autonome ===
if __name__ == "__main__":
    # Identifiants API
    CLIENT_ID = "PAR_scraperemploiaziz_14497dbf72629cf4304f3f8d3635c367dd96674dced592fd8ab5345539059252"
    CLIENT_SECRET = "9819e72518856c24f218b19e9ffa464c4eff192ffb6870f2726c5e4a333782c5"
    
    # Scraping
    jobs = scrape_france_travail(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        days=7
    )
    
    # Sauvegarde
    if jobs:
        save_jobs(jobs)