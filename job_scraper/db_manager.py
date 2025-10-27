import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import hashlib
import json


class JobDatabase:
    """Gestionnaire de base de données SQLite pour les offres d'emploi"""
    
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self):
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_tables(self):
        """Crée les tables si elles n'existent pas"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Table principale des offres
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_hash TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                job_url TEXT,
                date_posted TEXT,
                job_type TEXT,
                salary TEXT,
                source TEXT NOT NULL,
                contrat TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Table des logs de scraping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scraper_name TEXT NOT NULL,
                status TEXT NOT NULL,
                jobs_found INTEGER DEFAULT 0,
                errors TEXT,
                execution_time REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index pour recherche rapide
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON jobs(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_date_posted ON jobs(date_posted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_location ON jobs(location)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_hash ON jobs(job_hash)')
        
        conn.commit()
        conn.close()
    
    def generate_job_hash(self, job: Dict) -> str:
        """Génère un hash unique pour une offre basé sur titre + entreprise + lieu"""
        key_data = f"{job.get('title', '').lower()}|{job.get('company', '').lower()}|{job.get('location', '').lower()}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def insert_job(self, job: Dict) -> bool:
        """
        Insère une offre dans la base (ignore si doublon)
        Returns: True si insertion réussie, False si doublon
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        job_hash = self.generate_job_hash(job)
        
        try:
            cursor.execute('''
                INSERT INTO jobs (
                    job_hash, title, company, location, description,
                    job_url, date_posted, job_type, salary, source, contrat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_hash,
                job.get('title'),
                job.get('company'),
                job.get('location'),
                job.get('description'),
                job.get('job_url'),
                job.get('date'),
                job.get('job_type'),
                job.get('salary'),
                job.get('source'),
                job.get('contrat')
            ))
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.IntegrityError:
            # Doublon détecté (même job_hash existe déjà)
            conn.close()
            return False
        except Exception as e:
            print(f"Erreur insertion job: {e}")
            conn.close()
            return False
    
    def bulk_insert_jobs(self, jobs: List[Dict], source: str) -> Dict[str, int]:
        """
        Insère plusieurs offres d'un coup
        Returns: {'inserted': nb_inserted, 'duplicates': nb_duplicates}
        """
        inserted = 0
        duplicates = 0
        
        for job in jobs:
            job['source'] = source
            if self.insert_job(job):
                inserted += 1
            else:
                duplicates += 1
        
        print(f"  ✅ {source}: {inserted} nouvelles offres, {duplicates} doublons ignorés")
        return {'inserted': inserted, 'duplicates': duplicates}
    
    def log_scraping(self, scraper_name: str, status: str, 
                     jobs_found: int = 0, errors: str = None, 
                     execution_time: float = 0):
        """Enregistre un log de scraping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scraping_logs (
                scraper_name, status, jobs_found, errors, execution_time
            ) VALUES (?, ?, ?, ?, ?)
        ''', (scraper_name, status, jobs_found, errors, execution_time))
        
        conn.commit()
        conn.close()
    
    def get_recent_jobs(self, limit: int = 100, source: Optional[str] = None) -> List[Dict]:
        """Récupère les offres récentes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if source:
            cursor.execute('''
                SELECT * FROM jobs 
                WHERE source = ? AND is_active = 1
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (source, limit))
        else:
            cursor.execute('''
                SELECT * FROM jobs 
                WHERE is_active = 1
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
        
        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jobs
    
    def search_jobs(self, keyword: Optional[str] = None, 
                    location: Optional[str] = None, 
                    source: Optional[str] = None,
                    limit: int = 500) -> List[Dict]:
        """Recherche d'offres avec filtres"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM jobs WHERE is_active = 1"
        params = []
        
        if keyword:
            query += " AND (title LIKE ? OR description LIKE ? OR company LIKE ?)"
            search_term = f"%{keyword}%"
            params.extend([search_term, search_term, search_term])
        
        if location:
            query += " AND location LIKE ?"
            params.append(f"%{location}%")
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += f" ORDER BY created_at DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jobs
    
    def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        """Récupère une offre par son ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM jobs WHERE id = ? AND is_active = 1", (job_id,))
        job = cursor.fetchone()
        conn.close()
        
        return dict(job) if job else None
    
    def get_statistics(self) -> Dict:
        """Statistiques générales de la base"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total d'offres actives
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
        total = cursor.fetchone()[0]
        
        # Par source
        cursor.execute('''
            SELECT source, COUNT(*) as count 
            FROM jobs 
            WHERE is_active = 1 
            GROUP BY source
            ORDER BY count DESC
        ''')
        by_source = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Offres aujourd'hui
        cursor.execute('''
            SELECT COUNT(*) FROM jobs 
            WHERE DATE(created_at) = DATE('now') AND is_active = 1
        ''')
        today = cursor.fetchone()[0]
        
        # Offres cette semaine
        cursor.execute('''
            SELECT COUNT(*) FROM jobs 
            WHERE DATE(created_at) >= DATE('now', '-7 days') AND is_active = 1
        ''')
        this_week = cursor.fetchone()[0]
        
        # Dernière mise à jour
        cursor.execute('''
            SELECT MAX(created_at) FROM jobs WHERE is_active = 1
        ''')
        last_update = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_jobs': total,
            'by_source': by_source,
            'jobs_today': today,
            'jobs_this_week': this_week,
            'last_update': last_update
        }
    
    def deactivate_job(self, job_id: int):
        """Désactive une offre (soft delete)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET is_active = 0 WHERE id = ?", (job_id,))
        conn.commit()
        conn.close()
    
    def cleanup_old_jobs(self, days: int = 90):
        """Désactive les offres de plus de X jours"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs 
            SET is_active = 0 
            WHERE DATE(created_at) < DATE('now', ?)
        ''', (f'-{days} days',))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected
    
    def export_to_csv(self, output_path: str, limit: Optional[int] = None):
        """Exporte les offres actives vers CSV"""
        import csv
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM jobs WHERE is_active = 1 ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        jobs = cursor.fetchall()
        
        if jobs:
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                # Utiliser les noms de colonnes
                fieldnames = [description[0] for description in cursor.description]
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                writer.writerows([dict(job) for job in jobs])
        
        conn.close()
        print(f"📊 Export CSV: {len(jobs)} offres dans {output_path}")
        return len(jobs)
    
    def get_scraping_logs(self, limit: int = 20) -> List[Dict]:
        """Récupère les derniers logs de scraping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM scraping_logs 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs


# Exemple d'utilisation
if __name__ == "__main__":
    db = JobDatabase()
    
    # Test insertion
    test_job = {
        'title': 'Développeur Python Senior',
        'company': 'TechCorp Tunisia',
        'location': 'Tunis, Tunisia',
        'description': 'Recherche développeur Python expérimenté pour projet innovant',
        'job_url': 'https://example.com/job/123',
        'date': '2025-10-01',
        'job_type': 'CDI',
        'salary': '2500 DT/mois',
        'source': 'Test',
        'contrat': 'CDI'
    }
    
    success = db.insert_job(test_job)
    print(f"Insertion test: {'✅ Succès' if success else '❌ Doublon'}")
    
    # Statistiques
    stats = db.get_statistics()
    print("\nStatistiques:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # Recherche
    results = db.search_jobs(keyword="python", limit=5)
    print(f"\nRecherche 'python': {len(results)} résultats")