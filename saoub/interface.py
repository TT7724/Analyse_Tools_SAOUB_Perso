"""Traduction des choix de l'interface (listes déroulantes) en paramètres des moteurs. Sans Streamlit : testable."""
import json

from .donnees import STATS

# Choix proposés pour chaque stat -> règle du moteur (percentiles calculés sur les 181 persos non free)
NIVEAUX_STAT = {
    "Libre": {},
    "Très bas (20 % les plus bas)": {"pct_max": 20},
    "Bas (40 % les plus bas)": {"pct_max": 40},
    "Moyen (entre 30 % et 70 %)": {"pct_min": 30, "pct_max": 70},
    "Haut (40 % les plus hauts)": {"pct_min": 60},
    "Très haut (20 % les plus hauts)": {"pct_min": 80},
    "Valeur exacte…": None,       # complété par un champ numérique
    "Fourchette…": None,          # complété par deux champs numériques
}

FAMILLES = {"Au choix du moteur": None, "Physique (ATK ≥ MATK)": "physique", "Magique (MATK > ATK)": "magique"}

ORIGINALITE = {
    "Classique": dict(temperature_stats=1.0, distance_min=None, temperature_kit=1.0),
    "Original": dict(temperature_stats=1.0, distance_min=0.6, temperature_kit=1.5),
    "Audacieux": dict(temperature_stats=1.3, distance_min=None, temperature_kit=1.5),
}


def contraintes_depuis_choix(famille, choix_stats):
    """famille : clé de FAMILLES. choix_stats : {stat: {"niveau": clé de NIVEAUX_STAT, "egal"/"min"/"max": valeurs}}."""
    contraintes = {}
    if FAMILLES[famille]:
        contraintes["famille"] = FAMILLES[famille]
    for s in STATS:
        c = choix_stats.get(s, {"niveau": "Libre"})
        niveau = c["niveau"]
        if niveau == "Valeur exacte…":
            contraintes[s] = {"egal": c["egal"]}
        elif niveau == "Fourchette…":
            contraintes[s] = {"min": min(c["min"], c["max"]), "max": max(c["min"], c["max"])}
        elif NIVEAUX_STAT[niveau]:
            contraintes[s] = dict(NIVEAUX_STAT[niveau])
    return contraintes


def cle_params(params):
    """Texte unique pour un jeu de paramètres (sert de clé de cache et d'historique)."""
    return json.dumps(params, sort_keys=True, ensure_ascii=False)


def resume(params, graine):
    """Une ligne lisible pour l'historique."""
    morceaux = []
    for cle, regle in params["contraintes"].items():
        if cle == "famille":
            morceaux.append(regle)
        elif "egal" in regle:
            morceaux.append(f"{cle} = {regle['egal']:g}")
        elif "min" in regle:
            morceaux.append(f"{cle} {regle['min']:g}–{regle['max']:g}")
        else:
            nom = next(k for k, v in NIVEAUX_STAT.items() if v == regle)
            morceaux.append(f"{cle} {nom.split(' (')[0].lower()}")
    stats = ", ".join(morceaux) or "stats libres"
    kit = ", ".join(params["imposes"]) or "kit libre"
    return f"graine {graine} · {stats} · {kit} · {params['originalite'].lower()}"


def lecture_distance(d, mediane=0.41, p95=0.78):
    if d == 0: return "copie exacte d'un vrai perso"
    if d <= mediane: return "très proche d'un vrai perso (typique)"
    if d <= p95: return "ressemble aux vrais persos, avec sa personnalité"
    return "atypique : plus éloigné que 95 % des vrais persos entre eux"
