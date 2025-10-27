from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import random
import re

class DuplicateManager:
    """Gestionnaire de doublons simple"""
    
    def __init__(self):
        self.seen_urls = set()
        self.seen_jobs = set()
        self.duplicate_count = 0
        
    def is_duplicate(self, url, job_data):
        """Vérifie si c'est un doublon (URL ou contenu)"""
        if url in self.seen_urls:
            self.duplicate_count += 1
            return True
        
        job_signature = (
            job_data.get("title", "").lower().strip(),
            job_data.get("company", "").lower().strip(),
            job_data.get("location", "").lower().strip()
        )
        
        if job_signature in self.seen_jobs:
            self.duplicate_count += 1
            return True
        
        self.seen_urls.add(url)
        self.seen_jobs.add(job_signature)
        return False

def clean_job_title(title):
    """
    Nettoie le titre pour extraire seulement le poste
    
    Exemples:
    - "Chahia Tunis recrute Technicien Supérieur Informatique" 
      → "Technicien Supérieur Informatique"
    - "PRIMANET recrute Agent Commercial"
      → "Agent Commercial"
    """
    if not title:
        return "Non précisé"
    
    # Liste des mots-clés de séparation
    separators = [
        'recrute',
        'recrutement de',
        'recherche',
        'cherche',
        'embauche',
        'offre d\'emploi',
        'offre'
    ]
    
    # Chercher le séparateur dans le titre
    title_lower = title.lower()
    for separator in separators:
        if separator in title_lower:
            # Trouver la position et extraire ce qui suit
            parts = title.split(separator, 1)
            if len(parts) == 2:
                cleaned_title = parts[1].strip()
                # Nettoyer les caractères spéciaux en début
                cleaned_title = cleaned_title.lstrip(':- ')
                if cleaned_title:
                    return cleaned_title
    
    # Si aucun séparateur trouvé, retourner le titre tel quel
    return title.strip()

def extract_from_description(description):
    """
    Extrait les champs depuis la description
    
    Format attendu:
    Ville › Sfax ville
    Nom / Entreprise › PRIMANET TUNISIA
    Email › contact@email.com
    Adresse › Route El Ain sfax
    Tel / Fax › 27126506
    """
    
    fields = {
        "company": "Non précisé",
        "location": "Non précisé",
        "email": "Non précisé",
        "address": "Non précisé",
        "tel": "Non précisé"
    }
    
    if not description:
        return fields
    
    # Patterns pour les champs structurés
    patterns = {
        "location": [
            r"Ville\s*[›:]\s*([^\n›]+)",
            r"Lieu\s*[›:]\s*([^\n›]+)"
        ],
        "company": [
            r"(?:Nom\s*/\s*)?Entreprise\s*[›:]\s*([^\n›]+)",
            r"Société\s*[›:]\s*([^\n›]+)"
        ],
        "email": [
            r"Email\s*[›:]\s*([^\n›\s]+@[^\n›\s]+)",
            r"E-mail\s*[›:]\s*([^\n›\s]+@[^\n›\s]+)"
        ],
        "address": [
            r"Adresse\s*[›:]\s*([^\n›]+)"
        ],
        "tel": [
            r"Tel\s*(?:/\s*Fax)?\s*[›:]\s*([^\n›]+)",
            r"Téléphone\s*[›:]\s*([^\n›]+)"
        ]
    }
    
    # Extraire les champs
    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, description, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                if value and value != '›' and len(value) > 1:
                    fields[field] = value
                    break
    
    return fields

def setup_driver():
    """Configuration Selenium"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"❌ Erreur navigateur: {e}")
        return None

def perform_search(driver, ville, secteur):
    """Effectue une recherche ciblée sur le site"""
    try:
        print(f"🔍 Accès à la page de recherche de tunisietravail.net")
        driver.get("https://www.tunisietravail.net/")
        time.sleep(3)
        
        search_selectors = [
            "input[name='search']",
            "input[type='search']", 
            "input[placeholder*='recherch']",
            "input[placeholder*='emploi']",
            "#search",
            ".search-input",
            "input.form-control"
        ]
        
        search_box = None
        for selector in search_selectors:
            try:
                search_box = driver.find_element(By.CSS_SELECTOR, selector)
                if search_box.is_displayed():
                    break
            except:
                continue
        
        if not search_box:
            print("⚠️ Champ de recherche non trouvé, tentative avec URL de recherche directe")
            search_query = f"{ville} {secteur}"
            search_url = f"https://www.tunisietravail.net/?s={search_query.replace(' ', '+')}"
            driver.get(search_url)
            time.sleep(3)
            return True
        
        search_query = f"{ville} {secteur}"
        print(f"🔎 Recherche de: '{search_query}'")
        
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)
        
        time.sleep(5)
        print("✅ Recherche effectuée avec succès")
        return True
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la recherche: {e}")
        return False

def scrape_job_details(driver, job_link):
    """Extraction des détails d'une offre - VERSION AMÉLIORÉE"""
    try:
        driver.get(job_link)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        time.sleep(random.uniform(2, 4))
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 1. Extraire et nettoyer le titre
        title = "Non précisé"
        title_tag = soup.find("h1")
        if title_tag:
            raw_title = title_tag.get_text().strip()
            title = clean_job_title(raw_title)  # Nettoyer le titre
        
        # 2. Extraire la description complète
        description = "Non précisé"
        description_selectors = [
            ".PostContent",
            ".entry-content",
            ".job-description", 
            ".content",
            "article .content"
        ]
        
        for selector in description_selectors:
            description_tag = soup.select_one(selector)
            if description_tag:
                description = description_tag.get_text().strip()
                break
        
        # 3. Extraire les champs depuis la description
        extracted_fields = extract_from_description(description)
        
        # 4. Créer l'objet job avec les vraies données
        job_data = {
            "title": title,
            "company": extracted_fields["company"],
            "location": extracted_fields["location"],
            "email": extracted_fields["email"],
            "address": extracted_fields["address"],
            "tel": extracted_fields["tel"],
            "job_url": job_link,
            "description": description,
            "source": "Tunisie Travail",
            "date": "Non précisé",
            "job_type": "N/A",
            "salary": "Non précisé",
            "contrat": "N/A"
        }
        
        return job_data
        
    except Exception as e:
        print(f"⚠️ Erreur extraction: {e}")
        return None

