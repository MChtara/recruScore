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

    def extraire_competences_techniques(self, cv_texte: str) -> Dict:
        """Extraire les compétences techniques du CV pour générer des tests"""
        prompt = f"""Tu es un expert en analyse de CV. Extrait TOUTES les compétences techniques mentionnées dans ce CV.

CV DU CANDIDAT:
{cv_texte}

IMPORTANT:
- Extrait les langages de programmation (Python, Java, JavaScript, SQL, etc.)
- Extrait les frameworks et bibliothèques (React, Django, TensorFlow, etc.)
- Extrait les outils et technologies (Git, Docker, AWS, etc.)
- Extrait les domaines d'expertise (Machine Learning, Data Analysis, Web Development, etc.)
- Classe par catégories et indique le niveau si mentionné

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