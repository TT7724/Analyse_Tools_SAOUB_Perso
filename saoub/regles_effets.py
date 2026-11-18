"""Règles de reconnaissance des effets : SOURCE UNIQUE.

Ces listes sont de simples chaînes (expressions régulières). Elles servent :
- à l'application (saoub/effets.py, en Python pur) ;
- aux notebooks Spark, qui peuvent les importer au lieu de les recopier :
      import sys; sys.path.insert(0, "..")
      from saoub.regles_effets import SPLIT, EXCLUS, REGLES, BONUS
Modifier une règle ici la modifie partout.
"""

SLOTS_COMPETENCES = ["competence_1", "competence_2", "competence_3"]
SLOTS_TOUS = SLOTS_COMPETENCES + ["incarnation"]

# Découpe une description en phrases : un point suivi d'espaces puis d'une majuscule
SPLIT = r"(?<=\.)\s+(?=[A-ZÀÂÉÈÊÎÔÛÇ])"

# Phrases déjà traitées ailleurs (Break, Charge, Mode enhance, Enhance, Heal) ou sans intérêt ici
EXCLUS = (r"^(Brise la Volonté|Charge la Volonté de|Entre soi-même en mode|Capacité d'un allié|Soins HP"
          r"|Attaque (tranchante|magique|perçante|de frappe)( de Volonté)?( à puissance énorme)? sur (un ennemi|tous les ennemis)$"
          r"|Temps de préparation|Rotation|\（仮\）|$)")

REGLES = [
    (r"^Résistances? physique( et magique)? -N%", "Malus résistance physique"),
    (r"^Résistance magique (sur l'ennemi )?-N%|^Résistances? physique et magique -N%"
     r"|^Résistance physique -N% et résistance magique -N%", "Malus résistance magique"),
    (r"^Résistance à l'élément [^ ]+ -N%|^La résistance à l'élément [^ ]+ diminue"
     r"|et de N% la résistance à l'élément", "Malus résistance d'élément"),
    (r"^De plus, DEF et MDEF -N% si l'ennemi", "Malus DEF et MDEF (ennemi d'un élément)"),
    (r"^ATK -N%", "Malus ATK"),
    (r"^MATK -N%", "Malus MATK"),
    (r"^MP -N% pour l'élément", "Malus MP selon l'élément"),
    (r"^Élément [^ ]+ -N% sur l'ennemi", "Malus d'élément sur l'ennemi"),
    (r"^Réduit de N% le Break de Volonté de l'ennemi", "Réduction du Break ennemi"),
    (r"^Réduit de N% le Break de la compétence ennemie", "Réduction du Break de la compétence ennemie"),
    (r"^Réduit (de N% )?la Charge de Volonté (ennemie|de l'ennemi)|^Charge de Volonté de l'ennemi -N%", "Réduction de la Charge ennemie"),
    (r"^Inflige des dégâts continus", "Dégâts continus"),
    (r"^Provoque l'ennemi", "Provocation"),
    (r"^Inflige une contre-attaque", "Contre-attaque"),
    (r"^(Guérit|Soigne|Guérison)", "Guérison / soin de statut"),
    (r"^Restauration de MP", "Restauration de MP (alliés)"),
    (r"^Absorption des HP", "Absorption de HP"),
    (r"^Multiplie (sa|le|la) |^Capacité à charger", "Multiplication Charge/Break (soi)"),
    (r"^Attaque .*N% de dégâts de HP maximum", "Attaque avec coût en HP"),
    (r"^Et attaque ", "Attaque supplémentaire"),
    (r"^En contrepartie|^Résistance [^ ]+ sur soi-même -N%", "Malus en contrepartie"),
]

BONUS = [
    (r"(?<![A-Za-z])ATK", "Bonus ATK"),          # pas de lettre devant : MATK est à part
    (r"MATK", "Bonus MATK"),
    (r"[Rr]ésistances? physique", "Bonus résistance physique"),
    (r"[Rr]ésistances? (physique et )?magique", "Bonus résistance magique"),
    (r"[Rr]ésistance (d'|à l')élément", "Bonus résistance d'élément"),
    (r"[Dd]égâts critiques", "Bonus dégâts critiques"),
    (r"Taux de coup critique", "Bonus taux de critique"),
    (r"Taux d'esquive", "Bonus esquive"),
]

# Recollection Field, « augmentations conditionnelles » et bonus (utilisés par saoub/effets.py)
RF_VALEUR = r"^Recollection Field(?: spécial)? \([^)]*\)\s*\+(\d+)"
EST_BOOST = (r"[Aa]ugmentation (de N% )?(des dégâts(?! critiques)|de la Charge de Volonté|de la capacité à briser|du Break de Volonté)"
             r"|^Augmente les dégâts(?! critiques)|^Lance sur tous les alliés un bonus augmentant les dégâts")
BOOST_DEGATS = r"[Aa]ugmentation (de N% )?des dégâts(?! critiques)|^Augmente les dégâts(?! critiques)|bonus augmentant les dégâts"
EST_BONUS = (r"\+N%|en augmentant de N%|en augmentant l'(ATK|MATK) de N%"
             r"|^Augmentation de N% des dégâts critiques|^Augmente les dégâts critiques de N%")

# Catégories (mêmes noms que categorie_effet du notebook 03) + celle des effets créés dans l'application
CATEGORIES = ["Rôle", "Recollection Field", "Augmentation conditionnelle", "Bonus (buff)",
              "Malus sur l'ennemi", "Autres mécaniques"]
CATEGORIE_PERSO = "Personnalisé"
