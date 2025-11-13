# ats_scorer.py - Intégration ATS dans l'application Flask

import json
import requests
import PyPDF2
import pdfplumber
import os
from werkzeug.utils import secure_filename
from typing import Dict, Optional
import docx2txt
import tempfile

class ATSScorer:
    """Analyseur ATS intégré à Flask"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"  # Nouveau modèle VLM Groq
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}  # Seulement PDF et images
    
    def allowed_file(self, filename):
        """Vérifier si le fichier est autorisé"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def extraire_texte_fichier(self, file_path: str) -> str:
        """Extraire le texte selon le type de fichier"""
        extension = file_path.rsplit('.', 1)[1].lower()

        try:
            if extension == 'pdf':
                return self._extraire_pdf(file_path)
            elif extension in ['doc', 'docx']:
                return self._extraire_word(file_path)
            elif extension == 'txt':
                return self._extraire_txt(file_path)
            elif extension in ['jpg', 'jpeg', 'png']:
                return self._extraire_image_ocr(file_path)
            else:
                return ""
        except Exception as e:
            print(f"Erreur extraction {extension}: {e}")
            return ""

    def _extraire_image_ocr(self, file_path: str) -> str:
        """Extraire texte d'une image avec pytesseract OCR"""
        try:
            from PIL import Image
            import pytesseract
            import platform

            # Configurer le chemin Tesseract pour Windows
            if platform.system() == 'Windows':
                # Essayer différents chemins possibles
                possible_paths = [
                    r'D:\téléchargements\tesseract.exe',
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
                ]

                for path in possible_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        print(f"OCR: Utilise Tesseract depuis {path}")
                        break

            # Ouvrir l'image
            image = Image.open(file_path)
            print(f"OCR: Image ouverte - Taille: {image.size}, Mode: {image.mode}")

            # Extraire le texte (essayer français et anglais)
            try:
                texte = pytesseract.image_to_string(image, lang='fra+eng')
            except:
                # Fallback sur anglais uniquement
                texte = pytesseract.image_to_string(image, lang='eng')

            print(f"OCR: Extrait {len(texte)} caractères de l'image")
            return texte
        except ImportError as e:
            print(f"ERREUR: Module manquant - {e}. Installez: pip install pytesseract pillow")
            return ""
        except Exception as e:
            print(f"Erreur OCR: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _extraire_pdf(self, file_path: str) -> str:
        """Extraire texte d'un PDF"""
        # Méthode 1: pdfplumber (plus précise)
        try:
            with pdfplumber.open(file_path) as pdf:
                texte = '\n'.join(page.extract_text() or '' for page in pdf.pages)
                if texte.strip():
                    return texte
        except:
            pass
        
        # Méthode 2: PyPDF2 (fallback)
        try:
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                texte = '\n'.join(page.extract_text() or '' for page in pdf.pages)
                return texte
        except:
            return ""
    
    def _extraire_word(self, file_path: str) -> str:
        """Extraire texte d'un document Word"""
        try:
            return docx2txt.process(file_path)
        except:
            return ""
    
    def _extraire_txt(self, file_path: str) -> str:
        """Extraire texte d'un fichier TXT"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except:
                return ""
    
    def _generer_embedding_simple(self, texte: str) -> list:
        """
        Génère un embedding sémantique avec Sentence-BERT (all-MiniLM-L6-v2)

        Nouveau modèle : all-MiniLM-L6-v2
        - 384 dimensions (vs 100 avant)
        - Vraie compréhension sémantique
        - Gratuit et open-source
        - Fonctionne offline
        """
        try:
            from sentence_transformers import SentenceTransformer

            # Initialiser le modèle une seule fois (cache)
            if not hasattr(self, '_embedding_model'):
                print("[INFO] Chargement du modèle Sentence-BERT (all-MiniLM-L6-v2)...")
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("[OK] Modèle chargé avec succès")

            # Générer l'embedding (384 dimensions)
            embedding = self._embedding_model.encode(texte, convert_to_numpy=True)

            return embedding.tolist()

        except ImportError:
            print("[WARNING] sentence-transformers non installé, fallback sur TF-IDF")
            print("[INFO] Installez avec: pip install sentence-transformers")

            # Fallback : TF-IDF simplifié (ancien système)
            import re
            from collections import Counter
            import numpy as np

            texte_clean = re.sub(r'[^a-zA-Z\s]', '', texte.lower())
            mots = texte_clean.split()

            keywords_tech = [
                'python', 'java', 'javascript', 'sql', 'machine', 'learning', 'data', 'science',
                'ai', 'neural', 'deep', 'algorithm', 'model', 'framework', 'django', 'flask',
                'react', 'angular', 'vue', 'node', 'express', 'database', 'postgresql', 'mysql',
                'mongodb', 'docker', 'kubernetes', 'aws', 'azure', 'cloud', 'devops', 'git',
                'api', 'rest', 'graphql', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit',
                'statistics', 'analysis', 'visualization', 'backend', 'frontend', 'fullstack',
                'programming', 'development', 'software', 'engineering', 'architecture', 'design',
                'test', 'quality', 'security', 'performance', 'optimization', 'scalability',
                'microservices', 'distributed', 'systems', 'networking', 'web', 'mobile', 'app',
                'spring', 'hibernate', 'css', 'html', 'typescript', 'kotlin', 'swift', 'ruby',
                'rails', 'php', 'laravel', 'scala', 'hadoop', 'spark', 'kafka', 'redis',
                'elasticsearch', 'graphql', 'agile', 'scrum', 'jenkins', 'ansible', 'terraform',
                'linux', 'windows', 'macos', 'bash', 'powershell', 'ci', 'cd', 'testing'
            ]

            embedding = np.zeros(100)
            mot_freq = Counter(mots)
            total_mots = len(mots)

            for i, keyword in enumerate(keywords_tech[:100]):
                if keyword in mot_freq:
                    tf = mot_freq[keyword] / total_mots if total_mots > 0 else 0
                    embedding[i] = tf * 10

            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding.tolist()

    def _similarite_cosinus(self, vec1: list, vec2: list) -> float:
        """Calcule la similarité cosinus entre deux vecteurs"""
        import numpy as np

        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _calculer_score_nom(self, competence: str, titre: str, description: str = "") -> float:
        """
        Calcule un score de correspondance par nom/mot-clé (0-100)
        Basé sur la présence exacte de la compétence dans le titre et la description

        Args:
            competence: Nom de la compétence recherchée (ex: "Python", "Machine Learning")
            titre: Titre du cours
            description: Description du cours (optionnel)

        Returns:
            Score de 0 à 100 basé sur la correspondance exacte
        """
        score = 0.0
        comp_lower = competence.lower().strip()
        titre_lower = titre.lower() if titre else ""
        desc_lower = (description[:500].lower() if description else "") if description else ""

        # Mots de la compétence
        comp_words = comp_lower.split()

        # 1. Correspondance exacte complète dans le titre (score max: 100)
        if comp_lower == titre_lower:
            return 100.0

        # 2. Compétence complète présente dans le titre (score: 80-90)
        if comp_lower in titre_lower:
            # Bonus si c'est au début du titre
            if titre_lower.startswith(comp_lower):
                return 90.0
            return 80.0

        # 3. Tous les mots de la compétence dans le titre (score: 70)
        if all(word in titre_lower for word in comp_words if len(word) > 2):
            score = 70.0

        # 4. Au moins 50% des mots de la compétence dans le titre (score: 40-60)
        elif len(comp_words) > 1:
            mots_trouves = sum(1 for word in comp_words if len(word) > 2 and word in titre_lower)
            mots_significatifs = sum(1 for word in comp_words if len(word) > 2)
            if mots_significatifs > 0:
                ratio = mots_trouves / mots_significatifs
                if ratio >= 0.5:
                    score = 40.0 + (ratio * 20)  # 40-60 selon le ratio

        # 5. Compétence complète dans la description (bonus: +15)
        if comp_lower in desc_lower:
            score += 15.0
        elif all(word in desc_lower for word in comp_words if len(word) > 2):
            score += 10.0

        # 6. Au moins un mot significatif dans le titre (score minimal: 20)
        if score == 0.0:
            if any(word in titre_lower for word in comp_words if len(word) > 3):
                score = 20.0

        return min(score, 100.0)  # Cap à 100

    def _calculer_score_pertinence(self, competence: str, titre: str, description: str, categories: str, difficulty: str) -> float:
        """Calcule un score de pertinence basé sur plusieurs critères"""
        score = 0.0
        comp_lower = competence.lower()
        titre_lower = titre.lower() if titre else ""
        desc_lower = description.lower() if description else ""
        cat_lower = categories.lower() if categories else ""

        # Match exact dans le titre +50 points
        if comp_lower == titre_lower or comp_lower in titre_lower.split():
            score += 50
        elif comp_lower in titre_lower:
            score += 30
        elif any(word in titre_lower for word in comp_lower.split() if len(word) > 3):
            score += 15

        # Description contient la compétence +20 points
        if comp_lower in desc_lower:
            occurrences = min(desc_lower.count(comp_lower), 3)
            score += 20 * occurrences

        # Catégories +10 points
        if comp_lower in cat_lower:
            score += 10

        # Bonus difficulté
        if difficulty and difficulty.upper() == "INTERMEDIATE":
            score += 5
        elif difficulty and difficulty.upper() in ["ADVANCED", "BEGINNER"]:
            score += 3

        # Bonus mots-clés techniques
        tech_keywords = {
            'python': ['django', 'flask', 'pandas', 'numpy', 'tensorflow', 'pytorch'],
            'javascript': ['react', 'angular', 'vue', 'node', 'express'],
            'sql': ['database', 'query', 'postgresql', 'mysql', 'oracle'],
            'machine learning': ['ai', 'neural', 'deep learning', 'model', 'algorithm'],
            'data science': ['analysis', 'visualization', 'statistics', 'pandas', 'jupyter']
        }
        for key_comp, keywords in tech_keywords.items():
            if key_comp in comp_lower:
                bonus = sum(1 for kw in keywords if kw in desc_lower)
                score += min(bonus * 2, 10)

        return min(score, 100)

    def recommander_cours(self, competence: str, db_path: str = "course_scraper/coursera_fast.db", top_n: int = 3,
                         contexte_cv: str = "", niveau_declare: str = "", use_chromadb: bool = True) -> list:
        """
        Recommander des cours Coursera avec EMBEDDINGS SÉMANTIQUES + CONTEXTE CV

        OPTIMISÉ AVEC CHROMADB: Utilise un vector store persistant pour des recherches 10x plus rapides

        Args:
            competence: Compétence manquante (ex: "Python", "Machine Learning")
            db_path: Chemin vers la base de données Coursera
            top_n: Nombre de cours à recommander (défaut: 3)
            contexte_cv: Contexte professionnel du CV (ex: "Data Science", "Web Development")
            niveau_declare: Niveau déclaré dans le CV ("Débutant", "Intermédiaire", "Avancé", "Expert")
            use_chromadb: Utiliser ChromaDB (rapide) ou fallback SQLite (lent)

        Returns:
            Liste des top N cours recommandés avec scores de similarité sémantique
        """
        import sqlite3

        try:
            print(f"\n=== RECOMMANDATION SÉMANTIQUE POUR: {competence} ===")
            if contexte_cv:
                print(f"[INFO] Contexte CV: {contexte_cv}")
            if niveau_declare:
                print(f"[INFO] Niveau déclaré: {niveau_declare}")

            # NOUVEAU: Tenter d'utiliser ChromaDB si disponible et activé
            if use_chromadb:
                try:
                    from course_scraper.course_embedding_store import CourseEmbeddingStore

                    print(f"[INFO] Utilisation de ChromaDB (vector store optimisé)")

                    # Initialiser le store
                    store = CourseEmbeddingStore(
                        db_path=db_path,
                        chroma_path="course_scraper/chroma_db"
                    )

                    # Vérifier que des embeddings existent
                    if store.get_count() == 0:
                        print(f"[WARNING] ChromaDB vide, fallback sur méthode classique")
                        print(f"[INFO] Lancez: python course_scraper/migrate_embeddings_chromadb.py")
                        use_chromadb = False
                    else:
                        # Construire la requête enrichie avec le contexte
                        query_parts = [f"Learn {competence}"]

                        if contexte_cv:
                            query_parts.append(f"for {contexte_cv}")

                        query_parts.extend(["programming", "development", "course", "tutorial"])
                        query_text = " ".join(query_parts)

                        print(f"[INFO] Requête enrichie: '{query_text}'")

                        # Normaliser le niveau pour ChromaDB
                        niveau_filter = None
                        if niveau_declare:
                            import unicodedata
                            niveau_key = niveau_declare.lower()
                            niveau_key = unicodedata.normalize('NFD', niveau_key)
                            niveau_key = ''.join(c for c in niveau_key if unicodedata.category(c) != 'Mn')

                            niveau_mapping = {
                                'debutant': 'BEGINNER',
                                'intermediaire': 'INTERMEDIATE',
                                'avance': 'ADVANCED',
                                'expert': 'ADVANCED'
                            }

                            if niveau_key in niveau_mapping:
                                niveau_exact = niveau_mapping[niveau_key]
                                niveau_filter = {"difficulty": niveau_exact}
                                print(f"[INFO] Filtre de niveau: {niveau_exact}")

                        # Rechercher avec ChromaDB (recherche prioritaire au niveau exact)
                        n_results = top_n * 5  # Chercher plus pour avoir de la marge
                        print(f"[DEBUG] top_n={top_n}, n_results={n_results}")

                        if niveau_filter:
                            # ÉTAPE 1: Chercher d'abord au niveau exact
                            results_exact = store.search_similar_courses(
                                query=query_text,
                                n_results=n_results,
                                where=niveau_filter
                            )

                            print(f"[INFO] {len(results_exact)} cours trouvés au niveau exact")

                            # ÉTAPE 2: Si pas assez de résultats de qualité, élargir
                            if not results_exact or (results_exact and results_exact[0]['score_similarite'] < 60.0):
                                print(f"[INFO] Élargissement de la recherche (tous niveaux)")
                                results_all = store.search_similar_courses(
                                    query=query_text,
                                    n_results=n_results
                                )

                                # Marquer les cours du niveau exact
                                for course in results_exact:
                                    course['niveau_exact'] = True

                                # Combiner les résultats (éviter doublons)
                                seen_ids = {c['course_id'] for c in results_exact}
                                for course in results_all:
                                    if course['course_id'] not in seen_ids:
                                        course['niveau_exact'] = False
                                        results_exact.append(course)

                                results = results_exact
                            else:
                                results = results_exact
                                for course in results:
                                    course['niveau_exact'] = True
                        else:
                            # Pas de filtre de niveau
                            results = store.search_similar_courses(
                                query=query_text,
                                n_results=n_results
                            )
                            for course in results:
                                course['niveau_exact'] = False

                        # Formatter les résultats pour correspondre au format attendu
                        cours_avec_scores = []
                        for course in results:
                            cours_avec_scores.append({
                                'titre': course['title'],
                                'description': course['description'],
                                'url': course['url'],
                                'difficulte': course['difficulty'],
                                'duree': course['duration'],
                                'organisme': course['partner_name'],
                                'categories': course['categories'],
                                'score_similarite': course['score_similarite'],
                                'score_semantique': course['score_similarite'],
                                'score_nom': 0,  # ChromaDB ne calcule pas ce score séparément
                                'niveau_exact': course.get('niveau_exact', False)
                            })

                        # Trier avec priorité au niveau exact
                        def score_avec_priorite(cours):
                            score = cours['score_similarite']
                            if cours.get('niveau_exact', False):
                                score += 15  # Bonus pour niveau exact
                            return score

                        cours_avec_scores.sort(key=score_avec_priorite, reverse=True)

                        # Retourner top N
                        print(f"[DEBUG] Avant limitation: {len(cours_avec_scores)} cours")
                        print(f"[DEBUG] Limitation à top_n={top_n}")
                        top_cours = cours_avec_scores[:top_n]
                        print(f"[DEBUG] Après limitation: {len(top_cours)} cours")

                        print(f"[OK] Top {len(top_cours)} cours recommandés (ChromaDB):")
                        for i, cours in enumerate(top_cours, 1):
                            titre_safe = cours['titre'].encode('ascii', 'ignore').decode('ascii')
                            if not titre_safe:
                                titre_safe = cours['titre'][:50]
                            print(f"  {i}. {titre_safe}")
                            print(f"     Difficulté: {cours['difficulte']}")
                            print(f"     Score: {cours['score_similarite']}%")
                            if cours.get('niveau_exact'):
                                print(f"     [NIVEAU EXACT - Recommandé]")

                        return top_cours

                except ImportError:
                    print(f"[WARNING] ChromaDB non disponible, fallback sur méthode classique")
                    use_chromadb = False
                except Exception as e:
                    print(f"[WARNING] Erreur ChromaDB: {e}, fallback sur méthode classique")
                    import traceback
                    traceback.print_exc()
                    use_chromadb = False

            # FALLBACK: Méthode classique (génération embeddings à la volée)
            if not use_chromadb:
                print(f"[INFO] Utilisation de la méthode classique (SQLite + génération à la volée)")

            # 1. Générer l'embedding de la requête ENRICHIE avec le contexte
            # Si on a un contexte CV, l'ajouter pour affiner la recherche
            query_parts = [f"Learn {competence}"]

            if contexte_cv:
                query_parts.append(f"for {contexte_cv}")

            query_parts.extend(["programming", "development", "course", "tutorial"])

            query_text = " ".join(query_parts)
            print(f"[INFO] Requête enrichie: '{query_text}'")
            print(f"[INFO] Génération de l'embedding pour la requête...")
            query_embedding = self._generer_embedding_simple(query_text)

            # 2. Connexion BDD
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 3. Filtrage initial par mots-clés ET niveau (optimisation)
            keywords = competence.lower().split()
            conditions = []
            params = []

            for kw in keywords:
                if len(kw) > 2:
                    conditions.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
                    kw_pattern = f"%{kw}%"
                    params.extend([kw_pattern, kw_pattern])

            if not conditions:
                pattern = f"%{competence.lower()}%"
                conditions = ["(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)"]
                params = [pattern, pattern]

            # NOUVEAU: Filtrage intelligent par niveau (PRIORISATION)
            # Mapping: niveau déclaré → [niveau exact, niveaux inférieurs acceptables]
            # IMPORTANT: Clés sans accents pour compatibilité
            niveau_mapping_exact = {
                'debutant': 'BEGINNER',
                'intermediaire': 'INTERMEDIATE',
                'avance': 'ADVANCED',
                'expert': 'ADVANCED'  # Pas de niveau EXPERT en base, utilise ADVANCED
            }

            # Niveaux alternatifs (inférieurs ET supérieurs, pas le niveau exact déjà traité)
            niveau_mapping_fallback = {
                'debutant': ['INTERMEDIATE', 'ADVANCED'],  # Débutant → niveaux supérieurs
                'intermediaire': ['BEGINNER', 'ADVANCED'],  # Intermédiaire → inférieur + supérieur
                'avance': ['INTERMEDIATE'],  # Avancé → niveau inférieur (pas de supérieur)
                'expert': ['INTERMEDIATE']  # Expert → niveau inférieur (ADVANCED déjà traité)
            }

            # Stratégie: Chercher d'abord au niveau EXACT, puis élargir si nécessaire
            cours_avec_scores = []
            seuil_qualite = 60.0  # Score minimum pour considérer un cours de qualité

            if niveau_declare:
                # Normaliser le niveau (supprimer les accents pour la comparaison)
                import unicodedata
                niveau_key = niveau_declare.lower()
                niveau_key = unicodedata.normalize('NFD', niveau_key)
                niveau_key = ''.join(c for c in niveau_key if unicodedata.category(c) != 'Mn')

                if niveau_key in niveau_mapping_exact:
                    niveau_exact = niveau_mapping_exact[niveau_key]
                    print(f"[INFO] Stratégie: Recherche prioritaire au niveau '{niveau_exact}'")

                    # ÉTAPE 1: Chercher d'abord au niveau EXACT
                    params_exact = params.copy()
                    difficulty_filter = " AND difficulty = ?"
                    params_exact.append(niveau_exact)

                    query_exact = f"""
                        SELECT title, description, url, difficulty, duration, partner_name, categories
                        FROM courses
                        WHERE {' OR '.join(conditions)}{difficulty_filter}
                        LIMIT 150
                    """

                    cursor.execute(query_exact, params_exact)
                    results_exact = cursor.fetchall()

                    print(f"[INFO] {len(results_exact)} cours trouvés au niveau exact '{niveau_exact}'")

                    # Calculer les scores pour les cours du niveau exact
                    for row in results_exact:
                        titre, description, url, difficulty, duration, partner_name, categories = row

                        # 1. Score sémantique (TF-IDF + cosinus)
                        cours_text = f"{titre}. {description[:500] if description else ''}"
                        cours_embedding = self._generer_embedding_simple(cours_text)
                        similarite_semantique = self._similarite_cosinus(query_embedding, cours_embedding)
                        score_semantique = similarite_semantique * 100

                        # 2. Score de correspondance par nom
                        score_nom = self._calculer_score_nom(competence, titre, description)

                        # 3. Score hybride: 60% sémantique + 40% nom
                        score_hybride = (0.6 * score_semantique) + (0.4 * score_nom)

                        cours_avec_scores.append({
                            'titre': titre,
                            'description': (description[:300] + '...') if description and len(description) > 300 else (description or ""),
                            'url': url,
                            'difficulte': difficulty or 'Non spécifié',
                            'duree': duration or 'Non spécifié',
                            'organisme': partner_name or 'Coursera',
                            'categories': categories or '[]',
                            'score_similarite': round(score_hybride, 2),
                            'score_semantique': round(score_semantique, 2),
                            'score_nom': round(score_nom, 2),
                            'niveau_exact': True  # Marquer comme niveau exact
                        })

                    # Trier pour voir le meilleur score au niveau exact
                    cours_avec_scores.sort(key=lambda x: x['score_similarite'], reverse=True)

                    # ÉTAPE 2: Si meilleur score < seuil, chercher aussi niveaux inférieurs
                    meilleur_score_exact = cours_avec_scores[0]['score_similarite'] if cours_avec_scores else 0

                    if meilleur_score_exact < seuil_qualite:
                        print(f"[INFO] Meilleur score au niveau exact: {meilleur_score_exact}% < {seuil_qualite}%")

                        # Chercher dans les niveaux alternatifs (inférieurs ET supérieurs)
                        niveaux_acceptes = niveau_mapping_fallback[niveau_key]

                        if niveaux_acceptes:  # Seulement si des niveaux alternatifs existent
                            print(f"[INFO] Recherche élargie aux niveaux alternatifs: {niveaux_acceptes}")

                            params_fallback = params.copy()
                            placeholders = ','.join(['?' for _ in niveaux_acceptes])
                            difficulty_filter_fallback = f" AND difficulty IN ({placeholders})"
                            params_fallback.extend(niveaux_acceptes)

                            query_fallback = f"""
                                SELECT title, description, url, difficulty, duration, partner_name, categories
                                FROM courses
                                WHERE {' OR '.join(conditions)}{difficulty_filter_fallback}
                                LIMIT 150
                            """

                            cursor.execute(query_fallback, params_fallback)
                            results_fallback = cursor.fetchall()

                            print(f"[INFO] {len(results_fallback)} cours trouvés aux niveaux alternatifs")
                        else:
                            print(f"[INFO] Pas de niveau alternatif disponible pour '{niveau_declare}'")
                            results_fallback = []

                        # Calculer scores pour tous les cours (éviter doublons)
                        urls_existantes = {c['url'] for c in cours_avec_scores}

                        for row in results_fallback:
                            titre, description, url, difficulty, duration, partner_name, categories = row

                            if url in urls_existantes:
                                continue  # Éviter doublons

                            # 1. Score sémantique
                            cours_text = f"{titre}. {description[:500] if description else ''}"
                            cours_embedding = self._generer_embedding_simple(cours_text)
                            similarite_semantique = self._similarite_cosinus(query_embedding, cours_embedding)
                            score_semantique = similarite_semantique * 100

                            # 2. Score de correspondance par nom
                            score_nom = self._calculer_score_nom(competence, titre, description)

                            # 3. Score hybride: 60% sémantique + 40% nom
                            score_hybride = (0.6 * score_semantique) + (0.4 * score_nom)

                            cours_avec_scores.append({
                                'titre': titre,
                                'description': (description[:300] + '...') if description and len(description) > 300 else (description or ""),
                                'url': url,
                                'difficulte': difficulty or 'Non spécifié',
                                'duree': duration or 'Non spécifié',
                                'organisme': partner_name or 'Coursera',
                                'categories': categories or '[]',
                                'score_similarite': round(score_hybride, 2),
                                'score_semantique': round(score_semantique, 2),
                                'score_nom': round(score_nom, 2),
                                'niveau_exact': (difficulty == niveau_exact)
                            })
                    else:
                        print(f"[OK] Meilleur score au niveau exact: {meilleur_score_exact}% >= {seuil_qualite}%")
                else:
                    print(f"[WARNING] Niveau '{niveau_key}' non reconnu")
            else:
                # Pas de niveau déclaré: recherche sans filtre de difficulté
                print(f"[INFO] Aucun niveau déclaré: recherche tous niveaux")

                query = f"""
                    SELECT title, description, url, difficulty, duration, partner_name, categories
                    FROM courses
                    WHERE {' OR '.join(conditions)}
                    LIMIT 150
                """

                cursor.execute(query, params)
                results = cursor.fetchall()

                print(f"[INFO] {len(results)} cours candidats trouvés")

                for row in results:
                    titre, description, url, difficulty, duration, partner_name, categories = row

                    # 1. Score sémantique (TF-IDF + cosinus)
                    cours_text = f"{titre}. {description[:500] if description else ''}"
                    cours_embedding = self._generer_embedding_simple(cours_text)
                    similarite_semantique = self._similarite_cosinus(query_embedding, cours_embedding)
                    score_semantique = similarite_semantique * 100  # Convertir en pourcentage

                    # 2. Score de correspondance par nom (exact matching)
                    score_nom = self._calculer_score_nom(competence, titre, description)

                    # 3. Score hybride: 60% sémantique + 40% nom
                    score_hybride = (0.6 * score_semantique) + (0.4 * score_nom)

                    cours_avec_scores.append({
                        'titre': titre,
                        'description': (description[:300] + '...') if description and len(description) > 300 else (description or ""),
                        'url': url,
                        'difficulte': difficulty or 'Non spécifié',
                        'duree': duration or 'Non spécifié',
                        'organisme': partner_name or 'Coursera',
                        'categories': categories or '[]',
                        'score_similarite': round(score_hybride, 2),  # Score hybride final
                        'score_semantique': round(score_semantique, 2),
                        'score_nom': round(score_nom, 2),
                        'niveau_exact': False
                    })

            conn.close()

            if not cours_avec_scores:
                print(f"[WARNING] Aucun cours trouvé pour '{competence}'")
                return []

            # 5. Trier avec priorité au niveau exact (bonus de 15% au score)
            def score_avec_priorite(cours):
                score = cours['score_similarite']
                if cours.get('niveau_exact', False):
                    score += 15  # Bonus pour niveau exact (fort pour vraiment prioriser)
                return score

            cours_avec_scores.sort(key=score_avec_priorite, reverse=True)

            # 6. Retourner top N
            top_cours = cours_avec_scores[:top_n]

            print(f"[OK] Top {len(top_cours)} cours recommandes:")
            for i, cours in enumerate(top_cours, 1):
                # Nettoyage des caractères pour éviter les erreurs d'encodage
                titre_safe = cours['titre'].encode('ascii', 'ignore').decode('ascii')
                if not titre_safe:
                    titre_safe = cours['titre'][:50]  # Garder 50 premiers chars
                print(f"  {i}. {titre_safe}")
                print(f"     Difficulte: {cours['difficulte']}")
                print(f"     Score Hybride: {cours['score_similarite']}% (Semantique: {cours.get('score_semantique', 0)}% + Nom: {cours.get('score_nom', 0)}%)")
                if cours.get('niveau_exact'):
                    print(f"     [NIVEAU EXACT - Recommande]")

            return top_cours

        except Exception as e:
            print(f"[ERROR] Recommandation cours échouée: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def analyser_cv_avec_offre(self, cv_texte: str, offre_data: Dict) -> Dict:
        """
        Analyser la compatibilité CV avec une offre d'emploi
        """
        # Créer la description de l'offre
        offre_texte = f"""
TITRE: {offre_data.get('title', '')}
ENTREPRISE: {offre_data.get('company', '')}
LOCALISATION: {offre_data.get('location', '')}
TYPE: {offre_data.get('job_type', '')}
CONTRAT: {offre_data.get('contrat', '')}

DESCRIPTION:
{offre_data.get('description', '')}
"""
        
        prompt = f"""Tu es un expert en recrutement et systèmes ATS. Analyse la compatibilité entre ce CV et cette offre d'emploi.

OFFRE D'EMPLOI:
{offre_texte[:2000]}

CV DU CANDIDAT:
{cv_texte[:4000]}

Évalue et réponds en JSON avec cette structure EXACTE:
{{
  "score_global": <0-100>,
  "niveau_compatibilite": "<excellent|bon|moyen|faible>",
  
  "scores_details": {{
    "competences_techniques": <0-100>,
    "experience": <0-100>,
    "formation": <0-100>,
    "soft_skills": <0-100>
  }},
  
  "competences_matchees": [
    "liste des compétences du CV qui correspondent à l'offre"
  ],
  
  "competences_manquantes": [
    "compétences importantes demandées mais absentes du CV"
  ],
  
  "points_forts": [
    "3-4 atouts majeurs du candidat pour ce poste"
  ],
  
  "points_amelioration": [
    "2-3 points à améliorer ou développer"
  ],
  
  "experience_adequation": {{
    "niveau_requis": "<junior|intermediaire|senior|expert>",
    "niveau_candidat": "<junior|intermediaire|senior|expert>",
    "adequation": "<insuffisant|suffisant|optimal|surabondant>",
    "commentaire": "phrase d'explication"
  }},
  
  "recommandations": [
    "3-4 recommandations concrètes pour améliorer la candidature"
  ],
  
  "probabilite_entretien": "<très_faible|faible|moyenne|élevée|très_élevée>",
  
  "resume_executif": "Résumé en 2-3 phrases de l'adéquation candidat/poste",
  
  "mots_cles_ats": [
    "mots-clés importants trouvés dans le CV qui matchent l'offre"
  ],
  
  "mots_cles_manquants": [
    "mots-clés importants de l'offre absents du CV"
  ],
  
  "score_ats": <0-100>,
  "conseils_optimisation": [
    "conseils pour optimiser le CV pour les systèmes ATS"
  ],

  "template_recommande": {{
    "type": "<chronologique|fonctionnel|mixte|moderne|creatif|minimaliste|academique|technique>",
    "raison": "explication détaillée de pourquoi ce template convient parfaitement pour ce poste spécifique",
    "caracteristiques": [
      "liste détaillée des caractéristiques importantes du template recommandé (au moins 5-6)"
    ],
    "sections_prioritaires": [
      "sections à mettre en avant dans le CV pour ce poste avec explication pour chacune"
    ],
    "ordre_sections": [
      "ordre recommandé des sections du CV pour maximiser l'impact"
    ],
    "mise_en_page": {{
      "style": "<professionnel|moderne|classique|creatif|minimaliste|corporate>",
      "couleurs": "<sobre|coloré|monochrome|bleu_professionnel|tons_neutres>",
      "palette_suggeree": "description de la palette de couleurs recommandée",
      "format": "<1_colonne|2_colonnes|multicolonnes|hybride>",
      "police_suggeree": "recommandation de polices (titre et corps de texte)",
      "espacement": "<compact|aéré|équilibré>",
      "marges": "taille des marges recommandée"
    }},
    "elements_visuels": {{
      "photo": "<recommandée|optionnelle|déconseillée>",
      "icones": "<oui|non|modération>",
      "graphiques": "<compétences_en_barres|cercles_competences|aucun|timeline>",
      "en_tete": "description de l'en-tête idéal (coordonnées, titre professionnel, etc.)",
      "separateurs": "<lignes|espaces|couleurs|aucun>"
    }},
    "contenu_detaille": {{
      "titre_professionnel": "recommandation pour le titre/accroche professionnel",
      "resume_profil": "conseils pour rédiger le résumé/profil (longueur, style, contenu)",
      "experience": "comment présenter l'expérience (détails par poste, quantification, etc.)",
      "competences": "comment organiser les compétences (catégories, niveau, priorisation)",
      "formation": "comment présenter la formation pour ce type de poste",
      "projets": "<section_essentielle|recommandée|optionnelle|non_nécessaire> avec justification",
      "certifications": "importance et placement des certifications",
      "langues": "comment afficher les langues pour ce poste"
    }},
    "longueur_recommandee": "<1_page|2_pages|flexible> avec justification",
    "mots_cles_ats": {{
      "placement": "où placer les mots-clés importants pour l'ATS",
      "densite": "recommandation sur la fréquence des mots-clés",
      "sections_critiques": ["sections où l'ATS scanne le plus"]
    }},
    "erreurs_a_eviter": [
      "liste des erreurs spécifiques à éviter pour ce type de poste"
    ],
    "conseils_specifiques": [
      "3-5 conseils très spécifiques et actionnables pour ce template et ce poste"
    ],
    "exemples_formulation": {{
      "titre_profil": "exemple de titre professionnel adapté",
      "accroche": "exemple d'accroche percutante pour ce poste",
      "bullet_point_experience": "exemple de bullet point bien formulé"
    }}
  }}
}}

Sois précis, objectif et constructif dans ton analyse."""

        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                resultat = json.loads(data['choices'][0]['message']['content'])
                resultat['tokens_utilises'] = data.get('usage', {}).get('total_tokens', 0)
                resultat['offre_info'] = {
                    'titre': offre_data.get('title', ''),
                    'entreprise': offre_data.get('company', ''),
                    'localisation': offre_data.get('location', '')
                }

                # Les recommandations de cours ne sont plus générées automatiquement
                # Elles sont générées uniquement quand l'utilisateur clique sur le bouton
                # via l'endpoint /api/recommend-courses

                return resultat
            else:
                return {'erreur': f'Erreur API: {response.status_code}'}
        
        except Exception as e:
            return {'erreur': str(e)}
    
    def generer_rapport_html(self, analyse: Dict) -> str:
        """Générer un rapport HTML de l'analyse"""
        if 'erreur' in analyse:
            return f"<div class='alert alert-danger'>Erreur: {analyse['erreur']}</div>"
        
        score = analyse.get('score_global', 0)
        niveau = analyse.get('niveau_compatibilite', 'moyen')
        
        # Couleur selon le score
        if score >= 80:
            color_class = 'success'
            icon = 'fas fa-check-circle'
        elif score >= 60:
            color_class = 'warning'
            icon = 'fas fa-exclamation-triangle'
        else:
            color_class = 'danger'
            icon = 'fas fa-times-circle'
        
        html = f"""
        <div class="ats-analysis-report">
            <!-- Score global -->
            <div class="text-center mb-4">
                <div class="score-circle bg-{color_class} text-white rounded-circle d-inline-flex align-items-center justify-content-center" 
                     style="width: 120px; height: 120px;">
                    <div>
                        <div class="h2 mb-0">{score}%</div>
                        <small>Compatibilité</small>
                    </div>
                </div>
                <h4 class="mt-3 text-{color_class}">
                    <i class="{icon} me-2"></i>
                    Niveau: {niveau.upper()}
                </h4>
                <p class="lead">{analyse.get('resume_executif', '')}</p>
            </div>
            
            <!-- Scores détaillés -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title">Compétences</h5>
                            <div class="h4 text-primary">{analyse.get('scores_details', {}).get('competences_techniques', 0)}%</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title">Expérience</h5>
                            <div class="h4 text-info">{analyse.get('scores_details', {}).get('experience', 0)}%</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title">Formation</h5>
                            <div class="h4 text-success">{analyse.get('scores_details', {}).get('formation', 0)}%</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="card-title">Soft Skills</h5>
                            <div class="h4 text-warning">{analyse.get('scores_details', {}).get('soft_skills', 0)}%</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Points forts et à améliorer -->
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header bg-success text-white">
                            <h6 class="mb-0"><i class="fas fa-thumbs-up me-2"></i>Points forts</h6>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
        """
        
        for point in analyse.get('points_forts', []):
            html += f"<li class='mb-2'><i class='fas fa-check text-success me-2'></i>{point}</li>"
        
        html += """
                            </ul>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header bg-warning text-white">
                            <h6 class="mb-0"><i class="fas fa-lightbulb me-2"></i>À améliorer</h6>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
        """
        
        for point in analyse.get('points_amelioration', []):
            html += f"<li class='mb-2'><i class='fas fa-arrow-up text-warning me-2'></i>{point}</li>"
        
        html += """
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Compétences -->
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h6 class="mb-0"><i class="fas fa-check-double me-2"></i>Compétences matchées</h6>
                        </div>
                        <div class="card-body">
        """
        
        for comp in analyse.get('competences_matchees', []):
            html += f"<span class='badge bg-primary me-2 mb-2'>{comp}</span>"
        
        html += """
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-danger text-white">
                            <h6 class="mb-0"><i class="fas fa-times me-2"></i>Compétences manquantes</h6>
                        </div>
                        <div class="card-body">
        """
        
        for comp in analyse.get('competences_manquantes', []):
            html += f"<span class='badge bg-danger me-2 mb-2'>{comp}</span>"

        html += f"""
                        </div>
                    </div>
                </div>
            </div>
        """

        # Section des formations recommandées (Coursera)
        formations = analyse.get('formations_recommandees', {})
        if formations:
            html += """
            <!-- Formations Recommandées Coursera -->
            <div class="card mb-4 border-warning">
                <div class="card-header text-white" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <h5 class="mb-0">
                        <i class="fas fa-graduation-cap me-2"></i>
                        Formations Recommandées pour Combler les Compétences Manquantes
                    </h5>
                </div>
                <div class="card-body">
                    <p class="text-muted mb-4">
                        <i class="fas fa-info-circle me-2"></i>
                        Nous avons sélectionné pour vous les meilleurs cours Coursera pour développer les compétences manquantes identifiées.
                    </p>
        """

            for competence, cours_list in formations.items():
                if cours_list:
                    html += f"""
                    <div class="mb-4">
                        <h6 class="text-primary border-bottom pb-2">
                            <i class="fas fa-book me-2"></i>
                            Formation en <strong>{competence}</strong>
                        </h6>
                        <div class="row">
        """

                    for cours in cours_list:
                        difficulte_badge = {
                            'BEGINNER': 'success',
                            'INTERMEDIATE': 'primary',
                            'ADVANCED': 'warning',
                            'EXPERT': 'danger'
                        }.get(cours.get('difficulte', 'INTERMEDIATE').upper(), 'secondary')

                        html += f"""
                            <div class="col-md-12 mb-3">
                                <div class="card h-100 shadow-sm">
                                    <div class="card-body">
                                        <h6 class="card-title">
                                            <a href="{cours.get('url', '#')}" target="_blank" class="text-decoration-none">
                                                {cours.get('titre', 'Cours sans titre')}
                                                <i class="fas fa-external-link-alt ms-1 small"></i>
                                            </a>
                                        </h6>
                                        <p class="card-text small text-muted">
                                            {cours.get('description', 'Aucune description disponible')}
                                        </p>
                                        <div class="d-flex flex-wrap gap-2 align-items-center">
                                            <span class="badge bg-{difficulte_badge}">
                                                <i class="fas fa-signal me-1"></i>{cours.get('difficulte', 'N/A')}
                                            </span>
                                            <span class="badge bg-info">
                                                <i class="fas fa-clock me-1"></i>{cours.get('duree', 'N/A')}
                                            </span>
                                            <span class="badge bg-secondary">
                                                <i class="fas fa-university me-1"></i>{cours.get('organisme', 'Coursera')}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="card-footer bg-light">
                                        <a href="{cours.get('url', '#')}" target="_blank" class="btn btn-sm btn-primary w-100">
                                            <i class="fas fa-arrow-right me-2"></i>Accéder au cours
                                        </a>
                                    </div>
                                </div>
                            </div>
        """

                    html += """
                        </div>
                    </div>
        """

            html += """
                </div>
            </div>
        """

        html += """

            <!-- Recommandations -->
            <div class="card mb-4">
                <div class="card-header bg-info text-white">
                    <h6 class="mb-0"><i class="fas fa-lightbulb me-2"></i>Recommandations</h6>
                </div>
                <div class="card-body">
                    <ol>
        """
        
        for rec in analyse.get('recommandations', []):
            html += f"<li class='mb-2'>{rec}</li>"
        
        probabilite = analyse.get('probabilite_entretien', 'moyenne')
        prob_class = {
            'très_élevée': 'success',
            'élevée': 'success', 
            'moyenne': 'warning',
            'faible': 'danger',
            'très_faible': 'danger'
        }.get(probabilite, 'warning')
        
        html += f"""
                    </ol>
                </div>
            </div>
            
            <!-- Probabilité entretien -->
            <div class="card mb-4">
                <div class="card-header bg-{prob_class} text-white">
                    <h6 class="mb-0"><i class="fas fa-chart-line me-2"></i>Probabilité d'entretien</h6>
                </div>
                <div class="card-body text-center">
                    <h4 class="text-{prob_class}">{probabilite.replace('_', ' ').title()}</h4>
                    <p class="text-muted">Score ATS: {analyse.get('score_ats', 0)}%</p>
                </div>
            </div>
        """

        # Ajouter la section template recommandé avec tous les détails
        template_info = analyse.get('template_recommande', {})
        if template_info:
            html += f"""
            <!-- Template de CV recommandé -->
            <div class="card mb-4 border-primary">
                <div class="card-header text-white" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                    <h5 class="mb-0"><i class="fas fa-file-contract me-2"></i>Guide Complet du Template de CV Recommandé</h5>
                </div>
                <div class="card-body">
                    <!-- Type et raison -->
                    <div class="row mb-4">
                        <div class="col-md-12">
                            <div class="alert alert-primary" role="alert">
                                <h4 class="alert-heading">
                                    <i class="fas fa-star me-2"></i>
                                    Type recommandé: <strong>{template_info.get('type', 'N/A').upper()}</strong>
                                </h4>
                                <hr>
                                <p class="mb-0"><strong>Pourquoi ce template ?</strong> {template_info.get('raison', '')}</p>
                            </div>
                        </div>
                    </div>

                    <!-- Longueur recommandée -->
                    <div class="row mb-3">
                        <div class="col-md-12">
                            <div class="alert alert-info">
                                <strong><i class="fas fa-ruler-combined me-2"></i>Longueur recommandée:</strong>
                                {template_info.get('longueur_recommandee', 'N/A')}
                            </div>
                        </div>
                    </div>

                    <!-- Caractéristiques et Sections prioritaires -->
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <div class="card border-success h-100">
                                <div class="card-header bg-success text-white">
                                    <h6 class="mb-0"><i class="fas fa-list-check me-2"></i>Caractéristiques du Template</h6>
                                </div>
                                <div class="card-body">
                                    <ul class="list-group list-group-flush">
        """

            for carac in template_info.get('caracteristiques', []):
                html += f'<li class="list-group-item"><i class="fas fa-check-circle text-success me-2"></i>{carac}</li>'

            html += """
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card border-primary h-100">
                                <div class="card-header bg-primary text-white">
                                    <h6 class="mb-0"><i class="fas fa-layer-group me-2"></i>Sections Prioritaires</h6>
                                </div>
                                <div class="card-body">
                                    <ul class="list-group list-group-flush">
        """

            for section in template_info.get('sections_prioritaires', []):
                html += f'<li class="list-group-item"><i class="fas fa-arrow-right text-primary me-2"></i>{section}</li>'

            html += """
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Ordre des sections -->
        """

            ordre_sections = template_info.get('ordre_sections', [])
            if ordre_sections:
                html += """
                    <div class="row mb-4">
                        <div class="col-md-12">
                            <div class="card border-warning">
                                <div class="card-header bg-warning">
                                    <h6 class="mb-0"><i class="fas fa-sort-numeric-down me-2"></i>Ordre Recommandé des Sections</h6>
                                </div>
                                <div class="card-body">
                                    <ol class="mb-0">
        """
                for idx, section in enumerate(ordre_sections, 1):
                    html += f'<li class="mb-2"><strong>{idx}.</strong> {section}</li>'

                html += """
                                    </ol>
                                </div>
                            </div>
                        </div>
                    </div>
        """

            # Mise en page détaillée
            mise_en_page = template_info.get('mise_en_page', {})
            html += f"""
                    <!-- Mise en page -->
                    <div class="row mb-4">
                        <div class="col-md-12">
                            <div class="card border-info">
                                <div class="card-header bg-info text-white">
                                    <h6 class="mb-0"><i class="fas fa-palette me-2"></i>Mise en Page Détaillée</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <ul class="list-unstyled">
                                                <li class="mb-2"><strong><i class="fas fa-paint-brush me-2"></i>Style:</strong> {mise_en_page.get('style', 'N/A')}</li>
                                                <li class="mb-2"><strong><i class="fas fa-fill-drip me-2"></i>Couleurs:</strong> {mise_en_page.get('couleurs', 'N/A')}</li>
                                                <li class="mb-2"><strong><i class="fas fa-palette me-2"></i>Palette:</strong> {mise_en_page.get('palette_suggeree', 'N/A')}</li>
                                                <li class="mb-2"><strong><i class="fas fa-columns me-2"></i>Format:</strong> {mise_en_page.get('format', 'N/A')}</li>
                                            </ul>
                                        </div>
                                        <div class="col-md-6">
                                            <ul class="list-unstyled">
                                                <li class="mb-2"><strong><i class="fas fa-font me-2"></i>Police:</strong> {mise_en_page.get('police_suggeree', 'N/A')}</li>
                                                <li class="mb-2"><strong><i class="fas fa-arrows-alt-v me-2"></i>Espacement:</strong> {mise_en_page.get('espacement', 'N/A')}</li>
                                                <li class="mb-2"><strong><i class="fas fa-expand me-2"></i>Marges:</strong> {mise_en_page.get('marges', 'N/A')}</li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Éléments visuels -->
        """

            elements_visuels = template_info.get('elements_visuels', {})
            if elements_visuels:
                html += f"""
                    <div class="row mb-4">
                        <div class="col-md-12">
                            <div class="card border-secondary">
                                <div class="card-header bg-secondary text-white">
                                    <h6 class="mb-0"><i class="fas fa-icons me-2"></i>Éléments Visuels</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <ul class="list-unstyled">
                                                <li class="mb-2"><strong><i class="fas fa-user-circle me-2"></i>Photo:</strong> {elements_visuels.get('photo', 'N/A')}</li>
                                                <li class="mb-2"><strong><i class="fas fa-icons me-2"></i>Icônes:</strong> {elements_visuels.get('icones', 'N/A')}</li>
                                                <li class="mb-2"><strong><i class="fas fa-chart-bar me-2"></i>Graphiques:</strong> {elements_visuels.get('graphiques', 'N/A')}</li>
                                            </ul>
                                        </div>
                                        <div class="col-md-6">
                                            <p class="mb-2"><strong><i class="fas fa-heading me-2"></i>En-tête idéal:</strong></p>
                                            <p class="text-muted small">{elements_visuels.get('en_tete', 'N/A')}</p>
                                            <p class="mb-0"><strong><i class="fas fa-minus me-2"></i>Séparateurs:</strong> {elements_visuels.get('separateurs', 'N/A')}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
        """

            # Contenu détaillé
            contenu = template_info.get('contenu_detaille', {})
            if contenu:
                html += """
                    <div class="row mb-4">
                        <div class="col-md-12">
                            <div class="card border-dark">
                                <div class="card-header bg-dark text-white">
                                    <h6 class="mb-0"><i class="fas fa-file-lines me-2"></i>Guide de Contenu Détaillé</h6>
                                </div>
                                <div class="card-body">
        """

                contenu_items = [
                    ('heading', 'Titre Professionnel', contenu.get('titre_professionnel')),
                    ('user', 'Résumé/Profil', contenu.get('resume_profil')),
                    ('briefcase', 'Expérience', contenu.get('experience')),
                    ('tools', 'Compétences', contenu.get('competences')),
                    ('graduation-cap', 'Formation', contenu.get('formation')),
                    ('project-diagram', 'Projets', contenu.get('projets')),
                    ('certificate', 'Certifications', contenu.get('certifications')),
                    ('language', 'Langues', contenu.get('langues'))
                ]

                for icon, label, value in contenu_items:
                    if value:
                        html += f"""
                                    <div class="mb-3">
                                        <h6 class="text-primary"><i class="fas fa-{icon} me-2"></i>{label}</h6>
                                        <p class="ms-4 text-muted">{value}</p>
                                    </div>
        """

                html += """
                                </div>
                            </div>
                        </div>
                    </div>
        """

            # Optimisation ATS
            mots_cles_ats = template_info.get('mots_cles_ats', {})
            if mots_cles_ats:
                html += f"""
                    <div class="row mb-4">
                        <div class="col-md-12">
                            <div class="card border-success">
                                <div class="card-header bg-success text-white">
                                    <h6 class="mb-0"><i class="fas fa-robot me-2"></i>Optimisation ATS (Mots-clés)</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-4">
                                            <p><strong><i class="fas fa-map-marker-alt me-2"></i>Placement:</strong></p>
                                            <p class="text-muted small">{mots_cles_ats.get('placement', 'N/A')}</p>
                                        </div>
                                        <div class="col-md-4">
                                            <p><strong><i class="fas fa-percentage me-2"></i>Densité:</strong></p>
                                            <p class="text-muted small">{mots_cles_ats.get('densite', 'N/A')}</p>
                                        </div>
                                        <div class="col-md-4">
                                            <p><strong><i class="fas fa-crosshairs me-2"></i>Sections critiques:</strong></p>
                                            <ul class="small text-muted">
        """

                for section in mots_cles_ats.get('sections_critiques', []):
                    html += f'<li>{section}</li>'

                html += """
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
        """

            # Exemples de formulation
            exemples = template_info.get('exemples_formulation', {})
            if exemples:
                html += """
                    <div class="row mb-4">
                        <div class="col-md-12">
                            <div class="card border-primary">
                                <div class="card-header bg-primary text-white">
                                    <h6 class="mb-0"><i class="fas fa-lightbulb me-2"></i>Exemples de Formulation</h6>
                                </div>
                                <div class="card-body">
        """

                if exemples.get('titre_profil'):
                    html += f"""
                                    <div class="mb-3">
                                        <strong><i class="fas fa-tag me-2"></i>Titre Professionnel:</strong>
                                        <div class="alert alert-light mt-2">
                                            <code>{exemples.get('titre_profil')}</code>
                                        </div>
                                    </div>
        """

                if exemples.get('accroche'):
                    html += f"""
                                    <div class="mb-3">
                                        <strong><i class="fas fa-quote-left me-2"></i>Accroche:</strong>
                                        <div class="alert alert-light mt-2">
                                            <em>"{exemples.get('accroche')}"</em>
                                        </div>
                                    </div>
        """

                if exemples.get('bullet_point_experience'):
                    html += f"""
                                    <div class="mb-3">
                                        <strong><i class="fas fa-circle me-2"></i>Bullet Point Expérience:</strong>
                                        <div class="alert alert-light mt-2">
                                            • {exemples.get('bullet_point_experience')}
                                        </div>
                                    </div>
        """

                html += """
                                </div>
                            </div>
                        </div>
                    </div>
        """

            # Erreurs à éviter et conseils
            html += """
                    <div class="row mb-4">
        """

            erreurs = template_info.get('erreurs_a_eviter', [])
            if erreurs:
                html += """
                        <div class="col-md-6">
                            <div class="card border-danger h-100">
                                <div class="card-header bg-danger text-white">
                                    <h6 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>Erreurs à Éviter</h6>
                                </div>
                                <div class="card-body">
                                    <ul class="list-group list-group-flush">
        """
                for erreur in erreurs:
                    html += f'<li class="list-group-item text-danger"><i class="fas fa-times-circle me-2"></i>{erreur}</li>'

                html += """
                                    </ul>
                                </div>
                            </div>
                        </div>
        """

            conseils = template_info.get('conseils_specifiques', [])
            if conseils:
                html += """
                        <div class="col-md-6">
                            <div class="card border-success h-100">
                                <div class="card-header bg-success text-white">
                                    <h6 class="mb-0"><i class="fas fa-check-double me-2"></i>Conseils Spécifiques</h6>
                                </div>
                                <div class="card-body">
                                    <ul class="list-group list-group-flush">
        """
                for conseil in conseils:
                    html += f'<li class="list-group-item text-success"><i class="fas fa-star me-2"></i>{conseil}</li>'

                html += """
                                    </ul>
                                </div>
                            </div>
                        </div>
        """

            html += """
                    </div>
                </div>
            </div>
        </div>
        """

        return html

    def extraire_certificats_attestations(self, cv_texte: str) -> Dict:
        """Extraire tous les certificats et attestations déclarés dans le CV"""
        prompt = f"""Tu es un expert en analyse de CV. Extrait UNIQUEMENT les certificats, attestations, diplômes et certifications déclarés dans ce CV.

CV DU CANDIDAT:
{cv_texte}

IMPORTANT:
- Extrait SEULEMENT les éléments concrets mentionnés (certificats, attestations, diplômes, certifications)
- Ne déduis rien, ne suppose rien
- Pour chaque élément, extrais: nom exact, organisme émetteur, date/année si disponible
- Classe par catégories: Diplômes, Certifications professionnelles, Formations certifiantes, Attestations
- Ajoute un ID unique pour chaque document pour le tracking

Réponds en JSON avec cette structure EXACTE:
{{
  "diplomes": [
    {{
      "id": "DIP_001",
      "nom": "nom exact du diplôme",
      "organisme": "établissement émetteur",
      "date": "année ou date si disponible",
      "niveau": "licence|master|doctorat|autre",
      "statut_verification": "non_verifie"
    }}
  ],
  "certifications_professionnelles": [
    {{
      "id": "CERT_001",
      "nom": "nom exact de la certification",
      "organisme": "organisme certificateur",
      "date": "année ou date si disponible",
      "domaine": "domaine de la certification",
      "statut_verification": "non_verifie"
    }}
  ],
  "formations_certifiantes": [
    {{
      "id": "FORM_001",
      "nom": "nom de la formation",
      "organisme": "organisme de formation",
      "date": "année ou date si disponible",
      "duree": "durée si mentionnée",
      "statut_verification": "non_verifie"
    }}
  ],
  "attestations": [
    {{
      "id": "ATT_001",
      "nom": "nom de l'attestation",
      "organisme": "organisme émetteur",
      "date": "année ou date si disponible",
      "type": "type d'attestation",
      "statut_verification": "non_verifie"
    }}
  ],
  "langues_certifiees": [
    {{
      "id": "LANG_001",
      "langue": "langue",
      "certification": "nom du certificat (TOEFL, DELF, etc.)",
      "niveau": "niveau obtenu",
      "date": "année si disponible",
      "statut_verification": "non_verifie"
    }}
  ],
  "total_claims": "nombre total d'éléments extraits",
  "resume": "résumé en 1 phrase des qualifications principales"
}}

Sois précis et extrait SEULEMENT ce qui est explicitement mentionné."""

        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                timeout=30
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']

                # Extraire le JSON
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                resultat = json.loads(content.strip())
                return resultat
            else:
                return {'erreur': f'Erreur API: {response.status_code}'}

        except Exception as e:
            return {'erreur': str(e)}

    def pdf_to_image(self, pdf_path: str) -> str:
        """Convertir la première page d'un PDF en image avec PyMuPDF"""
        try:
            import fitz  # PyMuPDF
            import tempfile

            print(f"Conversion PDF vers image: {pdf_path}")

            # Ouvrir le PDF
            pdf_document = fitz.open(pdf_path)

            if pdf_document.page_count == 0:
                print("ERREUR: PDF vide, aucune page")
                return None

            # Convertir la première page en image
            page = pdf_document[0]

            # Rendre la page en pixmap (image)
            zoom = 2.0  # Zoom pour meilleure qualité
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Sauvegarder temporairement
            temp_dir = tempfile.gettempdir()
            image_path = os.path.join(temp_dir, f"pdf_page_{os.getpid()}.png")
            pix.save(image_path)

            pdf_document.close()

            print(f"[OK] PDF converti en image: {image_path} (taille: {pix.width}x{pix.height})")
            return image_path

        except ImportError:
            print("ERREUR: PyMuPDF non installé. Installez: pip install pymupdf")
            return None
        except Exception as e:
            print(f"Erreur conversion PDF: {e}")
            import traceback
            traceback.print_exc()
            return None

    def image_to_base64(self, image_path: str) -> str:
        """Convertir une image en base64"""
        try:
            import base64

            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
                base64_str = base64.b64encode(img_data).decode('utf-8')

            print(f"[OK] Image encodée en base64: {len(base64_str)} caractères")
            return base64_str

        except Exception as e:
            print(f"Erreur encodage base64: {e}")
            return None

    def verifier_document_vlm(self, claim: dict, file_path: str, category: str) -> Dict:
        """
        Vérification avec VLM (Vision Language Model)
        Accepte PDF ou images, convertit tout en image, envoie au VLM
        """
        print(f"\n=== VERIFICATION VLM ===")
        print(f"Claim: {claim.get('nom', 'N/A')}")
        print(f"File: {file_path}")

        # Déterminer le type de fichier
        extension = file_path.rsplit('.', 1)[1].lower()

        # Convertir en image si nécessaire
        if extension == 'pdf':
            image_path = self.pdf_to_image(file_path)
            if not image_path:
                return {'erreur': 'Impossible de convertir le PDF en image'}
        else:
            image_path = file_path

        # Convertir l'image en base64
        base64_image = self.image_to_base64(image_path)
        if not base64_image:
            return {'erreur': 'Impossible d\'encoder l\'image'}

        # Nettoyer l'image temporaire si c'était un PDF
        if extension == 'pdf' and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass

        # Créer le prompt pour le VLM
        nom_declare = claim.get('nom', '')
        organisme_declare = claim.get('organisme', '')

        prompt = f"""Analyse ce document et vérifie s'il correspond à la certification déclarée.

CERTIFICATION DÉCLARÉE:
- Nom: {nom_declare}
- Organisme: {organisme_declare}

INSTRUCTIONS:
1. Lis attentivement le document
2. Vérifie si le nom de la certification correspond
3. Vérifie si l'organisme correspond
4. Donne un statut: "confirmé" ou "non_confirmé"

Réponds en JSON:
{{
  "nom_trouve": true|false,
  "organisme_trouve": true|false,
  "statut": "confirmé|non_confirmé",
  "score_confiance": <0-100>,
  "commentaire": "explication courte"
}}"""

        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=60
            )

            print(f"VLM Response status: {response.status_code}")

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                print(f"VLM Response: {content[:200]}...")

                # Extraire le JSON
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                content = content.strip()
                resultat = json.loads(content)

                resultat['claim_id'] = claim.get('id', 'N/A')
                resultat['category'] = category
                resultat['verification_method'] = 'VLM'

                print(f"[OK] Vérification terminée: {resultat.get('statut', 'unknown')}")
                return resultat
            else:
                error_text = response.text
                print(f"ERROR: API status {response.status_code} - {error_text}")
                return {'erreur': f'Erreur API: {response.status_code}'}

        except Exception as e:
            print(f"EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'erreur': str(e)}

    def verifier_document_simple(self, claim: dict, proof_text: str, category: str) -> Dict:
        """
        Vérification SIMPLE : vérifie juste si le nom du certificat correspond
        """
        print(f"\n=== VERIFICATION SIMPLE ===")
        print(f"Claim nom: {claim.get('nom', 'N/A')}")
        print(f"Proof text length: {len(proof_text)} chars")

        nom_declare = claim.get('nom', '')
        organisme_declare = claim.get('organisme', '')

        prompt = f"""Vérifie si ce document correspond à la certification déclarée.

CERTIFICATION DÉCLARÉE:
Nom: {nom_declare}
Organisme: {organisme_declare}

TEXTE DU DOCUMENT:
{proof_text[:2000]}

Réponds en JSON:
{{
  "nom_trouve": true|false,
  "organisme_trouve": true|false,
  "statut": "confirmé|non_confirmé",
  "score_confiance": <0-100>,
  "commentaire": "explication courte"
}}"""

        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                resultat = json.loads(content.strip())
                resultat['claim_id'] = claim.get('id', 'N/A')
                resultat['category'] = category
                print(f"[OK] Vérification terminée: {resultat.get('statut', 'unknown')}")
                return resultat
            else:
                print(f"ERROR: API status {response.status_code}")
                return {'erreur': f'Erreur API: {response.status_code}'}

        except Exception as e:
            print(f"EXCEPTION: {str(e)}")
            return {'erreur': str(e)}

    def verifier_document_unique(self, claim: dict, proof_text: str, category: str) -> Dict:
        """
        Vérifier UN SEUL document à la fois par rapport au claim déclaré dans le CV
        Utilise le LLM pour analyser si le document prouve bien ce qui est déclaré
        """
        print(f"\n=== VERIFICATION DOCUMENT UNIQUE ===")
        print(f"Catégorie: {category}")
        print(f"Claim ID: {claim.get('id', 'N/A')}")
        print(f"Document: {claim.get('nom', 'N/A')}")

        # Déterminer le type de document pour adapter l'analyse
        type_document = self._determiner_type_document(category, claim)

        prompt = f"""Tu es un expert en vérification de documents académiques et professionnels.

MISSION: Vérifier si le document fourni PROUVE le claim déclaré dans le CV.

TYPE DE DOCUMENT: {type_document}

CLAIM DÉCLARÉ DANS LE CV:
Catégorie: {category}
Nom: {claim.get('nom', 'N/A')}
Organisme: {claim.get('organisme', 'N/A')}
Date: {claim.get('date', 'N/A')}
{self._formater_details_claim(claim, category)}

TEXTE EXTRAIT DU DOCUMENT FOURNI:
{proof_text[:3000]}

CONSIGNES D'ANALYSE:
1. Vérifie si le document est du bon type ({type_document})
2. Vérifie si le nom du diplôme/certification correspond
3. Vérifie si l'organisme émetteur correspond
4. Vérifie si la date est cohérente (±1 an acceptable)
5. Vérifie l'authenticité apparente (format, signature, cachet mentionné, etc.)
6. Détecte toute incohérence ou divergence

Réponds en JSON avec cette structure EXACTE:
{{
  "statut": "confirme|partiellement_confirme|non_confirme|document_invalide",
  "score_confiance": <0-100>,
  "type_document_detecte": "type détecté dans le document fourni",
  "correspondance_type": true|false,
  "elements_verifies": {{
    "nom_diplome": {{
      "declare": "ce qui est déclaré",
      "trouve": "ce qui est trouvé",
      "correspondance": true|false,
      "score": <0-100>
    }},
    "organisme": {{
      "declare": "organisme déclaré",
      "trouve": "organisme trouvé",
      "correspondance": true|false,
      "score": <0-100>
    }},
    "date": {{
      "declare": "date déclarée",
      "trouve": "date trouvée",
      "correspondance": true|false,
      "ecart_jours": <nombre ou null>
    }},
    "authenticite_apparente": {{
      "indices_authenticite": ["liste des indices trouvés: signature, cachet, format officiel, etc."],
      "score": <0-100>
    }}
  }},
  "divergences": [
    "Liste détaillée de TOUTES les différences entre claim et document"
  ],
  "elements_manquants": [
    "Éléments déclarés mais non trouvés dans le document"
  ],
  "elements_supplementaires": [
    "Informations dans le document mais non déclarées dans le CV"
  ],
  "drapeaux_rouges": [
    "Tout élément suspect ou problématique (dates incohérentes, format inhabituel, etc.)"
  ],
  "analyse_detaillee": "Analyse complète en 3-5 phrases",
  "recommandation": "accepter|demander_clarification|rejeter",
  "raison_recommandation": "Justification de la recommandation"
}}

Sois TRÈS RIGOUREUX et OBJECTIF. En cas de doute, indique-le clairement."""

        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Tu es un expert en vérification de documents. Tu DOIS répondre UNIQUEMENT en JSON valide, sans texte additionnel."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,  # Très basse pour être factuel
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"}  # Forcer JSON
                },
                timeout=45
            )

            print(f"API Response status: {response.status_code}")

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                print(f"Raw response (first 200 chars): {content[:200]}")

                # Extraire le JSON si entouré de markdown
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                content = content.strip()
                if not content:
                    print("ERROR: Empty content after extraction")
                    return {'erreur': 'Réponse vide de l\'API'}

                resultat = json.loads(content)

                # Ajouter des métadonnées
                resultat['claim_id'] = claim.get('id', 'N/A')
                resultat['category'] = category
                resultat['timestamp'] = json.dumps({'verified_at': 'timestamp'})

                print(f"[OK] Vérification terminée: {resultat.get('statut', 'unknown')}")
                return resultat
            else:
                error_msg = f'Erreur API: {response.status_code}'
                print(f"ERROR: {error_msg}")
                return {'erreur': error_msg}

        except Exception as e:
            error_msg = str(e)
            print(f"EXCEPTION: {error_msg}")
            return {'erreur': error_msg}

    def _determiner_type_document(self, category: str, claim: dict) -> str:
        """Déterminer le type de document attendu"""
        types_mapping = {
            'diplomes': 'Diplôme universitaire',
            'certifications_professionnelles': 'Certificat professionnel',
            'formations_certifiantes': 'Attestation de formation',
            'attestations': 'Attestation',
            'langues_certifiees': 'Certificat de langue'
        }
        return types_mapping.get(category, 'Document académique ou professionnel')

    def _formater_details_claim(self, claim: dict, category: str) -> str:
        """Formater les détails spécifiques selon la catégorie"""
        details = []

        if category == 'diplomes':
            if 'niveau' in claim:
                details.append(f"Niveau: {claim['niveau']}")
        elif category == 'certifications_professionnelles':
            if 'domaine' in claim:
                details.append(f"Domaine: {claim['domaine']}")
        elif category == 'formations_certifiantes':
            if 'duree' in claim:
                details.append(f"Durée: {claim['duree']}")
        elif category == 'langues_certifiees':
            if 'langue' in claim:
                details.append(f"Langue: {claim['langue']}")
            if 'niveau' in claim:
                details.append(f"Niveau: {claim['niveau']}")

        return '\n'.join(details) if details else ""

    def generer_quiz_coursera(self, competence_nom: str, niveau: str = "", contexte_cv: str = "", cv_text: str = "") -> Dict:
        """
        Génère un quiz basé UNIQUEMENT sur un cours Coursera recommandé (SANS matrice de compétences)

        Workflow simplifié:
        1. Trouve le meilleur cours Coursera (avec contexte + niveau)
        2. Scrape "What you'll learn" du cours
        3. Génère un quiz basé sur ces objectifs

        Args:
            competence_nom: Nom de la compétence (ex: "Python", "SQL")
            niveau: Niveau déclaré dans le CV ("Débutant", "Intermédiaire", "Avancé")
            contexte_cv: Contexte professionnel (ex: "Data Science", "Web Development")
            cv_text: Texte complet du CV (pour extraction automatique du contexte)

        Returns:
            Dict contenant le test généré ou un message d'erreur
        """
        print(f"\n=== GENERATION QUIZ COURSERA POUR: {competence_nom} ===")

        try:
            # 1. Extraire le contexte du CV si fourni
            contexte_pour_recherche = contexte_cv
            if not contexte_pour_recherche and cv_text:
                contexte_pour_recherche = self._extraire_contexte_professionnel(cv_text)
                if contexte_pour_recherche:
                    print(f"[INFO] Contexte extrait du CV: {contexte_pour_recherche}")

            # 2. Recommander le meilleur cours AVEC contexte et niveau
            import sys
            import os
            scraper_path = os.path.join(os.path.dirname(__file__), 'course_scraper')
            if scraper_path not in sys.path:
                sys.path.insert(0, scraper_path)

            from coursera_scraper_utils import (
                scrape_course_modules_details,
                format_modules_for_quiz_context,
                scrape_what_you_learn
            )

            print(f"[INFO] Recherche du cours Coursera le plus pertinent...")
            cours_list = self.recommander_cours(
                competence_nom,
                top_n=1,
                contexte_cv=contexte_pour_recherche,
                niveau_declare=niveau
            )

            if not cours_list or len(cours_list) == 0:
                return {'erreur': f"Aucun cours Coursera trouvé pour {competence_nom}"}

            cours_recommande = cours_list[0]
            cours_url = cours_recommande.get('url', '')
            cours_titre = cours_recommande.get('titre', '')
            score_similarite = cours_recommande.get('score_similarite', 0)

            print(f"[OK] Cours trouvé: {cours_titre}")
            print(f"[INFO] Score de similarité: {score_similarite}%")

            # SEUIL DE QUALITÉ : Si score < 50%, test indisponible
            SEUIL_MINIMUM = 50.0

            if score_similarite < SEUIL_MINIMUM:
                print(f"[WARNING] Score trop faible ({score_similarite}% < {SEUIL_MINIMUM}%)")
                print(f"[INFO] Test indisponible pour la compétence '{competence_nom}'")

                # Logger dans un fichier
                self._log_test_indisponible(
                    competence_nom=competence_nom,
                    niveau=niveau,
                    contexte=contexte_pour_recherche,
                    score=score_similarite,
                    cours_titre=cours_titre,
                    raison=f"Score de similarité trop faible ({score_similarite}% < {SEUIL_MINIMUM}%)"
                )

                return {
                    'erreur': 'Test indisponible',
                    'raison': f'Aucun cours de qualité suffisante trouvé (score: {score_similarite}%, minimum requis: {SEUIL_MINIMUM}%)',
                    'competence': competence_nom,
                    'score': score_similarite,
                    'cours_trouve': cours_titre
                }

            print(f"[INFO] Scraping détaillé des modules depuis: {cours_url}")

            # 3. NOUVEAU : Scraper les modules détaillés (avec fallback sur 'What you'll learn')
            modules_data = scrape_course_modules_details(cours_url)

            if modules_data and modules_data.get('modules') and len(modules_data['modules']) > 0:
                # Succès : Utiliser le contexte enrichi des modules
                contexte_cours = format_modules_for_quiz_context(modules_data)
                total_topics = sum(len(m.get('topics', [])) for m in modules_data['modules'])
                print(f"[SUCCESS] {len(modules_data['modules'])} modules extraits avec {total_topics} topics au total")

                # DEBUG: Afficher tous les topics extraits
                print("\n[DEBUG] TOPICS EXTRAITS PAR MODULE:")
                for i, module in enumerate(modules_data['modules'], 1):
                    print(f"\n  Module {i}: {module['title']} ({len(module.get('topics', []))} topics)")
                    for j, topic in enumerate(module.get('topics', []), 1):
                        print(f"    {j}. {topic}")
                print()
            else:
                # Fallback : Utiliser l'ancienne méthode 'What you'll learn'
                print("[INFO] Fallback sur 'What you'll learn'...")
                learning_objectives = scrape_what_you_learn(cours_url)

                if not learning_objectives or len(learning_objectives) == 0:
                    print("[WARNING] Impossible de scraper les objectifs, génération générique")
                    contexte_cours = f"Cours: {cours_titre}"
                else:
                    contexte_cours = f"Cours: {cours_titre}\n\n"
                    contexte_cours += "Ce que vous allez apprendre dans ce cours:\n"
                    contexte_cours += "\n".join([f"- {obj}" for obj in learning_objectives])
                    print(f"[SUCCESS] {len(learning_objectives)} objectifs d'apprentissage récupérés")

            # 4. Générer le quiz avec le LLM
            print(f"[INFO] Génération du quiz avec le LLM...")

            system_prompt = """Tu es un expert en évaluation de compétences techniques.
Génère un quiz QCM de 10 questions basé sur le contenu détaillé du cours Coursera fourni.

IMPORTANT:
- Les questions doivent couvrir les différents modules et topics du cours
- Format QCM avec 4 options par question
- Mélange de questions théoriques et pratiques
- Questions progressives avec la répartition suivante:
  * 20% faciles (2 questions) - Concepts de base des premiers modules
  * 20% intermédiaires (2 questions) - Couvrant les différents topics
  * 60% difficiles (6 questions) - Concepts avancés et application pratique
- Indique clairement la réponse correcte
- Fournis une explication détaillée pour chaque réponse
- Le score de réussite requis est de 80%

Réponds UNIQUEMENT en JSON valide, sans texte avant ou après."""

            user_prompt = f"""CONTEXTE:
Compétence testée: {competence_nom}
Niveau: {niveau or 'Non spécifié'}
Contexte professionnel: {contexte_pour_recherche or 'Non spécifié'}

CONTENU DU COURS:
{contexte_cours}

GÉNÈRE un quiz QCM de 10 questions basé sur le contenu détaillé de ce cours.
Les questions doivent couvrir les sujets principaux abordés dans les différents modules.
RAPPEL: Respecte la distribution 20% faciles (2 questions), 20% intermédiaires (2 questions), 60% difficiles (6 questions).

FORMAT JSON:
{{
  "competence_testee": "{competence_nom}",
  "niveau_difficulte": "{niveau or 'Intermédiaire'}",
  "type_test": "QCM",
  "duree_estimee": "20",
  "enonce": "Répondez aux questions suivantes pour tester vos compétences",
  "bareme": {{
    "total_points": 100,
    "seuil_reussite": 80,
    "excellent": 90
  }},
  "questions": [
    {{
      "question": "Question 1...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "reponse_correcte": "0",
      "difficulte": "facile/intermediaire/difficile",
      "explication": "Explication..."
    }}
  ]
}}"""

            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2500
                },
                timeout=60
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']

                # Nettoyer le JSON
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                resultat = json.loads(content.strip())
                print(f"[OK] Quiz généré avec {len(resultat.get('questions', []))} questions")

                # Ajouter les informations du cours Coursera
                resultat['cours_recommande'] = {
                    'titre': cours_recommande.get('titre', ''),
                    'url': cours_recommande.get('url', ''),
                    'organisme': cours_recommande.get('organisme', 'Coursera'),
                    'difficulte': cours_recommande.get('difficulte', 'N/A'),
                    'duree': cours_recommande.get('duree', 'N/A'),
                    'description': cours_recommande.get('description', '')
                }
                print(f"[INFO] Cours recommandé ajouté au résultat")

                return resultat
            else:
                error_msg = f'Erreur API: {response.status_code} - {response.text}'
                print(f"ERROR: {error_msg}")
                return {'erreur': error_msg}

        except Exception as e:
            print(f"[ERROR] Erreur lors de la génération du quiz: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'erreur': str(e)}

    def _log_test_indisponible(self, competence_nom: str, niveau: str, contexte: str,
                                score: float, cours_titre: str, raison: str):
        """
        Enregistre dans un fichier log les tests indisponibles (score < 50%)

        Args:
            competence_nom: Nom de la compétence
            niveau: Niveau du candidat
            contexte: Contexte professionnel
            score: Score de similarité obtenu
            cours_titre: Titre du meilleur cours trouvé
            raison: Raison de l'indisponibilité
        """
        import datetime
        import os

        log_file = 'tests_indisponibles.log'

        try:
            # Créer l'entrée de log
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"""
================================================================================
[{timestamp}] TEST INDISPONIBLE
================================================================================
Compétence     : {competence_nom}
Niveau         : {niveau or 'Non spécifié'}
Contexte       : {contexte or 'Non spécifié'}
Score obtenu   : {score}%
Cours trouvé   : {cours_titre}
Raison         : {raison}
================================================================================

"""

            # Écrire dans le fichier log (mode append)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            print(f"[LOG] Enregistré dans {log_file}")

        except Exception as e:
            print(f"[ERROR] Impossible d'écrire dans le log: {str(e)}")

    def _extraire_contexte_professionnel(self, cv_text: str) -> str:
        """
        Extrait le contexte professionnel principal du CV (ex: Data Science, Web Dev, etc.)

        Args:
            cv_text: Texte complet du CV

        Returns:
            Contexte professionnel (ex: "Data Science", "Web Development", "DevOps")
        """
        try:
            # Chercher des mots-clés dans le CV
            cv_lower = cv_text.lower()

            contextes = {
                'Data Science': ['data scien', 'machine learning', 'data analy', 'big data', 'analytics'],
                'Web Development': ['web dev', 'frontend', 'backend', 'fullstack', 'react', 'angular', 'django', 'flask'],
                'DevOps': ['devops', 'kubernetes', 'docker', 'ci/cd', 'jenkins', 'terraform'],
                'Mobile Development': ['mobile dev', 'android', 'ios', 'react native', 'flutter'],
                'Cloud Computing': ['cloud', 'aws', 'azure', 'gcp', 'cloud architect'],
                'Cybersecurity': ['security', 'cybersecurity', 'penetration', 'ethical hacking'],
                'Database': ['database', 'dba', 'sql server', 'postgresql', 'mongodb'],
                'AI/ML': ['artificial intelligence', 'deep learning', 'neural network', 'nlp', 'computer vision']
            }

            # Compter les occurrences pour chaque contexte
            scores = {}
            for contexte, keywords in contextes.items():
                score = sum(1 for kw in keywords if kw in cv_lower)
                if score > 0:
                    scores[contexte] = score

            # Retourner le contexte avec le plus d'occurrences
            if scores:
                meilleur_contexte = max(scores, key=scores.get)
                print(f"[INFO] Contexte détecté: {meilleur_contexte} (score: {scores[meilleur_contexte]})")
                return meilleur_contexte
            else:
                return ""

        except Exception as e:
            print(f"[WARNING] Erreur extraction contexte: {e}")
            return ""

    def extraire_competences_techniques(self, cv_texte: str) -> Dict:
        """Extraire les compétences techniques du CV pour générer des tests"""

        # Obtenir la date actuelle
        from datetime import datetime
        date_actuelle = datetime.now().strftime("%B %Y")  # Ex: "Janvier 2025"
        annee_actuelle = datetime.now().year  # Ex: 2025

        prompt = f"""Tu es un expert en analyse de CV. Extrait TOUTES les compétences techniques mentionnées dans ce CV.

DATE ACTUELLE: {date_actuelle} (Année {annee_actuelle})

IMPORTANT: Utilise cette date pour calculer la durée d'expérience à partir des dates mentionnées dans le CV.
Exemple: Si le CV indique "Développeur depuis 2020", alors l'expérience = {annee_actuelle} - 2020 = {annee_actuelle - 2020} ans

CV DU CANDIDAT:
{cv_texte}

IMPORTANT:
- Extrait les langages de programmation (Python, Java, JavaScript, SQL, etc.)
- Extrait les frameworks et bibliothèques (React, Django, TensorFlow, etc.)
- Extrait les outils et technologies (Git, Docker, AWS, etc.)
- Extrait les domaines d'expertise (Machine Learning, Data Analysis, Web Development, etc.)
- Pour CHAQUE compétence, détermine le niveau selon ces CRITÈRES:

CRITÈRES D'INFÉRENCE DU NIVEAU (si non explicitement mentionné):

CALCUL DE LA DURÉE D'EXPÉRIENCE:
- Si dates explicites (ex: "2020 - Présent" ou "2020-2023"): Calcule la durée en années
- Si "depuis X" ou "from X": Durée = {annee_actuelle} - X
- Si mention de rôle avec dates (ex: "Senior Dev 2019-2022"): Utilise ces dates
- Si plusieurs postes utilisent la même compétence: ADDITIONNE les durées

EXEMPLES DE CALCUL:
- "Python Developer 2020-2022" + "Data Scientist 2022-{annee_actuelle}" = 5 ans de Python ({annee_actuelle - 2020} ans)
- "Développeur depuis 2021" = {annee_actuelle - 2021} ans
- "Junior Dev 2023 - Présent" = {annee_actuelle - 2023} an(s)

1. DÉBUTANT (< 1 an):
   - Mentionné dans "Compétences" sans contexte d'utilisation
   - Ou "en cours d'apprentissage", "notions", "bases", "débutant"
   - Ou < 1 an d'expérience (calculé avec la date actuelle)
   - Ou projets académiques simples uniquement

2. INTERMÉDIAIRE (1-3 ans):
   - 1-3 ans d'expérience professionnelle avec cette compétence (calculé)
   - Ou projets personnels/professionnels de complexité moyenne
   - Ou utilisation dans des tâches spécifiques (non architecturales)
   - Ou rôle "Développeur" (sans mention Junior/Senior)

3. AVANCÉ (3-5 ans):
   - 3-5 ans d'expérience professionnelle (calculé avec la date actuelle)
   - Ou projets complexes (architecture, optimisation, production)
   - Ou rôle de "Lead", "Senior", "Tech Lead" utilisant cette technologie
   - Ou frameworks avancés (microservices, ML en production, CI/CD, etc.)

4. EXPERT (5+ ans):
   - 5+ ans d'expérience avec rôle "Senior", "Architect", "Principal" (calculé)
   - Ou contributions open-source, publications techniques, conférences
   - Ou conception d'architectures complexes et scalables
   - Ou certifications avancées (AWS Certified, Google Professional, etc.)
   - Ou rôle de formateur/mentor sur cette technologie

5. NON SPÉCIFIÉ:
   - Seulement si AUCUN contexte n'est disponible (ni dates, ni rôle, ni projets)

Réponds en JSON avec cette structure EXACTE:
{{
  "langages_programmation": [
    {{
      "nom": "nom du langage",
      "niveau": "débutant|intermédiaire|avancé|expert|non spécifié",
      "experience": "durée en années si mentionnée"
    }}
  ],
  "frameworks_bibliotheques": [
    {{
      "nom": "nom du framework/bibliothèque",
      "categorie": "web|mobile|data|ml|autre",
      "niveau": "débutant|intermédiaire|avancé|expert|non spécifié"
    }}
  ],
  "outils_technologies": [
    {{
      "nom": "nom de l'outil/technologie",
      "categorie": "versioning|cloud|database|devops|autre",
      "niveau": "débutant|intermédiaire|avancé|expert|non spécifié"
    }}
  ],
  "domaines_expertise": [
    {{
      "nom": "domaine (ex: Machine Learning, Web Dev)",
      "competences_associees": ["liste des compétences dans ce domaine"]
    }}
  ],
  "bases_donnees": [
    {{
      "nom": "nom de la BD (MySQL, PostgreSQL, MongoDB, etc.)",
      "type": "relationnel|nosql|autre",
      "niveau": "débutant|intermédiaire|avancé|expert|non spécifié"
    }}
  ],
  "resume_competences": "résumé en 1-2 phrases du profil technique",
  "niveau_global": "junior|intermédiaire|senior|expert"
}}

Sois précis et extrait TOUTES les compétences techniques trouvées."""

        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2500
                },
                timeout=30
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']

                # Extraire le JSON
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                resultat = json.loads(content.strip())
                return resultat
            else:
                return {'erreur': f'Erreur API: {response.status_code}'}

        except Exception as e:
            return {'erreur': str(e)}

    def generer_test_avec_matrice(self, competence_nom: str, niveau: str, matrix_file: str = "competency_matrix.json",
                                  use_coursera: bool = True, contexte_cv: str = "", cv_text: str = "") -> Dict:
        """
        Génère un test basé sur la matrice de compétences e-CF/SFIA

        NOUVEAU : Si use_coursera=True, trouve le cours Coursera le plus pertinent,
        scrape la section "What you'll learn", et utilise ces objectifs d'apprentissage
        comme contexte pour générer un quiz adapté.

        Args:
            competence_nom: Nom de la compétence (ex: "Python", "SQL", "Data Science")
            niveau: Niveau ciblé ("Débutant", "Intermédiaire", "Avancé", "Expert")
                    OU niveau de difficulté ("facile", "moyen", "difficile", "expert")
            matrix_file: Chemin vers le fichier JSON de référence
            use_coursera: Si True, utilise le contexte du cours Coursera recommandé
            contexte_cv: Contexte professionnel du CV (ex: "Data Scientist", "Web Developer")
            cv_text: Texte complet du CV (optionnel, pour extraction automatique du contexte)

        Returns:
            Dict contenant le test généré ou un message d'erreur
        """
        # Mapper le niveau de difficulte UI vers le niveau e-CF/SFIA si necessaire
        niveau_mapping = {
            'facile': 'Débutant',
            'moyen': 'Intermédiaire',
            'difficile': 'Avancé',
            'expert': 'Expert',
            'easy': 'Débutant',
            'medium': 'Intermédiaire',
            'hard': 'Avancé'
        }

        # Normaliser le niveau (en minuscules pour la recherche)
        niveau_lower = niveau.lower().strip()

        # Si c'est un niveau de difficulté, le convertir
        if niveau_lower in niveau_mapping:
            niveau_original = niveau
            niveau = niveau_mapping[niveau_lower]
            print(f"\n=== GENERATION TEST AVEC MATRICE e-CF/SFIA ===")
            print(f"Competence: {competence_nom}")
            print(f"Difficulte demandee: {niveau_original} => Niveau e-CF/SFIA: {niveau}")
        else:
            print(f"\n=== GENERATION TEST AVEC MATRICE e-CF/SFIA ===")
            print(f"Competence: {competence_nom}")
            print(f"Niveau: {niveau}")

        # 1. Charger la matrice de compétences
        try:
            with open(matrix_file, 'r', encoding='utf-8') as f:
                matrix = json.load(f)
                print(f"[OK] Matrice chargée: {matrix_file}")
        except FileNotFoundError:
            error_msg = f"Fichier de référence non trouvé: {matrix_file}"
            print(f"ERROR: {error_msg}")
            return {'erreur': error_msg}
        except json.JSONDecodeError as e:
            error_msg = f"Erreur de lecture JSON: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {'erreur': error_msg}

        # 1.5. NOUVEAU : Utiliser le contexte Coursera si activé
        coursera_context = ""
        cours_recommande = None

        if use_coursera:
            print(f"[INFO] Recherche du cours Coursera le plus pertinent pour '{competence_nom}'...")
            try:
                # Importer le module de scraping
                import sys
                import os
                scraper_path = os.path.join(os.path.dirname(__file__), 'course_scraper')
                if scraper_path not in sys.path:
                    sys.path.insert(0, scraper_path)

                from coursera_scraper_utils import scrape_what_you_learn

                # Extraire le contexte du CV si fourni
                contexte_pour_recherche = contexte_cv
                if not contexte_pour_recherche and cv_text:
                    # Extraire automatiquement le contexte professionnel du CV
                    contexte_pour_recherche = self._extraire_contexte_professionnel(cv_text)
                    if contexte_pour_recherche:
                        print(f"[INFO] Contexte extrait du CV: {contexte_pour_recherche}")

                # Recommander le meilleur cours AVEC contexte et niveau
                cours_list = self.recommander_cours(
                    competence_nom,
                    top_n=1,
                    contexte_cv=contexte_pour_recherche,
                    niveau_declare=niveau
                )

                if cours_list and len(cours_list) > 0:
                    cours_recommande = cours_list[0]
                    cours_url = cours_recommande.get('url', '')
                    cours_titre = cours_recommande.get('titre', '')

                    print(f"[OK] Cours trouvé: {cours_titre}")
                    print(f"[INFO] Scraping de 'What you'll learn' depuis: {cours_url}")

                    # Scraper les objectifs d'apprentissage
                    learning_objectives = scrape_what_you_learn(cours_url)

                    if learning_objectives and len(learning_objectives) > 0:
                        coursera_context = "\n\nCONTEXTE DU COURS RECOMMANDÉ (Coursera):\n"
                        coursera_context += f"Cours: {cours_titre}\n"
                        coursera_context += f"Niveau: {cours_recommande.get('difficulte', 'N/A')}\n"
                        coursera_context += f"Durée: {cours_recommande.get('duree', 'N/A')}\n\n"
                        coursera_context += "Ce que vous allez apprendre dans ce cours:\n"
                        coursera_context += "\n".join([f"- {obj}" for obj in learning_objectives])
                        coursera_context += "\n\nGénère des questions de quiz basées sur CES objectifs d'apprentissage du cours Coursera."
                        print(f"[SUCCESS] {len(learning_objectives)} objectifs d'apprentissage récupérés")
                    else:
                        print("[WARNING] Impossible de scraper les objectifs, utilisation du mode standard")
                        coursera_context = ""
                else:
                    print("[WARNING] Aucun cours Coursera trouvé, utilisation du mode standard")

            except Exception as e:
                print(f"[ERROR] Erreur lors de l'intégration Coursera: {str(e)}")
                import traceback
                traceback.print_exc()
                coursera_context = ""

        # 2. Vérifier si la compétence existe dans la matrice
        competences = matrix.get('competences', {})

        if competence_nom not in competences:
            # Créer un fichier texte pour que l'admin l'ajoute
            missing_file = f"missing_competences.txt"
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(missing_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[{json.dumps({'date': timestamp, 'competence': competence_nom, 'niveau': niveau})}]\n")
                f.write(f"Date de la demande: {timestamp}\n")
                f.write(f"Compétence demandée: {competence_nom}\n")
                f.write(f"Niveau demandé: {niveau}\n")
                f.write(f"Action requise: Ajouter cette compétence dans {matrix_file}\n")
                f.write(f"Statut: En attente de validation par l'équipe pédagogique\n")
                f.write("-" * 80 + "\n")

            print(f"[INFO] Compétence '{competence_nom}' non trouvée dans la matrice")
            print(f"[INFO] Demande enregistrée dans {missing_file} pour traitement")

            # Retourner un message simple compatible avec le frontend
            return {
                'competence_testee': competence_nom,
                'niveau_difficulte': niveau,
                'type_test': 'Non disponible',
                'enonce': f"Quiz va être implémenté prochainement",
                'duree_estimee': '0',
                'questions': [],
                'message_info': f"Le test pour '{competence_nom}' sera disponible prochainement. Votre demande a été enregistrée."
            }

        # 3. Récupérer les critères pour le niveau demandé
        competence_data = competences[competence_nom]

        if niveau not in competence_data:
            available_levels = list(competence_data.keys())
            print(f"[ERROR] Niveau '{niveau}' non disponible pour {competence_nom}")
            return {
                'erreur': f"Niveau '{niveau}' non disponible pour {competence_nom}",
                'niveaux_disponibles': available_levels
            }

        criteres = competence_data[niveau]
        print(f"[OK] Critères e-CF/SFIA récupérés pour {competence_nom} - {niveau}")

        # 4. Construire le prompt avec les critères de référence e-CF/SFIA
        system_prompt = """Tu es un évaluateur professionnel basé sur les cadres SFIA 9 et e-CF 3.0.

Génère des questions de test précises selon la compétence et le niveau fournis.
Chaque question doit mesurer au moins un des critères suivants :
- knowledge (savoir)
- skills (savoir-faire)
- autonomy (niveau d'autonomie)
- complexity (capacité à gérer la complexité)

RÈGLES COMPORTEMENTALES:
- Utilise TOUJOURS la logique SFIA 9 et e-CF 3.0 pour les niveaux de complexité et d'autonomie
- Maintiens un langage cohérent (français dans ce cas)
- Ne fournis JAMAIS d'explications en dehors des structures JSON
- Concentre-toi sur la précision technique et des scénarios réalistes"""

        user_prompt = f"""INSTRUCTION:
Génère des questions de test précises pour évaluer la compétence suivante.

CONTEXTE:
Compétence : {competence_nom}
Niveau ciblé : {niveau}

CRITÈRES DE RÉFÉRENCE (e-CF/SFIA):
{json.dumps(criteres, ensure_ascii=False, indent=2)}

{coursera_context}

FORMAT DE SORTIE (JSON):
{{
  "competence_testee": "{competence_nom}",
  "niveau_difficulte": "{niveau}",
  "framework": "SFIA 9 + e-CF 3.0",
  "duree_estimee": "5-10",
  "questions": [
    {{
      "criterion": "knowledge",
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "reponse_correcte": "0",
      "explication": "Pourquoi cette réponse correspond au niveau visé"
    }},
    {{
      "criterion": "skills",
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "reponse_correcte": "1",
      "explication": "Pourquoi cette réponse correspond au niveau visé"
    }},
    {{
      "criterion": "autonomy",
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "reponse_correcte": "2",
      "explication": "Pourquoi cette réponse correspond au niveau visé"
    }},
    {{
      "criterion": "complexity",
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "reponse_correcte": "3",
      "explication": "Pourquoi cette réponse correspond au niveau visé"
    }},
    {{
      "criterion": "knowledge",
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "reponse_correcte": "0",
      "explication": "Pourquoi cette réponse correspond au niveau visé"
    }}
  ]
}}

IMPORTANT:
- Génère AU MOINS 5 questions (une par critère minimum)
- Les questions doivent être techniques, précises et adaptées au niveau {niveau}
- Utilise les critères de référence fournis pour calibrer la difficulté
- Les réponses doivent être claires et sans ambiguïté
- La reponse_correcte doit être "0", "1", "2" ou "3" (index de l'option correcte)"""

        # 5. Appeler l'API pour générer les questions
        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.4,
                    "max_tokens": 2000
                },
                timeout=60
            )

            print(f"API Response status: {response.status_code}")

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                print(f"Raw response (first 300 chars): {content[:300]}")

                # Extraire le JSON
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                resultat = json.loads(content.strip())
                print(f"[OK] Test généré avec {len(resultat.get('questions', []))} questions")

                # Ajouter les informations du cours Coursera si disponible
                if cours_recommande:
                    resultat['cours_recommande'] = {
                        'titre': cours_recommande.get('titre', ''),
                        'url': cours_recommande.get('url', ''),
                        'organisme': cours_recommande.get('organisme', 'Coursera'),
                        'difficulte': cours_recommande.get('difficulte', 'N/A'),
                        'duree': cours_recommande.get('duree', 'N/A'),
                        'description': cours_recommande.get('description', '')
                    }
                    print(f"[INFO] Cours recommandé ajouté au résultat: {cours_recommande.get('titre', 'N/A')}")

                return resultat
            else:
                error_msg = f'Erreur API: {response.status_code} - {response.text}'
                print(f"ERROR: {error_msg}")
                return {'erreur': error_msg}

        except Exception as e:
            error_msg = str(e)
            print(f"EXCEPTION: {error_msg}")
            import traceback
            traceback.print_exc()
            return {'erreur': error_msg}

    def generer_test_technique(self, competence: dict, categorie: str, difficulte: str = "moyen") -> Dict:
        """Générer un test technique structuré avec taxonomie de Bloom pour une compétence"""
        nom_competence = competence.get('nom', '')

        # Mapper les niveaux de difficulté selon Bloom
        niveau_mapping = {
            "facile": "Bloom 1-2 (reconnaissance, compréhension, définitions, bases)",
            "moyen": "Bloom 2-4 (application, interprétation, mini-cas pratiques)",
            "difficile": "Bloom 4-6 (analyse, évaluation, conception, raisonnement complexe)"
        }

        description_niveau = niveau_mapping.get(difficulte, niveau_mapping["moyen"])

        # System prompt (contexte du rôle)
        system_prompt = """Tu es un expert en évaluation technique et pédagogique.
Ta mission est de générer des tests QCM courts et fiables pour évaluer des compétences techniques extraites de CV.
Tu suis les principes de la taxonomie de Bloom pour ajuster la difficulté et produis des QCM adaptés, clairs, et pédagogiquement pertinents.

🎯 Objectif : Créer un test de 5 questions à choix multiple (QCM) mesurant la maîtrise réelle d'une compétence donnée.

🧩 Logique de difficulté (Taxonomie de Bloom) :
- Niveau "facile" → Bloom 1-2 : reconnaissance, compréhension, définitions, bases.
- Niveau "moyen" → Bloom 2-4 : application, interprétation, mini-cas pratiques.
- Niveau "difficile" → Bloom 4-6 : analyse, évaluation, conception, raisonnement complexe.

📋 Contraintes de génération :
- EXACTEMENT 5 questions QCM indépendantes
- 4 options par question (une seule correcte)
- Réponses indexées 0-3
- Test réalisable en 5-10 minutes
- Explication courte et claire justifiant la bonne réponse
- Pas de réponses ambiguës ni "toutes les réponses sont correctes"
- Langage professionnel et concis, sans jargon inutile
- Adapter la difficulté selon le paramètre demandé"""

        # User prompt (requête spécifique)
        user_prompt = f"""COMPÉTENCE: {nom_competence}
CATÉGORIE: {categorie}
NIVEAU DE DIFFICULTÉ: {difficulte.upper()} ({description_niveau})

Génère un test QCM conforme aux instructions système.
Adapte le contenu, la complexité et les raisonnements au niveau demandé.

Réponds UNIQUEMENT en JSON avec cette structure EXACTE :
{{
  "competence_testee": "{nom_competence}",
  "niveau_difficulte": "{difficulte}",
  "duree_estimee": "5-10",
  "questions": [
    {{
      "question": "Question technique sur {nom_competence}",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "reponse_correcte": "0",
      "explication": "Justification courte et claire de la bonne réponse"
    }},
    {{
      "question": "Question technique sur {nom_competence}",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "reponse_correcte": "1",
      "explication": "Justification courte et claire de la bonne réponse"
    }},
    {{
      "question": "Question technique sur {nom_competence}",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "reponse_correcte": "2",
      "explication": "Justification courte et claire de la bonne réponse"
    }},
    {{
      "question": "Question technique sur {nom_competence}",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "reponse_correcte": "3",
      "explication": "Justification courte et claire de la bonne réponse"
    }},
    {{
      "question": "Question technique sur {nom_competence}",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "reponse_correcte": "0",
      "explication": "Justification courte et claire de la bonne réponse"
    }}
  ]
}}

IMPORTANT:
- reponse_correcte doit être "0", "1", "2" ou "3" (index de l'option correcte)
- Génère EXACTEMENT 5 questions
- Questions pratiques et concrètes adaptées au niveau {difficulte}
- Pas de code JSON en dehors de la structure demandée"""

        try:
            print(f"\n=== GENERATION TEST (BLOOM) ===")
            print(f"Competence: {nom_competence}")
            print(f"Categorie: {categorie}")
            print(f"Difficulte: {difficulte}")
            print(f"Taxonomie Bloom: {description_niveau}")

            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.5,
                    "top_p": 0.9,
                    "max_tokens": 1500,
                    "seed": 42
                },
                timeout=40
            )

            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                print(f"Raw response: {content[:300]}...")

                # Extraire le JSON
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]

                resultat = json.loads(content.strip())
                print(f"Test generated successfully with {len(resultat.get('questions', []))} questions")
                return resultat
            elif response.status_code == 429:
                error_msg = 'Limite API atteinte. Veuillez patienter quelques secondes et réessayer.'
                print(f"ERROR: {error_msg}")
                return {'erreur': error_msg}
            else:
                error_msg = f'Erreur API: {response.status_code}'
                print(f"ERROR: {error_msg}")
                return {'erreur': error_msg}

        except Exception as e:
            error_msg = str(e)
            print(f"EXCEPTION: {error_msg}")
            return {'erreur': error_msg}