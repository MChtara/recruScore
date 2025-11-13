"""
Script de migration pour ChromaDB
Charge tous les cours depuis SQLite et génère les embeddings dans ChromaDB
"""

from course_embedding_store import CourseEmbeddingStore
import time


def main():
    """Migration complète vers ChromaDB"""
    print("=" * 80)
    print("MIGRATION DES EMBEDDINGS VERS CHROMADB")
    print("=" * 80)

    print("\nCe script va:")
    print("  1. Charger tous les cours depuis coursera_fast.db (SQLite)")
    print("  2. Générer les embeddings avec Sentence-BERT (all-MiniLM-L6-v2)")
    print("  3. Stocker les embeddings dans ChromaDB pour recherches rapides")
    print("\nTemps estimé: ~5-10 minutes pour 5000+ cours")

    choice = input("\nContinuer? (o/n): ").strip().lower()
    if choice != 'o':
        print("Migration annulée")
        return

    # Initialiser le store
    print("\n[INFO] Initialisation de ChromaDB...")

    # Déterminer le chemin correct de la base de données
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "coursera_fast.db")
    chroma_path = os.path.join(script_dir, "chroma_db")

    print(f"[INFO] Base de données SQLite: {db_path}")
    print(f"[INFO] Dossier ChromaDB: {chroma_path}")

    # Vérifier que la base SQLite existe
    if not os.path.exists(db_path):
        print(f"\n[ERROR] Base de données non trouvée: {db_path}")
        print(f"[INFO] Assurez-vous que coursera_fast.db existe dans le dossier course_scraper/")
        return

    store = CourseEmbeddingStore(
        db_path=db_path,
        chroma_path=chroma_path
    )

    # Vérifier si des embeddings existent déjà
    current_count = store.get_count()
    if current_count > 0:
        print(f"\n[WARNING] {current_count} embeddings déjà présents dans ChromaDB")
        reset = input("Voulez-vous les supprimer et recommencer? (o/n): ").strip().lower()
        if reset == 'o':
            print("[INFO] Réinitialisation de la collection...")
            store.reset()
            current_count = 0

    # Demander le batch size
    batch_input = input("\nBatch size (défaut: 100): ").strip()
    batch_size = int(batch_input) if batch_input else 100

    # Lancer la synchronisation
    print("\n" + "=" * 80)
    start_time = time.time()

    added, failed = store.sync_from_sqlite(batch_size=batch_size)

    elapsed = time.time() - start_time

    # Afficher le résumé
    print("\n" + "=" * 80)
    print("MIGRATION TERMINÉE")
    print("=" * 80)
    print(f"\nRésultats:")
    print(f"  - Cours ajoutés: {added}")
    print(f"  - Échecs: {failed}")
    print(f"  - Total dans ChromaDB: {store.get_count()}")
    print(f"  - Temps total: {elapsed/60:.1f} minutes ({elapsed:.0f} secondes)")

    if added > 0:
        print(f"  - Vitesse: {added/elapsed:.1f} cours/sec")

    # Test de recherche
    if store.get_count() > 0:
        print("\n" + "=" * 80)
        print("TEST DE RECHERCHE")
        print("=" * 80)

        test_query = "Learn Python programming"
        print(f"\nRequête de test: '{test_query}'")

        test_start = time.time()
        results = store.search_similar_courses(test_query, n_results=3)
        test_elapsed = (time.time() - test_start) * 1000  # en ms

        if results:
            print(f"\nTop 3 résultats (recherche en {test_elapsed:.1f}ms):")
            for i, course in enumerate(results, 1):
                print(f"\n{i}. {course['title'][:60]}...")
                print(f"   Similarité: {course['score_similarite']}%")
                print(f"   Difficulté: {course['difficulty']}")
        else:
            print("[WARNING] Aucun résultat trouvé")

    print("\n" + "=" * 80)
    print("Migration terminée avec succès!")
    print(f"Base ChromaDB: ./chroma_db")
    print("=" * 80)


if __name__ == "__main__":
    main()
