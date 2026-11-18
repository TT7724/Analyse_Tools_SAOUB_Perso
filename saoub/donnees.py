"""Lecture du JSON des persos et tables de travail (pandas, sans Spark)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent          # dossier du projet, quel que soit le dossier courant
CHEMIN_JSON = RACINE / "data" / "personnages_fr.json"

STATS = ["HP", "MP", "ATK", "MATK", "DEF", "MDEF", "CRIT", "SPD"]
NIVEAUX = [1, 80, 100, 120]
GRILLE_100 = {"HP": 75, "DEF": 15, "MDEF": 15, "ATK": 25, "MATK": 25}

IDS_FREE = {
    130114003, 130114008, 130114015, 130114018, 130124003, 130124009, 130124010, 130124026, 130124027,
    130124030, 130124034, 130124045, 130124054, 130134005, 130144008, 130144016, 130144022, 130214011,
    130324016, 130324021, 130344003, 130344007, 130344008, 130344010, 130344012, 130454001, 130454002,
    130454005, 130454007, 130454009, 130454011, 130454012, 130454013, 130454015, 130464005, 130524003,
    130724002,
}


def charger_persos(chemin=CHEMIN_JSON):
    """Liste des persos (dictionnaires) du fichier JSON, avec la clé « free » ajoutée."""
    with open(chemin, encoding="utf-8") as f:
        persos = json.load(f)["personnages"]
    for perso in persos:
        perso["free"] = perso["id"] in IDS_FREE
    return persos


def table_stats(persos, niveaux=NIVEAUX):
    """Une ligne par perso, colonnes HP_1, ..., SPD_120 (utile pour les rapports entre niveaux et les graphiques)."""
    lignes = [{"perso_id": p["id"], **{f"{s}_{lv}": p["stats"][f"lvl_{lv}"][s] for lv in niveaux for s in STATS}}
              for p in persos]
    return pd.DataFrame(lignes).set_index("perso_id")


def table_persos(persos, niveau=100):
    """Équivalent du select(...).toPandas() de preparer_table : une ligne par perso, stats au niveau demandé."""
    lignes = []
    for p in persos:
        comp = p["competences"]
        lignes.append({"perso_id": p["id"], "nom_complet": p["nom_complet"], "element": p["element"],
                       "arme": p["arme"], "free": p["free"],
                       "c1": comp["competence_1"]["categorie"], "c2": comp["competence_2"]["categorie"],
                       "c3": comp["competence_3"]["categorie"],
                       **{s: p["stats"][f"lvl_{niveau}"][s] for s in STATS}})
    return pd.DataFrame(lignes).set_index("perso_id")


def table_de_travail(base, effets_long):
    """Même code que le notebook 03. base : 1 ligne par perso. effets_long : colonnes perso_id, effet."""
    base = base.copy()
    base["famille"] = np.where(base["ATK"] >= base["MATK"], "physique", "magique")
    cats = base[["c1", "c2", "c3"]].fillna("")
    roles = pd.DataFrame({
        "Rôle Break": cats.apply(lambda ligne: any("BREAK" in x for x in ligne), axis=1),
        "Rôle Charge": cats.apply(lambda ligne: any("CHARGE" in x for x in ligne), axis=1),
        "Rôle Mode enhance": cats.apply(lambda ligne: any(x == "ENHANCE_MODE" for x in ligne), axis=1)})
    effets = ((pd.crosstab(effets_long["perso_id"], effets_long["effet"]) > 0)
              .reindex(base.index, fill_value=False))
    kit = pd.concat([roles, effets], axis=1).astype(bool)
    base["taille_kit"] = effets.sum(axis=1)
    return dict(base=base, kit=kit)


def preparer_table(persos, df_eff, niveau=100):
    """dict(base=..., kit=...) : la table de travail des moteurs (comme dans le notebook 03)."""
    effets_long = df_eff[["perso_id", "effet"]].drop_duplicates()
    return table_de_travail(table_persos(persos, niveau), effets_long)
