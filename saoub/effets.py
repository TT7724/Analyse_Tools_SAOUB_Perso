"""Table des effets en Python pur (même résultat que construire_effets du notebook 03, vérifié par les tests)
et registre des effets personnalisés (data/effets_personnalises.json)."""
import json
import os
import re
from datetime import date

import pandas as pd

from .donnees import RACINE
from .regles_effets import (BONUS, BOOST_DEGATS, CATEGORIES, EST_BONUS, EST_BOOST, EXCLUS, REGLES, RF_VALEUR,
                            SLOTS_TOUS, SPLIT)

CHEMIN_EFFETS_PERSO = RACINE / "data" / "effets_personnalises.json"
ROLES = ["Rôle Break", "Rôle Charge", "Rôle Mode enhance"]
CATEGORIES_CREABLES = [c for c in CATEGORIES if c not in ("Rôle", "Recollection Field")]


# ----------------------------------------------------------------------------------------------
# 1. Reconnaissance des effets dans une phrase
# ----------------------------------------------------------------------------------------------
def normaliser(texte):
    """Rend deux phrases comparables : nombres -> N, durées et intensités retirées, espaces nettoyés."""
    t = texte.replace("’", "'")
    t = re.sub(r"tour\(s\)", "tours", t)
    t = re.sub(r"\s*\([^()]*(tours|maximum)[^()]*\)", "", t)
    t = re.sub(r"\s*\((faible|moyenne|forte|énorme)\)", "", t)
    t = re.sub(r"\d+(,\d+)?", "N", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[\s.,;]+$", "", t)
    return t.strip()


def _condition(p):
    if "subissant des dégâts continus" in p: return "ennemi en dégâts continus"
    if "subissant un malus de résistance" in p:
        m = re.search(r"malus de résistance\s*(.*)$", p)
        return "ennemi avec malus de résistance " + (m.group(1) if m else "")
    if "Recollection Field" in p: return "Recollection Field atteint un seuil"
    if "lien de compétences" in p: return "lien de compétences"
    if "nombre de cibles" in p: return "nombre de cibles"
    if re.search(r"Volonté de l'ennemi (dépasse|est de N% ou plus)", p): return "Volonté ennemie au-dessus d'un seuil"
    if re.search(r"(quand|lorsque) le bonus", p): return "bonus d'ATK ou de critique atteint un seuil"
    return "autre condition"


def etiquettes(phrase, p):
    """Liste des effets d'une phrase (phrase = texte d'origine, p = texte normalisé). [« Autre »] si rien n'est reconnu."""
    cherche = lambda motif: re.search(motif, p) is not None
    out = []
    est_rf = cherche(r"^Recollection Field")
    if est_rf:                                              # la valeur (+1, +2, +3) se lit dans le texte d'origine
        m = re.search(RF_VALEUR, phrase)
        valeur = m.group(1) if m else ""
        out.append(("Recollection Field spécial +" if cherche(r"^Recollection Field spécial") else "Recollection Field +") + valeur)
    est_boost = not est_rf and cherche(EST_BOOST)
    if est_boost:
        quoi = ("Dégâts" if cherche(BOOST_DEGATS) else
                "Charge de Volonté" if cherche(r"[Aa]ugmentation de la Charge") else "Break de Volonté")
        out.append(f"{quoi} + : {_condition(p)}")
    out += [nom for motif, nom in REGLES if cherche(motif)]
    if not est_boost and not est_rf and cherche(EST_BONUS):
        cible = " (soi-même)" if "soi-même" in p else (" (alliés)" if cherche("alliés?") else " (cible non précisée)")
        out += [nom + cible for motif, nom in BONUS if cherche(motif)]
    return out or ["Autre"]


# ----------------------------------------------------------------------------------------------
# 2. Table des effets : une ligne par (perso, compétence, effet)
# ----------------------------------------------------------------------------------------------
def construire_effets(persos, slots=SLOTS_TOUS, effets_perso=()):
    """Colonnes : perso_id, element, slot, phrase, p, effet. On lit la description du niveau max de chaque slot.
    effets_perso : registre des effets personnalisés. Une phrase « Autre » dont le texte normalisé figure dans
    les « phrases » d'un effet personnalisé reçoit le nom de cet effet (les 59 effets existants ne changent pas)."""
    phrase_vers_perso = {ph: e["nom"] for e in effets_perso for ph in e.get("phrases", [])}
    lignes = []
    for perso in persos:
        for slot in slots:
            niveaux = perso["competences"][slot]["niveaux"]
            description = (niveaux[-1].get("description") or "").strip() if niveaux else ""
            for phrase in re.split(SPLIT, description):
                p = normaliser(phrase)
                if re.search(EXCLUS, p):
                    continue
                effets = etiquettes(phrase, p)
                if effets == ["Autre"] and p in phrase_vers_perso:
                    effets = [phrase_vers_perso[p]]
                lignes += [dict(perso_id=perso["id"], element=perso["element"], slot=slot, phrase=phrase, p=p, effet=e)
                           for e in effets]
    return pd.DataFrame(lignes, columns=["perso_id", "element", "slot", "phrase", "p", "effet"])


def phrases_a_classer(df_eff, persos=None):
    """Phrases qu'aucune règle ne reconnaît (« Autre »), regroupées par texte normalisé, avec le nombre de persos."""
    autres = df_eff[df_eff["effet"] == "Autre"]
    if autres.empty:
        return pd.DataFrame(columns=["p", "nb_persos", "exemple", "persos"])
    noms = {x["id"]: x["nom_complet"] for x in persos} if persos else {}
    t = (autres.groupby("p")
         .agg(nb_persos=("perso_id", "nunique"), exemple=("phrase", "first"),
              persos=("perso_id", lambda ids: ", ".join(sorted({str(noms.get(i, i)) for i in ids}))))
         .reset_index().sort_values("nb_persos", ascending=False))
    return t.reset_index(drop=True)


# ----------------------------------------------------------------------------------------------
# 3. Registre des effets personnalisés (fichier JSON relu à chaque démarrage)
# ----------------------------------------------------------------------------------------------
def charger_effets_perso(chemin=CHEMIN_EFFETS_PERSO):
    if not os.path.exists(chemin):
        return []
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)["effets"]


