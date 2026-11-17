# Analyse_Tools_SAOUB_perso

Analyse des personnages du jeu **SAOUB** et outil de **création de personnage** : on fixe des contraintes (stats, effets, rôles) et l'outil propose le reste de façon cohérente avec ce que font les développeurs, puis diagnostique le résultat.
Réalisé avec l'IA

> Projet personnel, non officiel. Le fichier `data/personnages_fr.json` contient des données issues du jeu, fournies pour reproduire l'analyse.

## Sommaire

- [Objectif](#objectif)
- [Ce que montre l'analyse](#ce-que-montre-lanalyse)
- [Structure du dépôt](#structure-du-dépôt)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Méthodes utilisées](#méthodes-utilisées)
- [Format de l'export](#format-de-lexport)
- [Limites](#limites)
- [Problèmes courants](#problèmes-courants)
- [Versions testées](#versions-testées)

## Objectif

Le projet répond à deux questions :

1. **Comment les développeurs conçoivent-ils leurs personnages ?** (stats, compétences, effets)
2. **Peut-on proposer un nouveau personnage plausible**, en laissant l'utilisateur imposer ce qu'il veut (une valeur d'ATK, un percentile de vitesse, un effet comme « Dégâts continus »…) ?

L'outil propose des personnages **plausibles par rapport aux existants**, pas des personnages « optimaux » : il n'y a aucune donnée de combat dans le jeu de données.

## Ce que montre l'analyse

Données : 218 personnages de rareté 4, dont 37 « free » (offerts, souvent plus faibles). Les modèles sont appris sur les **181 non-free**.

- **Stats** : au niveau 100, HP, ATK, MATK, DEF et MDEF valent environ 5 fois leur valeur du niveau 1 ; au niveau 120, ces stats valent 1,2 fois le niveau 100.
- **Grille** : les valeurs suivent des paliers (au niveau 100 : HP par 75, DEF et MDEF par 15, ATK et MATK par 25). Entre 123 et 143 persos non free sur 181 sont exactement sur la grille selon la stat. Les free la respectent beaucoup moins.
- **Deux familles** : physique (ATK ≥ MATK, 117 persos) et magique (64 persos). ATK et MATK sont corrélées à −0,78.
- **Kit** : 59 effets distincts (compétences 1 à 3 et incarnation), taille de kit médiane de 5 éléments. 39 de ces effets concernent moins de 10 persos non free.
- **Indépendance** : d'après les notebooks 01 et 02, les stats d'un perso n'expliquent pas son kit (et inversement).

## Structure du dépôt

```
Analyse_Tools_SAOUB_perso/
├── data/
│   ├── personnages_fr.json          # données d'entrée (218 personnages)
│   └── personage_new.json           # persos créés (généré par le notebook 03)
├── notebook/
│   ├── 01_Analyse_all_perso.ipynb             # analyse, avec les persos free
│   ├── 02_Analyse_perso_without_free.ipynb    # même analyse, sans les free
│   └── 03_Creation_perso.ipynb                # outil de création de personnage
├── main.py                          # réservé à la future application (vide pour l'instant)
├── requirements.txt
└── README.md
```

## Prérequis

| Outil | Version | Pourquoi |
|---|---|---|
| Python | 3.11 ou plus récent (testé avec 3.13) | exigé par PySpark 4.3 |
| Java | 21 | PySpark tourne sur la JVM |
| Git | récent | pour cloner le dépôt |

Vérifie tes versions :

```bash
python --version
java -version
```

## Installation

Remplace `<URL_DU_DEPOT>` par l'adresse du dépôt.

**Windows (PowerShell)**

```powershell
git clone https://github.com/TT7724/Algo_Genetique_Plantes.git
cd Analyse_Tools_SAOUB_perso
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si PowerShell refuse d'exécuter le script d'activation, autorise-le pour la session en cours, puis relance l'activation :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**Linux / macOS**

```bash
git clone https://github.com/TT7724/Algo_Genetique_Plantes.git
cd Analyse_Tools_SAOUB_perso
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Utilisation

### 1. Ouvrir les notebooks

Depuis la racine du projet, environnement activé :

```bash
jupyter lab
```

Ouvre ensuite un fichier du dossier `notebook/`. Le noyau Jupyter travaille dans le dossier du notebook, ce qui fait que le chemin `../data/personnages_fr.json` fonctionne tel quel.

Avec **PyCharm** : choisis `.venv` comme interpréteur du projet et ouvre les notebooks directement.

**Rejoue toujours les cellules dans l'ordre**, de haut en bas : chaque cellule s'appuie sur les précédentes.

### 2. Quel notebook ouvrir ?

| Notebook | Rôle | Durée indicative |
|---|---|---|
| `01_Analyse_all_perso` | Analyse complète des 218 persos (graphiques, grilles de stats, effets) | quelques minutes |
| `02_Analyse_perso_without_free` | Même analyse sans les persos free | quelques minutes |
| `03_Creation_perso` | **L'outil de création** | environ 1 minute |

Les notebooks 01 et 02 contiennent leurs graphiques déjà calculés. Il n'est pas nécessaire de les rejouer pour utiliser l'outil.

### 3. Créer un personnage (notebook 03)

Le notebook est découpé en sections. Pour créer un perso, rejoue les sections de chargement, puis les deux moteurs, puis passe à « Validation du perso ».

1. **Chargement et nettoyage** : session Spark locale, lecture du JSON, drapeau `free`, table des effets, table de travail.
2. **Moteur de stats** : apprend les lois de probabilité des 8 stats (HP, MP, ATK, MATK, DEF, MDEF, CRIT, SPD) sur les non-free.
3. **Moteur de kit** : apprend quels effets et rôles vont ensemble.
4. **Validation du perso** : c'est ici que tu écris tes contraintes et que tu crées un perso.
5. **Export** : enregistre le perso choisi dans `data/personage_new.json`.

**Contraintes sur les stats** (dictionnaire `CONTRAINTES_STATS`) :

| Règle | Sens | Exemple |
|---|---|---|
| `egal` | valeur exacte (arrondie à la grille) | `"ATK": {"egal": 2800}` |
| `min` / `max` | bornes | `"HP": {"min": 7500, "max": 8500}` |
| `pct_min` / `pct_max` | percentile parmi les non-free | `"SPD": {"pct_min": 80}` |
| `famille` | `"physique"` ou `"magique"` | `"famille": "magique"` |

**Contraintes sur le kit** (liste `IMPOSES_KIT`) : des noms exacts d'effets ou de rôles. `display(lister_effets(moteur_kit))` les affiche tous avec leur effectif. Une faute de frappe donne une erreur avec des suggestions.

**Exemple complet :**

```python
CONTRAINTES_STATS = {"famille": "physique", "ATK": {"egal": 2800}, "SPD": {"pct_min": 80}}
IMPOSES_KIT = ["Dégâts continus"]

persos = creer_persos(moteur, moteur_kit, CONTRAINTES_STATS, IMPOSES_KIT, n=5, graine=0)
afficher_persos(persos)

CHOIX = 0
alertes = valider_perso(moteur, moteur_kit, persos[CHOIX])
```

**Réglages optionnels :**

- `distance_min=0.6` : n'accepte que des stats à au moins cette distance de tout perso existant (persos plus originaux, sans sortir des plages observées).
- `temperature_kit=1.5` : tire des effets moins fréquents ; `temperature_stats` élargit la dispersion des stats (à garder en dessous de 1,3).
- `graine=…` : change le tirage ; la même graine redonne les mêmes résultats.

**Valider un perso imaginé par toi :**

```python
MON_PERSO = dict(stats={"HP": 7800, "MP": 270, "ATK": 2800, "MATK": 2300,
                        "DEF": 1500, "MDEF": 1450, "CRIT": 720, "SPD": 335},
                 kit=["Rôle Break", "Dégâts continus"])
valider_perso(moteur, moteur_kit, MON_PERSO)
```

### 4. Lire la validation

`valider_perso` affiche des **signaux**, pas des interdits : un ⚠ signifie « ne ressemble pas à l'existant ».

- **Percentile** : 90 veut dire « meilleur que 90 % des persos non free » sur cette stat.
- **Distance au plus proche perso réel** (stats) : médiane 0,41 entre persos réels, 95 % sont sous 0,78. Au-delà, le perso est plus atypique que 95 % des vrais.
- **Distance de Jaccard** (kits) : 0 = kits identiques, 1 = rien en commun. Entre vrais kits : médiane 0,38, 95e percentile 0,56.
- **Effets rares** : un effet présent chez moins de 10 vrais persos s'appuie sur très peu d'exemples.
- **Paires jamais vues** : deux éléments qui ne sont jamais ensemble chez les vrais persos alors qu'on en attendrait au moins 3 par hasard.
- **Vrais persos conformes** : si moins de 10 vrais persos respectent déjà tes contraintes, la proposition vient surtout du modèle et pas d'exemples réels.

### 5. Exporter

```python
nouveau = exporter_perso(
    persos[CHOIX], moteur, df_perso_complet,
    id_perso=999000001,            # un id qui n'existe pas dans le jeu
    nom="Mon perso", titre="[Mon titre]",
    element="feu", arme="Épée",    # les valeurs valides s'affichent dans l'erreur si tu te trompes
    chemin="../data/personage_new.json",
    parametres=dict(graine=0, contraintes_stats=CONTRAINTES_STATS, imposes_kit=IMPOSES_KIT))
```

Le fichier `data/personage_new.json` est créé au premier export, puis complété aux suivants. Un id déjà utilisé (dans le jeu ou dans le fichier) est refusé ; `remplacer=True` écrase un perso du fichier.

## Méthodes utilisées

| Étape | Méthode |
|---|---|
| Stats | Une loi normale à 8 dimensions **par famille** (physique, magique) ; contraintes par **conditionnement gaussien** ; **tirage par rejet** pour les bornes ; arrondi à la grille (HP, ATK, MATK, DEF, MDEF) ou à une valeur déjà vue (MP, CRIT, SPD) |
| Kit | **Modèle séquentiel** : chaque élément est tiré sachant ceux déjà choisis ; **lissage** vers les fréquences globales (k = 5, choisi par validation croisée « un perso à la fois ») ; regroupement des effets rares en trois niveaux ; **calibrage** des fréquences |
| Validation | Percentiles, distance au plus proche perso réel sur stats centrées-réduites, distance de Jaccard sur les kits, recherche de paires jamais vues |

Mesures de contrôle sur les données (sans contrainte) :

- Stats : moyennes générées quasi identiques aux réelles, écart moyen de corrélation de 0,02, aucune copie exacte d'un perso réel. L'écart-type des HP générés est un peu plus faible (524 contre 571), car les valeurs hors plage observée sont rejetées.
- Kit : écart moyen de fréquence de 0,5 point, taille moyenne 4,82 contre 4,83 réellement, 3,7 % de kits identiques à un vrai kit au niveau des groupes.

## Format de l'export

Chaque perso exporté reprend les clés du JSON d'origine, avec :

- les stats aux niveaux 1, 80, 100 et 120 (reconstruites depuis le niveau 100 ; erreur d'au plus 1 point sur les non-free) ;
- trois clés en plus : `genere` (vrai), `kit_propose` (liste d'effets) et `parametres_generation` (graine et contraintes).

**Les compétences sont des emplacements vides** : l'outil ne génère ni noms, ni textes, ni puissances, ni coûts en MP. Ils sont à écrire à la main.

## Limites

- Seulement 218 persos (181 non-free), tous de rareté 4.
- Aucune donnée de combat : la puissance réelle n'est pas mesurable, seulement la cohérence avec l'existant.
- Les stats et le kit sont générés indépendamment, car l'analyse ne montre aucun lien entre eux.
- Le kit est une liste d'effets pour tout le perso : l'emplacement (compétence 1, 2, 3 ou incarnation) n'est pas modélisé.
- Le regroupement des effets rares est un choix modifiable (`famille_effet`, `SEUIL_RARE`).
- Les classifications d'effets (cible d'un effet, catégories) sont aussi des choix.
- Les propositions d'un même tirage ne sont pas diversifiées entre elles.

## Problèmes courants

| Symptôme | Cause et solution |
|---|---|
| `Python worker failed to connect back` (Windows) | Les « Python workers » de Spark échouent sur certaines machines Windows. Le projet n'utilise ni UDF, ni `createDataFrame`, ni RDD. Pour du code Spark à toi, reste sur les fonctions `F.*` et `toPandas()` |
| `java` introuvable ou mauvaise version | Vérifie `java -version` (21 attendu). Si besoin, définis `JAVA_HOME`, par exemple `$env:JAVA_HOME = "C:\Program Files\Java\jdk-21"` (adapte le chemin) |
| `Path does not exist: ../data/personnages_fr.json` | Le notebook n'est pas lancé depuis son dossier. Ouvre-le via `jupyter lab` ou PyCharm, ou modifie `CHEMIN_JSON` |
| `id … déjà présent dans …/personage_new.json` | Tu rejoues l'export avec un id déjà utilisé. Change `id_perso` ou ajoute `remplacer=True` |
| `UserWarning: toPandas attempted Arrow optimization…` | Sans danger : PyArrow n'est pas installé, Spark utilise la conversion standard. `pip install pyarrow` est facultatif (non testé sous Windows) |
| `FutureWarning: Downcasting object dtype…` | Avertissement de pandas dans les notebooks 01 et 02, sans effet sur les résultats |
| `FutureWarning: PySpark does not yet fully support pandas >= 3.0.0` | Tu as installé pandas 3. Utilise `pip install -r requirements.txt` (pandas est borné à la version 2) |
| Le résultat de `correspondances` devient faux dans les notebooks 01 et 02 | Ne nomme jamais une variable `p` : elle écrase `p = F.col("p")`. Utilise des noms explicites |

## Versions testées

Développé sous Windows avec PyCharm. L'exécution complète des trois notebooks, de zéro, dans un nouvel environnement virtuel a été vérifiée sous Linux avec :

Python 3.13 · OpenJDK 21 · pyspark 4.3.0 · pandas 2.3.3 · numpy 2.5.5 · scipy 1.18.1 · matplotlib 3.11.2 · seaborn 0.13.2 · adjustText 1.4.0 · jupyterlab 4.6.6

Aucune cellule n'est en erreur.