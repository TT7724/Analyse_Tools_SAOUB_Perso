# Analyse_Tools_SAOUB_perso

Analyse des 218 personnages (rareté 4) du jeu SAOUB et **application web locale** pour :

- **explorer** les persos avec des graphiques interactifs filtrables ;
- **créer** de nouveaux persos (stats + kit d'effets) qui ressemblent à ce que font les développeurs ;
- **vérifier** un perso imaginé ou reçu d'un ami ;
- **inventer** des effets personnalisés.

Projet personnel d'étudiant (4e année d'informatique), orienté data science. Dépôt : `<URL_DU_DEPOT>`.

---

## Sommaire

1. [Installation](#installation)
2. [Lancer l'application](#lancer-lapplication)
3. [Ce que fait l'application](#ce-que-fait-lapplication)
4. [Les notebooks d'analyse](#les-notebooks-danalyse)
5. [Tests](#tests)
6. [Organisation du code](#organisation-du-code)
7. [Fichiers de données](#fichiers-de-données)
8. [Méthode et limites](#méthode-et-limites)

---

## Installation

Prérequis : **Python 3.11 ou plus** (`python --version`). Java n'est nécessaire que pour les notebooks (voir plus bas).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (sous Linux/macOS : source .venv/bin/activate)
pip install -r requirements.txt
```

Pour **l'application seule** (par exemple sur le PC d'un ami), sans Spark ni Java :

```bash
pip install -r requirements-app.txt
```

## Lancer l'application

Depuis la racine du projet, environnement activé :

```bash
streamlit run app.py
```

Le navigateur s'ouvre sur `http://localhost:8501`. Le premier chargement prend environ 5 secondes (réglage des moteurs),
ensuite tout est en mémoire. `Ctrl+C` dans le terminal pour arrêter.

**Pour des amis sur le même Wi-Fi** : le terminal affiche aussi une `Network URL` (`http://192.168.x.x:8501`). Ils
l'ouvrent dans leur navigateur, sans rien installer. Au premier lancement, Windows demande d'autoriser l'accès réseau.
L'application n'est disponible que pendant que ton PC tourne.

## Ce que fait l'application

Chaque outil et chaque graphique a un bouton **« ? »** qui explique ce qu'il montre, à quoi il sert, comment le lire et
ses limites.

| Page | Contenu |
|---|---|
| 🏠 **Accueil** | Compteurs (persos, offerts, effets), alerte s'il y a des phrases de compétences non reconnues, bouton « Recharger les données ». |
| 📊 **Graphiques** | Filtres communs dans la barre latérale (niveau 100/120/1, tous / sans les offerts, élément, arme, famille, effet, recherche par nom ou titre). **Simple** : répartition, distribution d'une stat, meilleurs/pires, carte d'identité (radar, comparaison de deux persos), effets. **Avancé** : effets × élément, corrélations, menu des valeurs (grille), ordre de sortie, voisins et groupes (dendrogramme), carte 2D (ACP), offre/demande d'états ennemis, complexité du kit, triangles de budget. Chaque graphique a une vue « Voir les données ». |
| 🛠️ **Création de perso** | Contraintes par listes déroulantes (famille, niveau de chaque stat, valeur exacte, fourchette), effets imposés, originalité (classique / original / audacieux), propositions variées, graine (🎲, saisie manuelle, historique des 20 derniers résultats), diagnostic de chaque proposition, **effets personnalisés**, **export** (téléchargement JSON ou ajout à `data/personage_new.json`, id libre proposé automatiquement). |
| 🔍 **Vérifier mon perso** | Saisie des stats + effets, ou import d'un JSON (format simple, fiche exportée, fichier complet, ou perso au format du jeu dont le kit est déduit des descriptions). |
| 📖 **Comment ça marche ?** | L'outil expliqué simplement, avec les chiffres de contrôle recalculés en direct. |

## Les notebooks d'analyse

Dans `notebook/` : `01_Analyse_all_perso` (avec les persos offerts), `02_Analyse_perso_without_free` (sans),
`03_Creation_perso` (prototype de l'outil de création).

Ils utilisent **PySpark 4** en local (`local[*]`, driver sur 127.0.0.1) et demandent **Java 21**. Sous Windows, les
« Python workers » de Spark échouent : les notebooks n'utilisent donc que les fonctions Spark natives (`F.*`) et
`toPandas()` (pas d'UDF, pas de `createDataFrame`, pas de RDD).

Les règles de reconnaissance des effets sont dans `saoub/regles_effets.py` (source unique). Les notebooks peuvent les
importer au lieu de les recopier :

```python
import sys; sys.path.insert(0, "..")
from saoub.regles_effets import SPLIT, EXCLUS, REGLES, BONUS
```

**L'application n'utilise pas Spark** : elle refait les mêmes calculs en pandas. Les tests vérifient que les résultats
sont identiques à ceux des notebooks.

## Tests

```bash
pytest
```

Environ 2 minutes, 40 tests. Ils vérifient notamment :

- que la version pandas donne **exactement** les mêmes tables que la version Spark (effets, table de travail) ;
- qu'à graine égale, les moteurs redonnent **les mêmes persos** que le notebook 03, et que la validation donne **les mêmes
  alertes** ;
- que chaque page de l'application s'exécute sans erreur, avec des parcours simulés (création, graine, historique,
  effets personnalisés, export, import).

Les résultats de référence sont dans `tests/reference/` (produits par les notebooks). Les tests écrivent dans un dossier
temporaire, jamais dans `data/`.

## Organisation du code

```
Analyse_Tools_SAOUB_perso/
├── app.py                    # point d'entrée Streamlit (navigation)
├── app_commun.py             # chargement en cache, bouton « ? », affichage d'un diagnostic
├── app_pages/                # une page par fichier
├── saoub/                    # le paquet (sans Streamlit, testable)
│   ├── donnees.py            # lecture du JSON, tables de travail
│   ├── regles_effets.py      # règles de reconnaissance des effets (source unique)
│   ├── effets.py             # table des effets + registre des effets personnalisés
│   ├── moteur_stats.py       # moteur de stats
│   ├── moteur_kit.py         # moteur de kit
│   ├── creation.py           # assemblage stats + kit
│   ├── validation.py         # diagnostic d'un perso
│   ├── export.py             # fiche JSON, fichier des nouveaux persos, import
│   ├── interface.py          # listes déroulantes -> paramètres des moteurs
│   ├── graphiques.py         # graphiques Plotly (filtres, onglet Simple, début de l'Avancé)
│   └── graphiques_avances.py # voisins, dendrogramme, ACP, offre/demande, complexité, triangles
├── tests/                    # pytest + résultats de référence
├── notebook/                 # analyses PySpark
├── data/                     # données (voir ci-dessous)
└── .streamlit/config.toml    # réglages de l'application
```

## Fichiers de données

| Fichier | Rôle |
|---|---|
| `data/personnages_fr.json` | Les persos du jeu (source). Pour une mise à jour du jeu : remplacer ce fichier, puis « Recharger » sur l'accueil. |
| `data/effets_personnalises.json` | Effets créés dans l'application (créé au premier effet). |
| `data/personage_new.json` | Persos exportés depuis l'application (créé au premier export). Ids à partir de 999000001. |

Les persos offerts (free) sont repérés par une liste d'ids dans `saoub/donnees.py` (`IDS_FREE`) : à compléter si le jeu
en ajoute.

## Méthode et limites

**Stats** : une loi normale à 8 dimensions par famille (physique si ATK ≥ MATK, magique sinon), apprise sur les persos non
offerts ; contraintes par conditionnement gaussien et tirage par rejet ; arrondi à la grille du jeu (niveau 100 : HP par
75, ATK/MATK par 25, DEF/MDEF par 15) ou à une valeur déjà vue (MP, CRIT, SPD). Niveaux 1, 80 et 120 déduits du niveau 100.

**Kit** : effets rares (moins de 10 persos) regroupés en 30 groupes ; taille tirée parmi les tailles réelles ; effets
ajoutés un par un selon leurs co-occurrences, lissées (k = 5, choisi par validation croisée) et calibrées.

**Validation** : percentiles, plages observées, grille, distance au plus proche vrai perso (référence : médiane 0,41,
95 % sous 0,78), distance de Jaccard au kit le plus proche, paires d'effets jamais vues ensemble.

**Limites** :

- 218 persos, tous de rareté 4, **aucune donnée de combat** : l'outil propose des persos *plausibles*, pas *optimaux*.
- Stats et kit sont tirés indépendamment ; un lien faible existe entre richesse du kit et puissance (ρ ≈ +0,19 sans
  les offerts), non utilisé.
- Les compétences (1, 2, 3, incarnation) ne sont pas distinguées ; leurs textes, puissances et MP ne sont pas générés.
- Testé sous Linux (Python 3.13, Streamlit 1.67) ; application prévue pour Windows (sans Spark).

## Licence

À choisir.
