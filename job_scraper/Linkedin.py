import requests
from bs4 import BeautifulSoup
import json
import time
import random
from urllib.parse import urlencode

def get_job_description(job_url, headers):
    """
    Récupère la description complète d'une offre d'emploi
    """
    try:
        time.sleep(random.uniform(2, 4))  # Pause entre chaque requête
        response = requests.get(job_url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Chercher la description dans différents sélecteurs possibles
            description = None
            
            # Tentative 1: div avec classe description
            desc_elem = soup.find('div', class_='show-more-less-html__markup')
            if desc_elem:
                description = desc_elem.get_text(strip=True)
            
            # Tentative 2: section description
            if not description:
                desc_elem = soup.find('section', class_='description')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
            
            # Tentative 3: article avec description
            if not description:
                desc_elem = soup.find('article', class_='jobs-description')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
            
            # Tentative 4: div description__text
            if not description:
                desc_elem = soup.find('div', class_='description__text')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
            
            return description if description else "Description non disponible"
        
        return f"Erreur HTTP {response.status_code}"
        
    except Exception as e:
        return f"Erreur: {str(e)}"

def scrape_linkedin_jobs_free(keywords="développeur", location="France", pages=5, get_descriptions=True):
    """
    Scrape LinkedIn jobs gratuitement avec déduplication et descriptions
    
    Args:
        keywords: Mots-clés de recherche
        location: Localisation
        pages: Nombre de pages à scraper
        get_descriptions: Si True, récupère la description de chaque offre (plus lent)
    """
    
    all_jobs = []
    seen_urls = set()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    print(f"Recherche: '{keywords}' à {location}")
    print(f"{pages} pages à scraper...")
    if get_descriptions:
        print("⚠️  Mode avec descriptions activé (plus lent)")
    
    for page in range(pages):
        try:
            params = {
                'keywords': keywords,
                'location': location,
                'start': page * 25,
                'refresh': 'true'
            }
            
            url = f"https://www.linkedin.com/jobs/search?{urlencode(params)}"
            print(f"\nPage {page + 1}/{pages}...")
            
            delay = random.uniform(3, 7)
            print(f"   Pause de {delay:.1f}s...")
            time.sleep(delay)
            
            response = requests.get(url, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                job_cards = soup.find_all('div', class_='base-card')
                
                if not job_cards:
                    job_cards = soup.find_all('div', {'data-entity-urn': True})
                    if not job_cards:
                        job_cards = soup.find_all('li', class_='result-card')
                
                if not job_cards:
                    print(f"   Aucun job trouvé sur cette page")
                    break
                
                print(f"   {len(job_cards)} jobs trouvés")
                page_jobs = 0
                page_duplicates = 0
                
                for idx, card in enumerate(job_cards, 1):
                    try:
                        title_elem = card.find('h3', class_='base-search-card__title')
                        if not title_elem:
                            title_elem = card.find('a', {'data-tracking-control-name': 'public_jobs_jserp-result_search-card'})
                        
                        company_elem = card.find('h4', class_='base-search-card__subtitle')
                        if not company_elem:
                            company_elem = card.find('a', href=lambda x: x and '/company/' in x)
                        
                        location_elem = card.find('span', class_='job-search-card__location')
                        
                        link_elem = card.find('a', class_='base-card__full-link')
                        if not link_elem:
                            link_elem = card.find('a', href=lambda x: x and '/jobs/view/' in x)
                        
                        date_elem = card.find('time')
                        
                        if title_elem:
                            job_url = link_elem.get('href') if link_elem else 'N/A'
                            title = title_elem.get_text().strip() if title_elem else 'N/A'
                            company = company_elem.get_text().strip() if company_elem else 'N/A'
                            
                            job_id = f"{title.lower()}|{company.lower()}"
                            
                            if job_id in seen_urls:
                                page_duplicates += 1
                                continue
                            
                            seen_urls.add(job_id)
                            
                            job = {
                                'title': title,
                                'company': company,
                                'location': location_elem.get_text().strip() if location_elem else 'N/A',
                                'job_url': job_url,
                                'date': date_elem.get('datetime', date_elem.get_text().strip()) if date_elem else 'N/A',
                                'source': 'LinkedIn',
                                'job_type': 'N/A',
                                'salary': 'N/A',
                                'contrat': 'N/A'
                            }
                            
                            # Récupérer la description si demandé
                            if get_descriptions and job_url != 'N/A':
                                print(f"      → Récupération description {idx}/{len(job_cards)}...", end=' ')
                                description = get_job_description(job_url, headers)
                                job['description'] = description
                                print("✓")
                            else:
                                job['description'] = "Non récupérée"
                            
                            all_jobs.append(job)
                            page_jobs += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   {page_jobs} nouveaux jobs ajoutés, {page_duplicates} doublons ignorés - Total: {len(all_jobs)}")
                        
            elif response.status_code == 429:
                print(f"   Rate limit détecté, pause de 60s...")
                time.sleep(60)
                continue
                
            else:
                print(f"   Erreur HTTP: {response.status_code}")
                if page == 0:
                    print("   Première page inaccessible, arrêt du scraping")
                    break
                continue
                
        except Exception as e:
            print(f"   Erreur page {page + 1}: {e}")
            continue
    
    return all_jobs

# UTILISATION PRINCIPALE
if __name__ == "__main__":
    print("Scraping LinkedIn Jobs - Version avec Descriptions")
    print("=" * 60)
    
    # Option 1: Avec descriptions (plus lent, mais complet)
    jobs = scrape_linkedin_jobs_free(
        keywords="développeur python",
        location="France",
        pages=2,
        get_descriptions=True  # Mettre False pour scraping rapide sans descriptions
    )
    
    # Option 2: Sans descriptions (rapide)
    # jobs = scrape_linkedin_jobs_free(
    #     keywords="développeur",
    #     location="France", 
    #     pages=5,
    #     get_descriptions=False
    # )
    
    # Sauvegarde
    with open("linkedin_jobs_with_descriptions.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Scraping terminé!")
    print(f"Total: {len(jobs)} offres uniques récupérées")
    print(f"Fichier: linkedin_jobs.json")
    