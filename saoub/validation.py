"""Diagnostic d'un perso (généré ou imaginé) : même contrôles que valider_perso du notebook 03,
mais le résultat est RENVOYÉ sous forme de rapport (dict) au lieu d'être affiché."""
from itertools import combinations

import numpy as np
import pandas as pd

from .donnees import GRILLE_100, STATS
from .moteur_kit import verifier_noms
from .moteur_stats import DISTANCE_MEDIANE, DISTANCE_P95, espace_z


def _groupe_de(moteur_kit, e):
    """Groupe de calcul d'un élément du kit ; pour un effet personnalisé sans données : celui de son modèle (ou None)."""
    if e in moteur_kit["groupe"]:
        return moteur_kit["groupe"][e]
    modele = moteur_kit["perso"].get(e, {}).get("se_comporte_comme")
    return moteur_kit["groupe"].get(modele)


def valider_perso(moteur, moteur_kit, perso, seuil_distance=DISTANCE_P95):
    """perso = {"stats": {8 stats au niveau 100}, "kit": [noms d'effets]}. Renvoie un rapport :
    stats (table), famille, plus_proche, distance, kit (table), taille, kit_proche, distance_kit, alertes (liste)."""
    ref, stats, kit = moteur["ref"], perso["stats"], list(perso["kit"])
    alertes = []
    # ---------- STATS ----------
    lignes = []
    for s in STATS:
        v = stats[s]
        lo, hi = moteur["bornes_obs"].loc["min", s], moteur["bornes_obs"].loc["max", s]
        if s in GRILLE_100: grille = "✓" if v % GRILLE_100[s] == 0 else f"✗ (pas {GRILLE_100[s]})"
        else:               grille = "✓ vue" if v in set(ref[s]) else "jamais vue"
        lignes.append(dict(stat=s, valeur=v, percentile=int(round((ref[s] <= v).mean() * 100)),
                           plage_observée="✓" if lo <= v <= hi else f"✗ ({int(lo)}-{int(hi)})", grille=grille))
        if not lo <= v <= hi: alertes.append(f"{s} = {v} hors de la plage vue chez les vrais persos ({int(lo)} à {int(hi)})")
        if grille.startswith("✗"): alertes.append(f"{s} = {v} hors grille (pas {GRILLE_100[s]}) : vrai pour 21 à 32 % des vrais persos selon la stat")
    Zref = espace_z(moteur, ref[STATS])
    D = np.sqrt(((Zref - espace_z(moteur, [stats[s] for s in STATS])) ** 2).sum(axis=1)); j = int(D.argmin())
    if D[j] == 0: alertes.append("stats identiques à un vrai perso")
    elif D[j] > seuil_distance: alertes.append(f"stats atypiques : distance {D[j]:.2f} au plus proche vrai perso (plus que 95 % des vrais)")

    # ---------- KIT ----------
    verifier_noms(moteur_kit, kit)
    G, K = moteur_kit["G"], moteur_kit["K"]
    cols = list(G.columns); Gv = G.values; N = len(Gv)
    gk = sorted({g for g in (_groupe_de(moteur_kit, e) for e in kit) if g is not None})
    sans_groupe = [e for e in kit if _groupe_de(moteur_kit, e) is None]
    x = np.zeros(len(cols), dtype=bool); x[[cols.index(g) for g in gk]] = True
    dk = 1 - (Gv & x).sum(axis=1) / np.maximum((Gv | x).sum(axis=1), 1); jk = int(dk.argmin())
    inter = Gv.astype(int) @ Gv.astype(int).T; un = Gv.sum(1)[:, None] + Gv.sum(1)[None, :] - inter
    dd = 1 - inter / np.maximum(un, 1); np.fill_diagonal(dd, 9)
    nn_ref = dd.min(axis=1)
    lignes_kit = []
    for e in kit:
        if e in moteur_kit["groupe"]:
            g = moteur_kit["groupe"][e]
            lignes_kit.append(dict(élément=e, vrais_persos_avec=int(K[e].sum()), groupe_de_calcul=g if g != e else "(lui-même)"))
        else:
            modele = moteur_kit["perso"][e].get("se_comporte_comme")
            lignes_kit.append(dict(élément=e, vrais_persos_avec=0,
                                   groupe_de_calcul=f"personnalisé, comme « {modele} »" if modele else "personnalisé, sans modèle"))
    taille = len(gk) + len(sans_groupe); tailles = G.sum(axis=1)
    nom_proche = ref.loc[G.index[jk], "nom_complet"]
    rares = [e for e in kit if e in K.columns and K[e].sum() < 10]
    if rares: alertes.append(f"effets présents chez moins de 10 vrais persos : {rares}")
    if dk[jk] == 0: alertes.append(f"kit identique (au niveau des groupes) à celui de {nom_proche}")
    elif dk[jk] > np.quantile(nn_ref, .95): alertes.append(f"kit atypique : distance {dk[jk]:.2f}, plus que 95 % des vrais kits")
    if taille > tailles.max() or taille < tailles.min(): alertes.append(f"taille de kit ({taille}) hors de ce qu'on voit chez les vrais persos")
    for a, b in combinations(gk, 2):
        na, nb, co = int(G[a].sum()), int(G[b].sum()), int((G[a] & G[b]).sum())
        if co == 0 and na * nb / N >= 3:
            alertes.append(f"« {a} » et « {b} » ne sont jamais ensemble chez les vrais persos (attendu ≈ {na * nb / N:.1f} si indépendants)")
    for ligne in lignes_kit:
        if ligne["groupe_de_calcul"].startswith("personnalisé"):
            alertes.append(f"effet nouveau « {ligne['élément']} » : aucune donnée réelle ({ligne['groupe_de_calcul']})")

    return dict(
        stats=pd.DataFrame(lignes), famille="physique" if stats["ATK"] >= stats["MATK"] else "magique",
        plus_proche=ref["nom_complet"].iloc[j], plus_proche_id=int(ref.index[j]), distance=float(D[j]),
        distance_reference=dict(mediane=DISTANCE_MEDIANE, p95=seuil_distance),
        kit=pd.DataFrame(lignes_kit), taille=taille,
        tailles_reference=dict(mediane=int(tailles.median()), min=int(tailles.min()), max=int(tailles.max()),
                               percentile=int(round((tailles <= taille).mean() * 100))),
        kit_proche=nom_proche, kit_proche_id=int(G.index[jk]), distance_kit=float(dk[jk]),
        distance_kit_reference=dict(mediane=float(np.median(nn_ref)), p95=float(np.quantile(nn_ref, .95))),
        alertes=alertes)
