# coursera_scraper_utils.py - Utilitaires pour scraper les détails des cours Coursera

import requests
from bs4 import BeautifulSoup
import time
import random

def scrape_what_you_learn(course_url: str, timeout: int = 15) -> list:
    """
    Scrape la section "What you'll learn" d'une page de cours Coursera

    Args:
        course_url: URL complète du cours Coursera
        timeout: Timeout en secondes pour la requête

    Returns:
        Liste des objectifs d'apprentissage ou liste vide si erreur
    """
    try:
        print(f"\n=== SCRAPING WHAT YOU'LL LEARN ===")
        print(f"URL: {course_url}")

        # Headers pour imiter un navigateur
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        # Requête GET avec timeout
        response = requests.get(course_url, headers=headers, timeout=timeout)
        response.raise_for_status()

        print(f"[OK] Page chargée (status: {response.status_code})")

        # Parser avec BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Stratégie 1: Chercher la section "What you'll learn" par aria-label ou title
        learning_objectives = []

        # Essayer plusieurs sélecteurs possibles
        selectors = [
            # Sélecteur pour les nouvelles pages Coursera
            'div[data-testid="what-you-will-learn"] ul li',
            'div[class*="whatYouWillLearn"] ul li',
            'section[aria-label*="What you"] ul li',
            'section[aria-label*="what you"] ul li',
            # Sélecteur générique
            'div.content-inner ul li',
            'ul.rc-Skills li',
            'div.Skills ul li'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements and len(elements) > 0:
                print(f"[OK] Trouvé {len(elements)} objectifs avec sélecteur: {selector}")
                learning_objectives = [elem.get_text(strip=True) for elem in elements]
                break

        # Stratégie 2: Recherche textuelle si aucun sélecteur ne fonctionne
        if not learning_objectives:
            print("[INFO] Recherche textuelle de 'What you'll learn'...")
            # Chercher le titre de section
            for heading in soup.find_all(['h2', 'h3', 'h4']):
                text = heading.get_text(strip=True).lower()
                if 'what you' in text or 'ce que vous' in text:
                    # Trouver la liste suivante
                    next_ul = heading.find_next('ul')
                    if next_ul:
                        items = next_ul.find_all('li')
                        learning_objectives = [item.get_text(strip=True) for item in items]
                        print(f"[OK] Trouvé {len(learning_objectives)} objectifs par recherche textuelle")
                        break

        # Stratégie 3: Chercher "Skills you'll gain" comme fallback
        if not learning_objectives:
            print("[INFO] Recherche de 'Skills you'll gain'...")
            skills_section = soup.find('div', {'class': lambda x: x and 'skills' in x.lower()})
            if skills_section:
                items = skills_section.find_all('li')
                learning_objectives = [item.get_text(strip=True) for item in items]
                print(f"[OK] Trouvé {len(learning_objectives)} compétences")

        if learning_objectives:
            # Nettoyer et limiter à 10 objectifs max
            learning_objectives = [obj for obj in learning_objectives if obj and len(obj) > 10][:10]
            print(f"[SUCCESS] {len(learning_objectives)} objectifs extraits")
            for i, obj in enumerate(learning_objectives, 1):
                print(f"  {i}. {obj[:80]}...")
            return learning_objectives
        else:
            print("[WARNING] Aucun objectif d'apprentissage trouvé")
            return []

    except requests.Timeout:
        print(f"[ERROR] Timeout après {timeout}s lors du chargement de {course_url}")
        return []
    except requests.RequestException as e:
        print(f"[ERROR] Erreur réseau: {str(e)}")
        return []
    except Exception as e:
        print(f"[ERROR] Erreur inattendue: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def get_course_learning_context(course_url: str, max_retries: int = 2) -> str:
    """
    Récupère le contexte d'apprentissage d'un cours pour générer un quiz contextuel

    Args:
        course_url: URL du cours Coursera
        max_retries: Nombre de tentatives en cas d'échec

    Returns:
        Texte formaté des objectifs d'apprentissage ou message d'erreur
    """
    for attempt in range(max_retries):
        learning_objectives = scrape_what_you_learn(course_url)

        if learning_objectives:
            # Formater en texte lisible
            context = "Ce cours enseigne les compétences suivantes :\n"
            context += "\n".join([f"- {obj}" for obj in learning_objectives])
            return context

        if attempt < max_retries - 1:
            print(f"[INFO] Tentative {attempt + 1}/{max_retries} échouée, nouvelle tentative dans 2s...")
            time.sleep(2)

    return "Aucun objectif d'apprentissage disponible. Génération d'un quiz générique."


def scrape_course_modules_details(course_url: str, timeout: int = 15) -> dict:
    """
    Scrape les détails complets des modules d'un cours Coursera

    NOUVEAU: Extrait le contenu détaillé de chaque module :
    - Nom du module
    - Description
    - Contenu (vidéos, lectures, assignments, etc.)
    - Durée estimée

    Args:
        course_url: URL complète du cours Coursera
        timeout: Timeout en secondes

    Returns:
        dict avec structure:
        {
            'course_title': str,
            'total_modules': int,
            'modules': [
                {
                    'module_number': int,
                    'title': str,
                    'duration': str,
                    'description': str,
                    'content': {
                        'videos': int,
                        'readings': int,
                        'assignments': int,
                        'quizzes': int
                    },
                    'topics': [str]  # Liste des sujets abordés
                }
            ]
        }
    """
    import re

    try:
        print(f"\n=== SCRAPING COURSE MODULES DETAILS ===")
        print(f"URL: {course_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

        response = requests.get(course_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        print(f"[OK] Page chargée (status: {response.status_code})")

        soup = BeautifulSoup(response.content, 'html.parser')

        # Structure du résultat
        result = {
            'course_title': '',
            'total_modules': 0,
            'modules': []
        }

        # Extraire le titre du cours
        title_selectors = ['h1', 'h1.banner-title', 'h1[class*="title"]']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                result['course_title'] = title_elem.get_text(strip=True)
                break

        print(f"[INFO] Cours: {result['course_title'][:60]}...")

        # Chercher les modules - Plusieurs stratégies
        modules_found = False

        # Stratégie 1: NOUVEAU - Utiliser data-testid="accordion-item" (structure actuelle Coursera 2025)
        accordion_items = soup.select('[data-testid="accordion-item"]')

        if accordion_items and len(accordion_items) > 0:
            print(f"[INFO] {len(accordion_items)} accordion items trouvés")

            for item in accordion_items:
                # Extraire le titre du module (H2/H3 = nom du module, ex: "Python Basics")
                module_title = ''
                title_elem = item.find(['h2', 'h3', 'h4'])
                if title_elem:
                    module_title = title_elem.get_text(strip=True)

                # Si pas de titre, passer
                if not module_title:
                    continue

                # Extraire le numéro du module depuis le texte complet de l'accordéon
                # Chercher "Module 1", "Module 2", etc. n'importe où dans l'item
                item_text = item.get_text(separator=' ', strip=True)
                module_number_match = re.search(r'Module\s*(\d+)', item_text, re.IGNORECASE)

                if module_number_match:
                    module_num = int(module_number_match.group(1))
                else:
                    # Si pas de numéro explicite, utiliser l'index
                    module_num = len(result['modules']) + 1

                module_data = {
                    'module_number': module_num,
                    'title': module_title,
                    'duration': '',
                    'description': '',
                    'content': {
                        'videos': 0,
                        'readings': 0,
                        'assignments': 0,
                        'quizzes': 0
                    },
                    'topics': []
                }

                # Extraire la durée (ex: "2 hours to complete")
                # Chercher dans le texte complet pour trouver "X hours/minutes to complete"
                duration_match = re.search(r'(\d+)\s*(hour|minute)s?\s+to\s+complete', item_text, re.IGNORECASE)
                if duration_match:
                    num = duration_match.group(1)
                    unit = duration_match.group(2)
                    module_data['duration'] = f"{num} {unit}{'s' if int(num) > 1 else ''} to complete"

                # Extraire la description du module
                # Généralement dans un paragraphe ou div après "Module details"
                all_text = item.get_text(separator=' ', strip=True)

                # Chercher la description après "Module details"
                desc_match = re.search(r'Module details\s+(.+?)(?:Show info|Module \d+|$)', all_text, re.IGNORECASE)
                if desc_match:
                    description = desc_match.group(1).strip()
                    # Limiter la longueur
                    if len(description) > 50:
                        module_data['description'] = description[:500]

                # Extraire le contenu (vidéos, lectures, etc.)
                # NOTE: Le contenu détaillé des modules (nombre de vidéos/lectures) est chargé dynamiquement
                # via JavaScript sur Coursera. Un scraping avec requests ne peut pas y accéder.
                # Solution future: Utiliser Selenium pour cliquer sur les accordéons.
                # Pour l'instant, on se concentre sur les topics visibles.
                content_matches = re.findall(r'(\d+)\s*(video|reading|quiz|assignment)', item_text, re.IGNORECASE)

                # Compter en prenant le premier match de chaque type (le résumé du module)
                video_counts = [int(m[0]) for m in content_matches if 'video' in m[1].lower()]
                reading_counts = [int(m[0]) for m in content_matches if 'reading' in m[1].lower()]
                quiz_counts = [int(m[0]) for m in content_matches if 'quiz' in m[1].lower()]
                assignment_counts = [int(m[0]) for m in content_matches if 'assignment' in m[1].lower()]

                # Prendre le premier (généralement le résumé) ou la somme si plusieurs
                if video_counts:
                    module_data['content']['videos'] = video_counts[0]
                if reading_counts:
                    module_data['content']['readings'] = reading_counts[0]
                if quiz_counts:
                    module_data['content']['quizzes'] = quiz_counts[0]
                if assignment_counts:
                    module_data['content']['assignments'] = assignment_counts[0]

                # Extraire les topics/sujets du module
                # Chercher les listes <ul><li> dans l'accordion
                topic_lists = item.find_all('ul')
                for ul in topic_lists:
                    topics = ul.find_all('li')
                    for topic in topics:
                        topic_text = topic.get_text(strip=True)

                        # Nettoyer pour extraire UNIQUEMENT le titre
                        # Enlever la durée (ex: "• 3 minutes", "· 2 hours")
                        topic_title = re.sub(r'\s*[•·]\s*\d+\s*(minute|hour)s?.*$', '', topic_text)
                        # Enlever les durées courtes (ex: "3 min", "2h")
                        topic_title = re.sub(r'\s*\d+\s*(min|h).*$', '', topic_title)
                        # Enlever les bullet points restants
                        topic_title = re.sub(r'^\s*[•·]\s*', '', topic_title).strip()

                        # Filtrer les topics valides (pas trop courts, pas trop longs)
                        if 5 < len(topic_title) < 200:
                            module_data['topics'].append(topic_title)

                # Limiter à 15 topics par module
                module_data['topics'] = module_data['topics'][:15]

                result['modules'].append(module_data)
                modules_found = True

            # Extraire le nombre total de modules depuis "There are X modules"
            modules_count_text = soup.find(string=lambda text: text and 'modules in this course' in text.lower())
            if modules_count_text:
                match = re.search(r'(\d+)\s+modules?', modules_count_text, re.IGNORECASE)
                if match:
                    result['total_modules'] = int(match.group(1))

        if not modules_found:
            # Stratégie 2: Chercher "There are X modules" et parser la structure
            modules_text = soup.find(string=lambda text: text and 'modules in this course' in text.lower())
            if modules_text:
                # Extraire le nombre
                import re
                match = re.search(r'(\d+)\s+modules?', modules_text, re.IGNORECASE)
                if match:
                    result['total_modules'] = int(match.group(1))
                    print(f"[INFO] {result['total_modules']} modules détectés")

            # Chercher les sections de modules individuels
            # Coursera utilise souvent des divs avec "Module X" dans le titre
            all_headings = soup.find_all(['h2', 'h3', 'h4'])

            for i, heading in enumerate(all_headings):
                heading_text = heading.get_text(strip=True)

                # Détecter "Module 1", "Week 1", etc.
                if re.match(r'(Module|Week|Semaine)\s*\d+', heading_text, re.IGNORECASE):
                    module_data = {
                        'module_number': len(result['modules']) + 1,
                        'title': heading_text,
                        'duration': '',
                        'description': '',
                        'content': {
                            'videos': 0,
                            'readings': 0,
                            'assignments': 0,
                            'quizzes': 0
                        },
                        'topics': []
                    }

                    # Chercher la durée (ex: "2 hours to complete")
                    next_elem = heading.find_next_sibling()
                    if next_elem:
                        duration_text = next_elem.get_text(strip=True)
                        if 'hour' in duration_text.lower() or 'minute' in duration_text.lower():
                            module_data['duration'] = duration_text

                    # Chercher le conteneur parent du module
                    module_container = heading.find_parent(['div', 'section'])
                    if module_container:
                        # Extraire la description du module
                        # Généralement dans un <p> ou <div> après le titre
                        desc_elem = module_container.find('p')
                        if desc_elem:
                            desc_text = desc_elem.get_text(strip=True)
                            if len(desc_text) > 50:  # Assez long pour être une description
                                module_data['description'] = desc_text[:500]

                        # Compter les contenus (vidéos, lectures, etc.)
                        # Chercher les icônes ou les textes comme "6 videos", "5 readings"
                        content_items = module_container.find_all(string=re.compile(r'\d+\s*(video|reading|assignment|quiz)', re.IGNORECASE))

                        for item in content_items:
                            text = item.strip().lower()
                            match = re.search(r'(\d+)\s*(video|reading|assignment|quiz)', text)
                            if match:
                                count = int(match.group(1))
                                content_type = match.group(2)

                                if 'video' in content_type:
                                    module_data['content']['videos'] = count
                                elif 'reading' in content_type:
                                    module_data['content']['readings'] = count
                                elif 'assignment' in content_type:
                                    module_data['content']['assignments'] = count
                                elif 'quiz' in content_type:
                                    module_data['content']['quizzes'] = count

                        # Extraire les topics (titres des vidéos/lectures)
                        # Chercher les listes dans le module
                        topic_lists = module_container.find_all('ul')
                        for ul in topic_lists:
                            topics = ul.find_all('li')
                            for topic in topics[:10]:  # Max 10 topics par module
                                topic_text = topic.get_text(strip=True)
                                # Filtrer les topics valides (pas trop courts)
                                if len(topic_text) > 15 and len(topic_text) < 200:
                                    # Enlever la durée si présente (ex: "Introduction • 4 minutes")
                                    topic_clean = re.sub(r'\s*[•·]\s*\d+\s*(minute|hour)s?', '', topic_text)
                                    module_data['topics'].append(topic_clean.strip())

                    result['modules'].append(module_data)
                    modules_found = True

        # Mise à jour du total si pas encore défini
        if result['total_modules'] == 0:
            result['total_modules'] = len(result['modules'])

        if modules_found and result['modules']:
            print(f"[SUCCESS] {len(result['modules'])} modules extraits avec détails")
            for i, module in enumerate(result['modules'], 1):
                print(f"  Module {i}: {module['title']}")
                print(f"    - Durée: {module['duration'] or 'N/A'}")
                print(f"    - Contenu: {module['content']['videos']} vidéos, {module['content']['readings']} lectures")
                print(f"    - Topics: {len(module['topics'])} sujets")
            return result
        else:
            print("[WARNING] Aucun module détaillé trouvé, fallback sur 'What you'll learn'")
            # Fallback: utiliser l'ancienne méthode
            learning_objectives = scrape_what_you_learn(course_url, timeout)
            if learning_objectives:
                result['modules'] = [{
                    'module_number': 1,
                    'title': 'Course Content',
                    'description': 'What you will learn',
                    'topics': learning_objectives,
                    'content': {}
                }]
                result['total_modules'] = 1
            return result

    except Exception as e:
        print(f"[ERROR] Erreur lors du scraping des modules: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'course_title': '', 'total_modules': 0, 'modules': []}


def format_modules_for_quiz_context(modules_data: dict) -> str:
    """
    Formate les données des modules en contexte texte pour le LLM

    Args:
        modules_data: Résultat de scrape_course_modules_details()

    Returns:
        Texte formaté avec tous les détails du cours
    """
    if not modules_data or not modules_data.get('modules'):
        return "Aucune information de module disponible."

    context = f"Cours : {modules_data.get('course_title', 'N/A')}\n"
    context += f"Nombre de modules : {modules_data.get('total_modules', 0)}\n\n"

    for module in modules_data['modules']:
        context += f"=== {module['title']} ===\n"

        if module.get('duration'):
            context += f"Durée : {module['duration']}\n"

        if module.get('description'):
            context += f"Description : {module['description']}\n"

        # Contenu du module
        content = module.get('content', {})
        if any(content.values()):
            context += f"Contenu : "
            content_parts = []
            if content.get('videos'):
                content_parts.append(f"{content['videos']} vidéos")
            if content.get('readings'):
                content_parts.append(f"{content['readings']} lectures")
            if content.get('assignments'):
                content_parts.append(f"{content['assignments']} devoirs")
            if content.get('quizzes'):
                content_parts.append(f"{content['quizzes']} quiz")
            context += ", ".join(content_parts) + "\n"

        # Topics couverts
        if module.get('topics'):
            context += f"Sujets abordés :\n"
            for topic in module['topics']:
                context += f"  - {topic}\n"

        context += "\n"

    return context


def extract_course_info_from_db(db_path: str, course_url: str) -> dict:
    """
    Récupère les informations d'un cours depuis la BDD locale

    Args:
        db_path: Chemin vers coursera_fast.db
        course_url: URL du cours

    Returns:
        Dictionnaire avec les infos du cours
    """
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, description, difficulty, duration, partner_name, categories
            FROM courses
            WHERE url = ?
        """, (course_url,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'title': result[0],
                'description': result[1],
                'difficulty': result[2],
                'duration': result[3],
                'partner': result[4],
                'categories': result[5]
            }
        else:
            return {}

    except Exception as e:
        print(f"[ERROR] Erreur lors de la récupération des infos du cours: {e}")
        return {}


# === TESTS ===
if __name__ == "__main__":
    # Test avec un cours Python réel
    test_url = "https://www.coursera.org/learn/python-for-applied-data-science-ai"

    print("="*80)
    print("TEST DU SCRAPER COURSERA")
    print("="*80)

    learning_objectives = scrape_what_you_learn(test_url)

    if learning_objectives:
        print(f"\n[OK] Test reussi ! {len(learning_objectives)} objectifs trouves:")
        for i, obj in enumerate(learning_objectives, 1):
            print(f"{i}. {obj}")
    else:
        print("\n[ERROR] Test echoue : Aucun objectif trouve")

    # Test du contexte formaté
    print("\n" + "="*80)
    print("CONTEXTE FORMATÉ POUR LE LLM:")
    print("="*80)
    context = get_course_learning_context(test_url)
    print(context)
