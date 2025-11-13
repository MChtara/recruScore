"""
Script de mise à jour hebdomadaire des cours Coursera
Détecte les nouveaux cours et met à jour la base de données
"""
import sqlite3
import time
from datetime import datetime
from coursera_scraper_simple import CourseraSimpleScraper
from typing import List, Dict
import json

class WeeklyUpdater:
    """Gestionnaire de mise à jour hebdomadaire"""

    def __init__(self, db_path: str = "coursera_fast.db"):
        self.db_path = db_path
        self.scraper = CourseraSimpleScraper(db_path=db_path)
        self.log_file = "update_log.txt"

    def get_existing_course_ids(self) -> set:
        """Récupérer les IDs des cours déjà en base"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT course_id FROM courses")
        existing_ids = {row[0] for row in cursor.fetchall()}

        conn.close()
        return existing_ids

    def run_weekly_update(self, max_courses: int = None, smart_mode: bool = True):
        """
        Exécuter la mise à jour hebdomadaire

        Args:
            max_courses: Limite de cours à scraper (None = tous)
            smart_mode: Si True, arrête dès qu'il n'y a plus de nouveaux cours

        Retourne le nombre de nouveaux cours ajoutés
        """
        print("=" * 80)
        print(f"MISE A JOUR HEBDOMADAIRE - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 80)

        # Étape 1: Récupérer les cours existants
        print("\n[1/3] Récupération des cours existants...")
        existing_ids = self.get_existing_course_ids()
        print(f"Cours actuels en base: {len(existing_ids)}")

        # Étape 2: Scraper intelligemment
        print("\n[2/3] Scraping des cours Coursera...")
        if smart_mode:
            print("Mode intelligent activé: arrêt dès qu'il n'y a plus de nouveaux cours")

        start_time = time.time()

        if smart_mode:
            total_saved, courses_scraped = self.smart_scrape_courses(existing_ids, max_courses)
        else:
            total_saved = self.scraper.scrape_courses(max_courses=max_courses)
            courses_scraped = total_saved

        elapsed = time.time() - start_time
        print(f"Temps de scraping: {elapsed/60:.1f} minutes")

        # Étape 3: Identifier les nouveaux cours
        print("\n[3/3] Identification des nouveaux cours...")
        new_ids = self.get_existing_course_ids() - existing_ids
        new_count = len(new_ids)

        # Générer le rapport
        report = self.generate_report(new_count, new_ids, elapsed, courses_scraped)

        # Sauvegarder le log
        self.save_log(report)

        print("\n" + "=" * 80)
        print(report)
        print("=" * 80)

        return new_count

    def smart_scrape_courses(self, existing_ids: set, max_courses: int = None):
        """
        Scraping intelligent: arrête dès qu'il n'y a plus de nouveaux cours

        Stratégie:
        - Scrape par batch de 100 cours
        - Vérifie combien sont nouveaux dans chaque batch
        - Si un batch a < 10% de nouveaux cours, on arrête
        - Sauvegarde au fur et à mesure

        Returns:
            (total_saved, total_scraped): nombre de cours sauvegardés et scrapés
        """
        import requests

        all_courses = []
        start_index = 0
        limit = 100
        total_scraped = 0
        consecutive_old_batches = 0
        new_courses_found = 0

        print("\nScraping intelligent en cours...")

        while True:
            if max_courses and total_scraped >= max_courses:
                break

            try:
                # Récupérer un batch via l'API
                url = f"{self.scraper.base_url}/api/courses.v1"
                params = {
                    'start': start_index,
                    'limit': limit,
                    'fields': 'name,description,partnerIds,photoUrl,workload,slug,primaryLanguages,domainTypes,level'
                }

                response = self.scraper.session.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    break

                data = response.json()
                elements = data.get('elements', [])

                if not elements:
                    print("Fin de la liste des cours")
                    break

                # Compter combien sont nouveaux dans ce batch
                batch_new_count = 0
                for course in elements:
                    course_id = course.get('id', course.get('slug'))
                    if course_id not in existing_ids:
                        batch_new_count += 1

                total_scraped += len(elements)
                new_courses_found += batch_new_count

                percentage_new = (batch_new_count / len(elements)) * 100

                print(f"Batch {start_index}-{start_index+limit}: "
                      f"{len(elements)} cours, {batch_new_count} nouveaux ({percentage_new:.0f}%)")

                all_courses.extend(elements)

                # Condition d'arrêt intelligente
                if batch_new_count == 0:
                    consecutive_old_batches += 1
                else:
                    consecutive_old_batches = 0

                # Arrêter si 3 batchs consécutifs sans nouveaux cours
                if consecutive_old_batches >= 3:
                    print(f"\nArrêt: 3 batchs consécutifs sans nouveaux cours")
                    print(f"Total scrapé: {total_scraped} cours (au lieu de potentiellement 16000+)")
                    break

                # Arrêter si très peu de nouveaux cours (< 5%)
                if total_scraped >= 500 and percentage_new < 5:
                    print(f"\nArrêt: moins de 5% de nouveaux cours dans ce batch")
                    print(f"Total scrapé: {total_scraped} cours")
                    break

                start_index += limit
                time.sleep(0.3)

            except Exception as e:
                print(f"Erreur API: {e}")
                break

        if not all_courses:
            return 0, 0

        # Récupérer les partenaires
        print(f"\nRécupération des partenaires pour {len(all_courses)} cours...")
        all_partner_ids = set()
        for course in all_courses:
            partner_ids = course.get('partnerIds', [])
            all_partner_ids.update(partner_ids)

        partners_map = self.scraper.fetch_partners(list(all_partner_ids))

        # Enrichir avec noms de partenaires
        for course in all_courses:
            partner_ids = course.get('partnerIds', [])
            if partner_ids and partner_ids[0] in partners_map:
                course['partner_name'] = partners_map[partner_ids[0]].get('name')

        # Sauvegarder en base
        print(f"\nSauvegarde de {len(all_courses)} cours...")
        saved_count = self.scraper.save_to_db(all_courses)

        print(f"\nRésumé du scraping intelligent:")
        print(f"  - Cours scrapés: {total_scraped}")
        print(f"  - Nouveaux cours trouvés: {new_courses_found}")
        print(f"  - Cours sauvegardés: {saved_count}")

        return saved_count, total_scraped

    def generate_report(self, new_count: int, new_ids: set, elapsed_time: float, courses_scraped: int = 0) -> str:
        """Générer un rapport de mise à jour"""
        report_lines = []
        report_lines.append(f"RAPPORT DE MISE A JOUR - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report_lines.append("-" * 80)
        report_lines.append(f"Cours scrapés: {courses_scraped}")
        report_lines.append(f"Nouveaux cours détectés: {new_count}")
        report_lines.append(f"Temps d'exécution: {elapsed_time/60:.1f} minutes ({elapsed_time:.0f} secondes)")

        if new_count > 0:
            report_lines.append("\nDétails des nouveaux cours:")
            # Récupérer les détails des nouveaux cours
            new_courses = self.get_course_details(list(new_ids)[:10])  # Max 10 pour le rapport

            for i, course in enumerate(new_courses, 1):
                title = course['title'][:60]
                partner = course['partner_name'] or 'N/A'
                report_lines.append(f"  {i}. {title} - {partner}")

            if new_count > 10:
                report_lines.append(f"  ... et {new_count - 10} autres cours")
        else:
            report_lines.append("\nAucun nouveau cours détecté.")

        # Statistiques globales
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM courses")
        total = cursor.fetchone()[0]
        conn.close()

        report_lines.append(f"\nTotal de cours en base: {total}")

        return "\n".join(report_lines)

    def get_course_details(self, course_ids: List[str]) -> List[Dict]:
        """Récupérer les détails de cours spécifiques"""
        if not course_ids:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        placeholders = ','.join(['?' for _ in course_ids])
        cursor.execute(f"""
            SELECT course_id, title, partner_name, url
            FROM courses
            WHERE course_id IN ({placeholders})
        """, course_ids)

        courses = []
        for row in cursor.fetchall():
            courses.append({
                'course_id': row[0],
                'title': row[1],
                'partner_name': row[2],
                'url': row[3]
            })

        conn.close()
        return courses

    def save_log(self, report: str):
        """Sauvegarder le rapport dans un fichier log"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write("\n\n")
            f.write(report)
            f.write("\n" + "=" * 80)

        print(f"\nRapport sauvegardé dans: {self.log_file}")

    def export_new_courses_json(self, new_ids: set, output_file: str = "nouveaux_cours.json"):
        """Exporter les nouveaux cours en JSON"""
        if not new_ids:
            return

        courses = self.get_course_details(list(new_ids))

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)

        print(f"Nouveaux cours exportés dans: {output_file}")


