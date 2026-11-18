"""Fiche d'un nouveau perso (même format que exporter_perso du notebook 03), fichier commun, import pour validation."""
import json
import os

import numpy as np

from .donnees import GRILLE_100, RACINE, STATS, table_persos, table_stats, table_de_travail
from .effets import construire_effets

CHEMIN_NOUVEAUX = RACINE / "data" / "personage_new.json"
PREMIER_ID = 999000001


def calculer_ratios_niveaux(persos):
    """Rapports niveau 1 / 80 / 120 sur niveau 100, estimés sur les persos non free."""
    t = table_stats([p for p in persos if not p["free"]])
    exacts = {1: 1 / 5, 80: 0.8, 120: 1.2}                  # règle exacte pour HP, ATK, MATK, DEF, MDEF
    return {lv: {s: (exacts[lv] if s in GRILLE_100 else float(np.median(t[f"{s}_{lv}"] / t[f"{s}_100"]))) for s in STATS}
            for lv in (1, 80, 120)}


def stats_tous_niveaux(stats100, ratios):
    out = {f"lvl_{lv}": {s: int(round(stats100[s] * ratios[lv][s])) for s in STATS} for lv in (1, 80)}
    out["lvl_100"] = {s: int(stats100[s]) for s in STATS}
    out["lvl_120"] = {s: int(round(stats100[s] * ratios[120][s])) for s in STATS}
    return {k: out[k] for k in ("lvl_1", "lvl_80", "lvl_100", "lvl_120")}


def charger_nouveaux(chemin=CHEMIN_NOUVEAUX):
    if not os.path.exists(chemin):
        return dict(source="Persos générés par l'outil de création (POC)", nb_personnages=0, personnages=[])
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def id_libre(persos, chemin=CHEMIN_NOUVEAUX, debut=PREMIER_ID):
    """Premier id ≥ debut utilisé ni dans le jeu ni dans le fichier des nouveaux persos."""
    pris = {p["id"] for p in persos} | {p["id"] for p in charger_nouveaux(chemin)["personnages"]}
    i = debut
    while i in pris:
        i += 1
    return i


def fiche_perso(perso, persos, id_perso, nom, titre, element, arme, description="", parametres=None):
    """Construit la fiche (dict) sans rien écrire. Les compétences sont des emplacements vides à remplir à la main."""
    elements = sorted({p["element"] for p in persos if not p["free"]})
    armes = sorted({p["arme"] for p in persos if not p["free"]})
    if element not in elements: raise ValueError(f"element inconnu : {element} (attendu : {elements})")
    if arme not in armes: raise ValueError(f"arme inconnue : {arme} (attendue : {armes})")
    if id_perso in {p["id"] for p in persos}: raise ValueError(f"id {id_perso} déjà utilisé dans le jeu : choisis-en un autre")
    stats = stats_tous_niveaux(perso["stats"], calculer_ratios_niveaux(persos))
    emplacement = lambda slot: dict(nom="", type="", categorie="", incarnation=(slot == "incarnation"),
                                    niveaux=[dict(niveau=1, id=None, nom="", description="", mp=None, puissance=None)])
    return dict(
        id=int(id_perso), nom=nom, nom_complet=f"{titre} {nom}", traduction_fr_officielle=False, titre=titre,
        nom_en="", nom_jp="", element=element, arme=arme, rarete=4,
        niveaux_paliers={"eveil_0": 80, "eveil_max": 100, "niveau_max": 120},
        stats=stats, stats_lvl_100=stats["lvl_100"], regen_mp_taux=500, description=description,
        competences={s: emplacement(s) for s in ("competence_1", "competence_2", "competence_3", "incarnation")},
        label=f"character.nouveau_{id_perso}",
        genere=True, kit_propose=list(perso["kit"]), parametres_generation=parametres or {})


def ajouter_au_fichier(fiche, chemin=CHEMIN_NOUVEAUX, remplacer=False):
    """Ajoute la fiche au fichier des nouveaux persos (le crée si besoin). Renvoie un message."""
    contenu = charger_nouveaux(chemin)
    deja = [i for i, p in enumerate(contenu["personnages"]) if p["id"] == fiche["id"]]
    if deja and not remplacer:
        raise ValueError(f"id {fiche['id']} déjà présent dans le fichier (coche « remplacer » pour l'écraser)")
    contenu["personnages"] = [p for p in contenu["personnages"] if p["id"] != fiche["id"]] + [fiche]
    contenu["nb_personnages"] = len(contenu["personnages"])
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    temporaire = f"{chemin}.tmp"
    with open(temporaire, "w", encoding="utf-8") as f:
        json.dump(contenu, f, ensure_ascii=False, indent=2)
    os.replace(temporaire, chemin)
    return (f"Perso {fiche['nom_complet']} (id {fiche['id']}) {'remplacé' if deja else 'ajouté'} "
            f"({contenu['nb_personnages']} perso(s) dans le fichier)")


def en_texte_json(fiche):
    """Texte JSON pour un bouton de téléchargement."""
    return json.dumps(fiche, ensure_ascii=False, indent=2)


def kit_depuis_competences(perso, effets_perso=()):
    """Kit d'un perso au format du jeu (descriptions remplies) : rôles + effets reconnus par les règles."""
    perso = {**perso, "free": perso.get("free", False)}
    eff = construire_effets([perso], effets_perso=effets_perso)
    kit = table_de_travail(table_persos([perso]), eff[["perso_id", "effet"]].drop_duplicates())["kit"]
    return [e for e in kit.columns if kit.iloc[0][e] and e != "Autre"]


def importer_persos(texte, effets_perso=()):
    """Lit un JSON collé ou chargé et renvoie une liste de {"nom", "stats", "kit"} à valider. Formats acceptés :
    - simple : {"stats": {HP: ..., ...}, "kit": [...]} (ou une liste de ces objets) ;
    - fiche exportée par l'application (stats.lvl_100 + kit_propose) ;
    - perso au format du jeu, compétences écrites : le kit est déduit des descriptions ;
    - fichier complet {"personnages": [...]}."""
    donnees = json.loads(texte)
    if isinstance(donnees, dict) and "personnages" in donnees:
        donnees = donnees["personnages"]
    if isinstance(donnees, dict):
        donnees = [donnees]
    sortie = []
    for i, d in enumerate(donnees):
        stats = d["stats"].get("lvl_100", d["stats"])
        manque = [s for s in STATS if s not in stats]
        if manque:
            raise ValueError(f"Perso {i + 1} : stats manquantes {manque}")
        if "kit" in d: kit = list(d["kit"])
        elif "kit_propose" in d: kit = list(d["kit_propose"])
        elif "competences" in d: kit = kit_depuis_competences(d, effets_perso)
        else: kit = []
        sortie.append(dict(nom=d.get("nom_complet", d.get("nom", f"Perso importé {i + 1}")),
                           stats={s: int(stats[s]) for s in STATS}, kit=kit))
    return sortie
