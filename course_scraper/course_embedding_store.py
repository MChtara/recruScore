"""
Course Embedding Store - Gestion des embeddings vectoriels avec ChromaDB
Optimise les recherches de similarité pour les recommandations de cours
"""

import chromadb
from chromadb.config import Settings
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Tuple
import os


class CourseEmbeddingStore:
    """
    Gestionnaire d'embeddings vectoriels pour les cours Coursera avec ChromaDB

    Features:
    - Stockage persistant des embeddings (384 dimensions)
    - Recherche rapide de similarité (HNSW indexing)
    - Synchronisation automatique avec SQLite
    - Gestion des métadonnées riches
    """

    def __init__(
        self,
        db_path: str = "coursera_fast.db",
        chroma_path: str = "./chroma_db",
        collection_name: str = "coursera_courses"
    ):
        """
        Initialiser le store d'embeddings

        Args:
            db_path: Chemin vers la base SQLite (métadonnées)
            chroma_path: Chemin vers la base ChromaDB (embeddings)
            collection_name: Nom de la collection ChromaDB
        """
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.model: Optional[SentenceTransformer] = None

        # Initialiser ChromaDB
        self._init_chromadb()

    def _init_chromadb(self):
        """Initialiser le client ChromaDB et la collection"""
        # Créer le dossier si nécessaire
        os.makedirs(self.chroma_path, exist_ok=True)

        # Initialiser le client avec persistance
        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(
                anonymized_telemetry=False,  # Désactiver la télémétrie
                allow_reset=True
            )
        )

        # Créer ou récupérer la collection
        # ChromaDB utilise cosine similarity par défaut (parfait pour nous)
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",  # Similarité cosinus
                "description": "Coursera courses with semantic embeddings"
            }
        )

        print(f"[INFO] ChromaDB initialisé: {self.chroma_path}")
        print(f"[INFO] Collection: {self.collection_name}")
        print(f"[INFO] Nombre d'embeddings: {self.collection.count()}")

    def load_model(self):
        """Charger le modèle Sentence-BERT"""
        if self.model is None:
            print("[INFO] Chargement du modèle Sentence-BERT (all-MiniLM-L6-v2)...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[OK] Modèle chargé (384 dimensions)")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Générer l'embedding pour un texte

        Args:
            text: Texte à encoder

        Returns:
            Embedding de 384 dimensions
        """
        if self.model is None:
            self.load_model()

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def add_course(
        self,
        course_id: str,
        title: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Ajouter un cours et son embedding à ChromaDB

        Args:
            course_id: ID unique du cours
            title: Titre du cours
            description: Description du cours
            metadata: Métadonnées additionnelles (difficulty, duration, etc.)

        Returns:
            True si ajouté avec succès
        """
        try:
            # Générer le texte combiné et l'embedding
            text = f"{title}. {description[:500] if description else ''}"
            embedding = self.generate_embedding(text)

            # Préparer les métadonnées
            course_metadata = {
                "title": title[:1000],  # ChromaDB limite à 1000 caractères
                "description": (description[:500] + "...") if description and len(description) > 500 else (description or "")
            }

            # Ajouter les métadonnées supplémentaires
            if metadata:
                course_metadata.update(metadata)

            # Ajouter à ChromaDB
            self.collection.add(
                ids=[course_id],
                embeddings=[embedding],
                metadatas=[course_metadata],
                documents=[text[:1000]]  # Texte pour référence
            )

            return True

        except Exception as e:
            print(f"[ERROR] Impossible d'ajouter le cours {course_id}: {e}")
            return False

    def add_courses_batch(self, courses: List[Dict]) -> Tuple[int, int]:
        """
        Ajouter plusieurs cours en batch (plus rapide)

        Args:
            courses: Liste de dictionnaires avec keys: course_id, title, description, metadata

        Returns:
            Tuple (succès, échecs)
        """
        if not courses:
            return 0, 0

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        success = 0
        failed = 0

        for course in courses:
            try:
                course_id = str(course['course_id'])
                title = course['title']
                description = course.get('description', '')

                # Générer le texte et l'embedding
                text = f"{title}. {description[:500] if description else ''}"
                embedding = self.generate_embedding(text)

                # Préparer les métadonnées
                metadata = {
                    "title": title[:1000],
                    "description": (description[:500] + "...") if description and len(description) > 500 else (description or "")
                }

                # Ajouter métadonnées supplémentaires
                if 'metadata' in course:
                    metadata.update(course['metadata'])

                ids.append(course_id)
                embeddings.append(embedding)
                metadatas.append(metadata)
                documents.append(text[:1000])

                success += 1

            except Exception as e:
                print(f"[WARNING] Erreur pour cours {course.get('course_id', 'unknown')}: {e}")
                failed += 1
                continue

        # Ajouter le batch à ChromaDB
        if ids:
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
            except Exception as e:
                print(f"[ERROR] Erreur lors de l'ajout batch: {e}")
                return 0, len(courses)

        return success, failed

    def search_similar_courses(
        self,
        query: str,
        n_results: int = 10,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Rechercher les cours similaires à une requête

        Args:
            query: Requête de recherche (ex: "Learn Python")
            n_results: Nombre de résultats à retourner
            where: Filtres sur les métadonnées (ex: {"difficulty": "BEGINNER"})
            where_document: Filtres sur les documents

        Returns:
            Liste des cours similaires avec scores et métadonnées
        """
        try:
            # Générer l'embedding de la requête
            query_embedding = self.generate_embedding(query)

            # Rechercher dans ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["metadatas", "distances", "documents"]
            )

            # Formater les résultats
            courses = []

            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    course_id = results['ids'][0][i]
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    # Convertir distance en score de similarité (0-100)
                    # ChromaDB retourne distance cosinus (0 = identique, 2 = opposé)
                    # Similarité = (2 - distance) / 2 * 100
                    similarity_score = ((2 - distance) / 2) * 100

                    courses.append({
                        'course_id': course_id,
                        'title': metadata.get('title', ''),
                        'description': metadata.get('description', ''),
                        'difficulty': metadata.get('difficulty', 'Non spécifié'),
                        'duration': metadata.get('duration', 'Non spécifié'),
                        'partner_name': metadata.get('partner_name', 'Coursera'),
                        'url': metadata.get('url', ''),
                        'categories': metadata.get('categories', '[]'),
                        'score_similarite': round(similarity_score, 2),
                        'distance': round(distance, 4)
                    })

            return courses

        except Exception as e:
            print(f"[ERROR] Erreur de recherche: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_count(self) -> int:
        """Obtenir le nombre d'embeddings stockés"""
        return self.collection.count()

    def delete_course(self, course_id: str) -> bool:
        """Supprimer un cours de ChromaDB"""
        try:
            self.collection.delete(ids=[course_id])
            return True
        except Exception as e:
            print(f"[ERROR] Impossible de supprimer le cours {course_id}: {e}")
            return False

    def update_course(
        self,
        course_id: str,
        title: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Mettre à jour un cours (supprimer + rajouter)

        Args:
            course_id: ID du cours
            title: Nouveau titre
            description: Nouvelle description
            metadata: Nouvelles métadonnées

        Returns:
            True si mis à jour avec succès
        """
        self.delete_course(course_id)
        return self.add_course(course_id, title, description, metadata)

    def sync_from_sqlite(self, batch_size: int = 100) -> Tuple[int, int]:
        """
        Synchroniser tous les cours depuis SQLite vers ChromaDB

        Args:
            batch_size: Taille des batches pour l'ajout

        Returns:
            Tuple (ajoutés, échoués)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Charger le modèle une seule fois
            self.load_model()

            # Compter les cours
            cursor.execute("SELECT COUNT(*) FROM courses")
            total = cursor.fetchone()[0]

            print(f"\n[INFO] Synchronisation de {total} cours depuis SQLite...")

            # Récupérer tous les IDs déjà dans ChromaDB
            existing_ids = set()
            if self.collection.count() > 0:
                # Récupérer par batches pour éviter les limites de mémoire
                offset = 0
                limit = 1000
                while True:
                    results = self.collection.get(
                        limit=limit,
                        offset=offset,
                        include=[]
                    )
                    if not results['ids']:
                        break
                    existing_ids.update(results['ids'])
                    offset += limit
                    if len(results['ids']) < limit:
                        break

            print(f"[INFO] {len(existing_ids)} cours déjà dans ChromaDB")

            # Récupérer les cours depuis SQLite
            cursor.execute("""
                SELECT id, course_id, title, description, difficulty, duration,
                       partner_name, url, categories
                FROM courses
            """)

            added = 0
            failed = 0
            batch = []

            for row in cursor.fetchall():
                db_id, course_id, title, description, difficulty, duration, partner_name, url, categories = row

                # Utiliser course_id comme identifiant unique
                unique_id = str(course_id) if course_id else str(db_id)

                # Sauter si déjà présent
                if unique_id in existing_ids:
                    continue

                # Ajouter au batch
                batch.append({
                    'course_id': unique_id,
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

                # Traiter le batch
                if len(batch) >= batch_size:
                    success, fail = self.add_courses_batch(batch)
                    added += success
                    failed += fail

                    progress = ((added + failed) / (total - len(existing_ids))) * 100 if total > len(existing_ids) else 100
                    print(f"[PROGRESS] {added + failed}/{total - len(existing_ids)} cours traités ({progress:.1f}%)")

                    batch = []

            # Traiter le dernier batch
            if batch:
                success, fail = self.add_courses_batch(batch)
                added += success
                failed += fail

            print(f"\n[OK] Synchronisation terminée:")
            print(f"  - Ajoutés: {added}")
            print(f"  - Échoués: {failed}")
            print(f"  - Total dans ChromaDB: {self.collection.count()}")

            return added, failed

        except Exception as e:
            print(f"[ERROR] Erreur de synchronisation: {e}")
            import traceback
            traceback.print_exc()
            return 0, 0
        finally:
            conn.close()

    def reset(self):
        """Supprimer tous les embeddings (attention!)"""
        self.chroma_client.delete_collection(self.collection_name)
        print(f"[WARNING] Collection {self.collection_name} supprimée")
        self._init_chromadb()


def main():
    """Fonction de test"""
    print("=== TEST COURSE EMBEDDING STORE ===\n")

    # Initialiser le store
    store = CourseEmbeddingStore(
        db_path="coursera_fast.db",
        chroma_path="./chroma_db"
    )

    print(f"\nNombre d'embeddings actuels: {store.get_count()}")

    # Test de recherche
    print("\n=== TEST DE RECHERCHE ===")
    query = "Learn Python programming for beginners"
    print(f"Requête: {query}\n")

    results = store.search_similar_courses(query, n_results=5)

    if results:
        print(f"Top 5 résultats:")
        for i, course in enumerate(results, 1):
            print(f"\n{i}. {course['title']}")
            print(f"   Similarité: {course['score_similarite']}%")
            print(f"   Difficulté: {course['difficulty']}")
            print(f"   URL: {course['url']}")
    else:
        print("Aucun résultat (base vide?)")
        print("\nPour synchroniser depuis SQLite, lancez:")
        print("python migrate_embeddings_chromadb.py")


if __name__ == "__main__":
    main()
