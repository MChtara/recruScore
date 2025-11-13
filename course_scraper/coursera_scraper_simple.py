"""
Scraper Coursera Simplifié - Version Rapide
Champs scrapés:
- title, description, partner_name, url
- categories, difficulty, duration, language
(Pas de rating pour plus de rapidité)
"""
import requests
import json
import sqlite3
import time
from typing import List, Dict

class CourseraSimpleScraper:
    """Scraper simplifié pour Coursera - version rapide sans rating"""

    def __init__(self, db_path: str = "coursera_simple.db"):
        self.db_path = db_path
        self.base_url = "https://www.coursera.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        self.init_database()

    def init_database(self):
        """Initialiser la base de données avec uniquement les champs essentiels"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
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
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_course_id ON courses(course_id)")

        conn.commit()
        conn.close()
        print("Base de donnees initialisee")

    def scrape_courses(self, max_courses: int = None):
        """
        Scraper les cours RAPIDEMENT (sans rating)
        Sauvegarde par batch pour plus de rapidité
        """
        print("\nScraping rapide des cours (sans rating)...")
        print("Les cours seront sauvegardes par batch\n")

        all_courses = []
        start_index = 0
        limit = 100

        # Étape 1: Récupérer les cours via API
        while True:
            if max_courses and len(all_courses) >= max_courses:
                break

            try:
                url = f"{self.base_url}/api/courses.v1"
                params = {
                    'start': start_index,
                    'limit': limit,
                    'fields': 'name,description,partnerIds,photoUrl,workload,slug,primaryLanguages,domainTypes,level'
                }

                response = self.session.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    break

                data = response.json()
                elements = data.get('elements', [])

                if not elements:
                    break

                all_courses.extend(elements)
                print(f"Recuperes: {len(all_courses)} cours (batch {start_index}-{start_index+limit})")

                start_index += limit
                time.sleep(0.3)

            except Exception as e:
                print(f"Erreur API: {e}")
                break

        # Étape 2: Récupérer les partenaires
        print(f"\nRecuperation des partenaires...")
        all_partner_ids = set()
        for course in all_courses:
            partner_ids = course.get('partnerIds', [])
            all_partner_ids.update(partner_ids)

        partners_map = self.fetch_partners(list(all_partner_ids))

        # Enrichir avec noms de partenaires
        for course in all_courses:
            partner_ids = course.get('partnerIds', [])
            if partner_ids and partner_ids[0] in partners_map:
                course['partner_name'] = partners_map[partner_ids[0]].get('name')

        print(f"\nTotal: {len(all_courses)} cours recuperes")

        # Étape 3: Sauvegarder en batch (beaucoup plus rapide)
        print(f"\nSauvegarde des cours en base...")
        saved_count = self.save_to_db(all_courses)

        print(f"\nTermine! {saved_count} cours sauvegardes")
        return saved_count

    def fetch_partners(self, partner_ids: List[str]) -> Dict:
        """Récupérer les noms des partenaires"""
        partners_map = {}
        batch_size = 100

        for i in range(0, len(partner_ids), batch_size):
            batch = partner_ids[i:i+batch_size]
            try:
                url = f"{self.base_url}/api/partners.v1"
                params = {'ids': ','.join(batch), 'fields': 'name'}
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    for partner in data.get('elements', []):
                        partners_map[partner['id']] = partner

                time.sleep(0.3)
            except:
                continue

        return partners_map


    def save_to_db(self, courses: List[Dict], sync_chromadb: bool = True):
        """
        Sauvegarder une liste de cours en batch (optimisé)

        Args:
            courses: Liste des cours à sauvegarder
            sync_chromadb: Si True, synchroniser automatiquement avec ChromaDB
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        saved = 0
        new_courses = []  # Pour ChromaDB

        try:
            for course in courses:
                # Extraire les champs
                course_id = course.get('id', course.get('slug'))
                slug = course.get('slug')
                title = course.get('title') or course.get('name')
                description = course.get('description')
                partner_name = course.get('partner_name')

                # Construire URL
                url = f"{self.base_url}/learn/{slug}" if slug else None

                # Categories
                categories = None
                if 'domainTypes' in course:
                    domain_types = course.get('domainTypes', [])
                    if domain_types:
                        cats = [f"{d.get('domainId', '')}/{d.get('subdomainId', '')}" for d in domain_types]
                        categories = json.dumps(cats)

                # Difficulté
                difficulty = course.get('level')

                # Durée
                duration = course.get('workload')

                # Langue
                language = None
                primary_langs = course.get('primaryLanguages', [])
                if primary_langs:
                    language = primary_langs[0] if isinstance(primary_langs, list) else primary_langs

                cursor.execute("""
                    INSERT OR REPLACE INTO courses
                    (course_id, slug, title, description, partner_name, url,
                     categories, difficulty, duration, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    course_id, slug, title, description, partner_name, url,
                    categories, difficulty, duration, language
                ))
                saved += 1

                # Préparer pour ChromaDB
                if sync_chromadb and title:
                    new_courses.append({
                        'course_id': course_id,
                        'title': title,
                        'description': description,
                        'metadata': {
                            'difficulty': difficulty or 'Non spécifié',
                            'duration': duration or 'Non spécifié',
                            'partner_name': partner_name or 'Coursera',
                            'url': url or '',
                            'categories': categories or '[]'
                        }
                    })

            conn.commit()
            print(f"Sauvegarde: {saved} cours dans SQLite")

            # NOUVEAU: Synchronisation automatique avec ChromaDB
            if sync_chromadb and new_courses:
                try:
                    from course_embedding_store import CourseEmbeddingStore

                    print(f"[INFO] Synchronisation de {len(new_courses)} cours vers ChromaDB...")
                    store = CourseEmbeddingStore(
                        db_path=self.db_path,
                        chroma_path="./chroma_db"
                    )

                    # Ajouter les nouveaux cours en batch
                    success, failed = store.add_courses_batch(new_courses)
                    print(f"[OK] ChromaDB: {success} cours ajoutés, {failed} échecs")

                except ImportError:
                    print(f"[WARNING] ChromaDB non disponible, synchronisation ignorée")
                except Exception as e:
                    print(f"[WARNING] Erreur synchronisation ChromaDB: {e}")

        except Exception as e:
            print(f"Erreur sauvegarde: {e}")
        finally:
            conn.close()

        return saved

    def get_stats(self):
        """Afficher les statistiques"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM courses")
        total = cursor.fetchone()[0]

        print(f"\nStatistiques:")
        print(f"Total: {total} cours")

        # Top 5 par partenaire
        cursor.execute("""
            SELECT partner_name, COUNT(*) as count
            FROM courses
            WHERE partner_name IS NOT NULL
            GROUP BY partner_name
            ORDER BY count DESC
            LIMIT 5
        """)

        print(f"\nTop 5 des partenaires avec le plus de cours:")
        for i, (partner, count) in enumerate(cursor.fetchall(), 1):
            print(f"{i}. {partner}: {count} cours")

        conn.close()


def main():
    """Fonction principale"""
    import sys

    print("=" * 80)
    print("COURSERA SCRAPER RAPIDE - SANS RATING")
    print("=" * 80)

    scraper = CourseraSimpleScraper(db_path="coursera_fast.db")

    print("\nOptions:")
    print("1. Scraper 100 cours (test rapide - ~30 sec)")
    print("2. Scraper 1000 cours (~2 min)")
    print("3. Scraper TOUS les cours (~15-20 min)")

    choice = input("\nVotre choix (1-3): ").strip()

    if choice == "1":
        max_courses = 100
    elif choice == "2":
        max_courses = 1000
    elif choice == "3":
        max_courses = None
    else:
        print("Choix invalide")
        return

    start = time.time()
    saved_count = scraper.scrape_courses(max_courses=max_courses)

    elapsed = time.time() - start
    print(f"\nTemps total: {elapsed/60:.1f} minutes ({elapsed:.0f} secondes)")

    scraper.get_stats()
    print(f"\nBase de donnees: coursera_fast.db")
    print("Scraping rapide termine!")


if __name__ == "__main__":
    main()
