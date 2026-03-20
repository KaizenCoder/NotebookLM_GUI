# Étude de Faisabilité : Interface Graphique pour NotebookLM

## 1. Objectif
Créer une interface graphique (GUI) permettant de lister et sélectionner des carnets (notebooks) NotebookLM, puis de télécharger leurs contenus (artefacts, notes, sources) vers des chemins locaux spécifiés par l'utilisateur, en s'appuyant sur le projet `jacob-bd/notebooklm-mcp-cli`.

## 2. Faisabilité
**Statut : EXCELLENTE (100% Réalisable)**

Le projet `notebooklm-mcp-cli` expose déjà toutes les fonctionnalités nécessaires via sa ligne de commande (`nlm`) et son serveur MCP. L'interface graphique peut agir comme une surcouche locale communicant avec ces outils.

### Points viables confirmés :
- **Lister les notebooks** : Possible via la commande `nlm notebook list` (ou l'outil MCP `mcp_notebooklm_notebook_list`).
- **Télécharger le contenu** : Possible via `nlm download <type> <notebook>` (ou l'outil externe `download_artifact` gérant audio, vidéo, rapports, markdown, etc.).
- **Authentification** : Le backend gère la récupération des cookies du navigateur (commande `nlm login`).

## 3. Architecture Technique Recommandée

### Application Desktop Python (Fortement Recommandée)
Puisque `notebooklm-mcp-cli` est un outil Python, concevoir l'interface dans le même langage est l'approche la plus cohérente et rapide.
- **Frontend UI** : `CustomTkinter` (pour un design moderne, thèmes sombre/clair) ou `PyQt6` (pour une interface très riche).
- **Communication avec NotebookLM** : Utiliser le module `subprocess` pour exécuter les commandes `nlm` en arrière-plan et récupérer leurs sorties (notamment avec des arguments JSON si supportés par la CLI pour le parsing).
- **Gestion des fichiers** : La bibliothèque Python standard permet d'afficher des fenêtres de dialogue natives pour choisir les dossiers de destination.
- **Packaging** : L'outil final peut être compilé en un exécutable unique avec `PyInstaller` ou `Nuitka`.

## 4. Parcours Utilisateur Envisagé (User Flow)
1. **Lancement de l'app** : Vérification automatique de l'authentification NotebookLM en tâche de fond.
2. **Écran Principal** : 
   - Une liste (Checkboxes) des Notebooks disponibles (récupérés dynamiquement).
   - Un menu déroulant pour sélectionner le/les types d'artefacts à télécharger (Audio, PDF, Markdown, etc.).
3. **Paramétrage** : Un champ de texte + un bouton "Parcourir" permettant de sélectionner le dossier de sauvegarde.
4. **Téléchargement** : Bouton d'action "Lancer le téléchargement" avec affichage d'une barre de progression ou d'un rapport de logs textuel.

## 5. Prochaines Étapes Suggérées
1. Création de l'architecture du projet de bureau (`app.py`, `ui/`, `core/`).
2. Preuve de concept (PoC) : Afficher une fenêtre simple de listage de carnets via `nlm notebook list`.
3. Implémenter le téléchargement bloquant/non-bloquant avec mise à jour de l'UI.