def scrape_search_results(driver, ville, secteur, max_pages=10):
    """Scrape les résultats de recherche"""
    
    duplicate_manager = DuplicateManager()
    matching_jobs = []
    
    try:
        for page in range(1, max_pages + 1):
            print(f"\n📄 Page {page}/{max_pages} des résultats de recherche")
            
            if page > 1:
                current_url = driver.current_url
                if "page/" in current_url:
                    base_url = current_url.split("page/")[0]
                    driver.get(f"{base_url}page/{page}/")
                else:
                    separator = "&" if "?" in current_url else "?"
                    driver.get(f"{current_url}{separator}paged={page}")
                
                time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            job_selectors = [
                ".Post h2 a[href]",
                ".Post a[href*='emploi']",
                ".Post a[href*='recrute']",
                "article.Post a[href]",
                ".entry-title a[href]",
                ".job-title a[href]",
                ".Post .entry-header a[href]"
            ]
            
            job_links = []
            for selector in job_selectors:
                links = soup.select(selector)
                if links:
                    filtered_links = []
                    for link in links:
                        href = link.get('href', '')
                        link_text = link.get_text().lower()
                        
                        exclude_keywords = [
                            'facebook', 'twitter', 'linkedin', 'instagram',
                            's\'identifier', 'connexion', 'inscription', 'contact',
                            'javascript', 'cookies', 'confidentialité', 'mentions',
                            'accueil', 'à propos', 'services', 'blog'
                        ]
                        
                        include_keywords = [
                            'recrute', 'emploi', 'offre', 'poste', 'candidat',
                            'technicien', 'ingénieur', 'commercial', 'assistant',
                            'responsable', 'chef', 'directeur', 'agent', 'stage'
                        ]
                        
                        is_excluded = any(keyword in link_text for keyword in exclude_keywords)
                        is_job_related = any(keyword in link_text for keyword in include_keywords)
                        has_valid_href = href and not href.startswith('#') and len(href) > 10
                        
                        if not is_excluded and is_job_related and has_valid_href:
                            filtered_links.append(href)
                    
                    if filtered_links:
                        job_links = filtered_links
                        print(f"✅ Trouvé {len(job_links)} liens d'offres")
                        break
            
            if len(job_links) > 50:
                print(f"⚠️ Limitation à 50 premiers liens")
                job_links = job_links[:50]
            
            if not job_links:
                print("❌ Aucun lien d'offre valide trouvé")
                break
            
            page_matches = 0
            
            for i, job_link in enumerate(job_links, 1):
                try:
                    if job_link.startswith('/'):
                        job_link = "https://www.tunisietravail.net" + job_link
                    elif not job_link.startswith('http'):
                        job_link = "https://www.tunisietravail.net/" + job_link
                    
                    print(f"  📋 Analyse offre {i}/{len(job_links)}")
                    
                    job_data = scrape_job_details(driver, job_link)
                    if not job_data:
                        continue
                    
                    if duplicate_manager.is_duplicate(job_link, job_data):
                        print(f"    🔄 Doublon ignoré")
                        continue
                    
                    matching_jobs.append(job_data)
                    page_matches += 1
                    print(f"    ✅ {job_data['title'][:40]}... - {job_data['company']}")
                    
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    print(f"    ⚠️ Erreur: {e}")
                    continue
            
            print(f"📊 Page {page}: {page_matches} nouvelles offres")
            print(f"📊 Total: {len(matching_jobs)} offres")
            
            time.sleep(random.uniform(3, 6))
    
    except Exception as e:
        print(f"❌ Erreur scraping: {e}")
    
    return matching_jobs, duplicate_manager

def scrape_tunisie_travail(ville, secteur, max_pages=10):
    """Scrape les offres d'emploi avec recherche ciblée"""
    
    print(f"Recherche: {ville.upper()} + {secteur.upper()}")
    print(f"Pages: {max_pages}")
    
    driver = setup_driver()
    if not driver:
        return []
    
    try:
        if not perform_search(driver, ville, secteur):
            print("Erreur: Impossible d'effectuer la recherche")
            return []
        
        matching_jobs, duplicate_manager = scrape_search_results(driver, ville, secteur, max_pages)
        
    except Exception as e:
        print(f"Erreur: {e}")
        matching_jobs = []
    finally:
        driver.quit()
    
    print(f"\nTerminé: {len(matching_jobs)} offres trouvées")
    
    return matching_jobs  # Retourne directement la liste

def save_to_json(data, filename):
    """Sauvegarde en JSON"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Sauvegardé dans: {filename}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")

if __name__ == "__main__":
    
    print("="*60)
    print("RECHERCHE: TUNIS + INFORMATIQUE")
    print("="*60)
    
    # Récupère directement la liste des offres
    offres = scrape_tunisie_travail(
        ville="tunis",
        secteur="informatique",
        max_pages=1
    )
    
    # Sauvegarder directement la liste
    save_to_json(offres, "tunis_travail.json")
    
    print(f"\nTotal: {len(offres)} offres")