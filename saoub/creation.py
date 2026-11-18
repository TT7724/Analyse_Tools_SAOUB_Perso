"""Assemblage : charge tout ce qu'il faut, puis crée des persos complets (stats + kit)."""
from .donnees import STATS, charger_persos, preparer_table
from .effets import charger_effets_perso, construire_effets
from .moteur_kit import ajuster_moteur_kit, proposer_kit
from .moteur_stats import ajuster_moteur_stats, proposer_stats


def preparer_tout(chemin_json=None, chemin_effets_perso=None, niveau=100):
    """Tout ce dont l'application a besoin, en un appel (≈ 5 s, à mettre en cache dans l'application)."""
    persos = charger_persos(chemin_json) if chemin_json else charger_persos()
    effets_perso = charger_effets_perso(chemin_effets_perso) if chemin_effets_perso else charger_effets_perso()
    df_eff = construire_effets(persos, effets_perso=effets_perso)
    tab = preparer_table(persos, df_eff, niveau)
    return dict(persos=persos, effets_perso=effets_perso, df_eff=df_eff, tab=tab,
                moteur=ajuster_moteur_stats(tab), moteur_kit=ajuster_moteur_kit(tab, effets_perso=effets_perso))


def creer_persos(moteur, moteur_kit, contraintes_stats=None, imposes_kit=(), n=5, graine=0,
                 temperature_stats=1.0, distance_min=None, temperature_kit=1.0, diversifier=False):
    """Stats et kit sont tirés indépendamment (comme dans les vraies données).
    Renvoie (persos, infos) : persos = liste de {"stats": {...}, "kit": [...]}, infos = {"stats": ..., "kit": ...}."""
    df, infos_stats = proposer_stats(moteur, contraintes_stats, n=n, graine=graine, temperature=temperature_stats,
                                     distance_min=distance_min, diversifier=diversifier)
    kits, infos_kit = proposer_kit(moteur_kit, imposes_kit, n=n, graine=graine, temperature=temperature_kit,
                                   diversifier=diversifier)
    persos = [dict(stats={s: int(df.loc[i, s]) for s in STATS}, kit=list(kits[i])) for i in range(min(len(df), len(kits)))]
    return persos, dict(stats=infos_stats, kit=infos_kit, proches=df[["plus_proche", "distance"]])