def main():
    """Fonction principale"""
    import sys

    print("Script de mise à jour hebdomadaire Coursera")
    print("=" * 80)

    # Créer l'updater
    updater = WeeklyUpdater(db_path="coursera_fast.db")

    # Options
    print("\nOptions:")
    print("1. Mise à jour complète (recommandé - scrape tous les cours)")
    print("2. Mise à jour test (100 cours seulement)")

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Mode automatique (pour Task Scheduler)
        print("\nMode automatique activé")
        max_courses = None
    else:
        # Mode interactif
        choice = input("\nVotre choix (1-2, défaut=1): ").strip() or "1"

        if choice == "2":
            max_courses = 100
        else:
            max_courses = None

    # Exécuter la mise à jour
    new_count = updater.run_weekly_update(max_courses=max_courses)

    # Exporter les nouveaux cours si nécessaire
    if new_count > 0:
        print("\nVoulez-vous exporter les nouveaux cours en JSON?")
        if len(sys.argv) > 1 and sys.argv[1] == "--auto":
            # En mode auto, toujours exporter
            export = True
        else:
            export = input("(o/n, défaut=n): ").strip().lower() == 'o'

        if export:
            new_ids = updater.get_existing_course_ids()
            updater.export_new_courses_json(new_ids, f"nouveaux_cours_{datetime.now().strftime('%Y%m%d')}.json")


if __name__ == "__main__":
    main()