def _enregistrer(effets, chemin):
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    temporaire = f"{chemin}.tmp"                    # écriture dans un fichier temporaire puis remplacement :
    with open(temporaire, "w", encoding="utf-8") as f:   # un plantage en cours d'écriture n'abîme pas le registre
        json.dump({"effets": effets}, f, ensure_ascii=False, indent=2)
    os.replace(temporaire, chemin)


def ajouter_effet_perso(nom, categorie, effets_connus, se_comporte_comme=None, description="", phrases=(),
                        chemin=CHEMIN_EFFETS_PERSO):
    """Ajoute un effet au registre et renvoie le registre à jour. Lève ValueError avec un message clair si besoin.
    effets_connus : noms déjà utilisés (effets du jeu + rôles), pour éviter les doublons."""
    nom = " ".join(str(nom).split())
    effets = charger_effets_perso(chemin)
    deja = set(effets_connus) | {e["nom"] for e in effets}
    if not nom:
        raise ValueError("Donne un nom à l'effet.")
    if nom.casefold() in {x.casefold() for x in deja} or nom == "Autre":
        raise ValueError(f"Le nom « {nom} » existe déjà.")
    if categorie not in CATEGORIES_CREABLES:
        raise ValueError(f"Catégorie inconnue : {categorie} (attendu : {CATEGORIES_CREABLES})")
    if se_comporte_comme is not None and se_comporte_comme not in set(effets_connus):
        raise ValueError(f"« Se comporte comme » doit être un effet existant du jeu : {se_comporte_comme}")
    effets.append(dict(nom=nom, categorie=categorie, se_comporte_comme=se_comporte_comme,
                       description=description.strip(), phrases=sorted(set(phrases)),
                       cree_le=date.today().isoformat()))
    _enregistrer(effets, chemin)
    return effets


def supprimer_effet_perso(nom, chemin=CHEMIN_EFFETS_PERSO):
    effets = [e for e in charger_effets_perso(chemin) if e["nom"] != nom]
    _enregistrer(effets, chemin)
    return effets


def liste_effets(df_eff, effets_perso=()):
    """Tous les noms pour les listes déroulantes : rôles, effets du jeu, puis effets personnalisés (groupe à part)."""
    du_jeu = sorted(set(df_eff["effet"]) - {"Autre"} - {e["nom"] for e in effets_perso})
    return dict(jeu=ROLES + du_jeu, personnalise=[e["nom"] for e in effets_perso])
