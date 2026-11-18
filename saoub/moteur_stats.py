"""Moteur de stats (niveau 100) : une loi normale à 8 dimensions par famille, apprise sur les non-free.
Même calcul que le notebook 03. Différence : les fonctions RENVOIENT leurs messages (dict « infos »)
au lieu de les afficher avec print, pour que l'application puisse les montrer où elle veut."""
import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal

from .donnees import GRILLE_100, STATS

STATS_MENU = ["MP", "CRIT", "SPD"]            # pas de grille : on choisit parmi les valeurs déjà vues
DISTANCE_MEDIANE, DISTANCE_P95 = 0.41, 0.78   # plus proche voisin entre vrais persos (référence)


def ajuster_moteur_stats(tab):
    ref = tab["base"][~tab["base"]["free"]]
    modeles = {}
    for fam, groupe in ref.groupby("famille"):
        modeles[fam] = dict(moy=groupe[STATS].mean().values, cov=np.cov(groupe[STATS].values, rowvar=False),
                            poids=len(groupe) / len(ref), n=len(groupe))
    return dict(ref=ref, modeles=modeles, menus={s: np.sort(ref[s].unique()) for s in STATS_MENU},
                bornes_obs=ref[STATS].agg(["min", "max"]), moy=ref[STATS].mean(), std=ref[STATS].std(ddof=0))


def arrondir_stats(moteur, X):
    X = X.copy()
    for j, s in enumerate(STATS):
        if s in GRILLE_100:
            X[:, j] = np.round(X[:, j] / GRILLE_100[s]) * GRILLE_100[s]
        else:
            menu = moteur["menus"][s]
            X[:, j] = menu[np.abs(X[:, [j]] - menu[None, :]).argmin(axis=1)]
    return X


def espace_z(moteur, valeurs):
    """Stats centrées-réduites divisées par √8 : l'échelle de toutes les distances de l'outil."""
    return ((np.asarray(valeurs, dtype=float) - moteur["moy"].values) / moteur["std"].values) / np.sqrt(len(STATS))


def lire_contraintes(moteur, contraintes):
    """contraintes = {"ATK": {"egal": 2800}, "SPD": {"pct_min": 80}, "HP": {"min": 7500, "max": 8500}, "famille": "physique"}
    Renvoie (bornes, famille, messages). Lève ValueError si les contraintes sont invalides."""
    ref = moteur["ref"]
    bornes, famille, messages = {}, None, []
    for cle, regle in (contraintes or {}).items():
        if cle == "famille":
            if regle not in ("physique", "magique"):
                raise ValueError("famille doit valoir 'physique' ou 'magique'")
            famille = regle
            continue
        if cle not in STATS:
            raise ValueError(f"stat inconnue : {cle} (attendu : {STATS} ou 'famille')")
        b = dict(egal=None, min=-np.inf, max=np.inf)
        for mot, v in regle.items():
            if mot == "egal":      b["egal"] = float(v)
            elif mot == "min":     b["min"] = max(b["min"], float(v))
            elif mot == "max":     b["max"] = min(b["max"], float(v))
            elif mot == "pct_min": b["min"] = max(b["min"], np.percentile(ref[cle], v))
            elif mot == "pct_max": b["max"] = min(b["max"], np.percentile(ref[cle], v))
            else: raise ValueError(f"{cle} : règle inconnue « {mot} » (egal, min, max, pct_min, pct_max)")
        if b["egal"] is not None and cle in GRILLE_100:
            pas = GRILLE_100[cle]
            arrondi = round(b["egal"] / pas) * pas
            if arrondi != b["egal"]:
                messages.append(f"{cle} = {b['egal']:.0f} n'est pas sur la grille (pas {pas}) : arrondi à {arrondi:.0f}")
            b["egal"] = float(arrondi)
        if b["min"] > b["max"] or (b["egal"] is not None and not b["min"] <= b["egal"] <= b["max"]):
            raise ValueError(f"{cle} : contraintes contradictoires {regle}")
        bornes[cle] = b
    if len([s for s in bornes if bornes[s]["egal"] is not None]) >= len(STATS):
        raise ValueError("Laisse au moins une stat libre.")
    return bornes, famille, messages


def _reels_conformes(moteur, bornes, famille):
    """Nombre de VRAIS persos non free qui respectent déjà les contraintes (« egal » = à un pas près)."""
    ref = moteur["ref"]
    ok = pd.Series(True, index=ref.index)
    for s, b in bornes.items():
        tol = GRILLE_100.get(s, moteur["std"][s] * 0.1)
        if b["egal"] is not None:
            ok &= (ref[s] - b["egal"]).abs() <= tol
        ok &= (ref[s] >= b["min"]) & (ref[s] <= b["max"])
    if famille:
        ok &= ref["famille"] == famille
    return int(ok.sum())


def _tirer(moteur, bornes, famille, n_tirages, rng, temperature=1.0):
    idx = {s: i for i, s in enumerate(STATS)}
    fixes = [idx[s] for s, b in bornes.items() if b["egal"] is not None]
    libres = [i for i in range(len(STATS)) if i not in fixes]
    xf = np.array([bornes[STATS[i]]["egal"] for i in fixes])
    familles = [famille] if famille else list(moteur["modeles"])
    cond, logw = {}, []
    for fam in familles:
        m = moteur["modeles"][fam]
        moy, cov = m["moy"], m["cov"]
        if fixes:                                       # conditionnement gaussien (complément de Schur)
            Sff, Srf, Srr = cov[np.ix_(fixes, fixes)], cov[np.ix_(libres, fixes)], cov[np.ix_(libres, libres)]
            K = Srf @ np.linalg.inv(Sff)
            cond[fam] = (moy[libres] + K @ (xf - moy[fixes]), Srr - K @ Srf.T)
            logw.append(np.log(m["poids"]) + multivariate_normal(moy[fixes], Sff).logpdf(xf))
        else:
            cond[fam] = (moy, cov)
            logw.append(np.log(m["poids"]))
    w = np.exp(np.array(logw) - max(logw)); w /= w.sum()
    choix = rng.choice(len(familles), size=n_tirages, p=w)
    X = np.zeros((n_tirages, len(STATS)))
    fam_tiree = np.empty(n_tirages, dtype=object)
    for k, fam in enumerate(familles):
        masque = choix == k
        mu, sigma = cond[fam]
        X[np.ix_(masque, libres)] = rng.multivariate_normal(mu, sigma * temperature ** 2, size=int(masque.sum()))
        fam_tiree[masque] = fam
    if fixes:
        X[:, fixes] = xf
    return X, fam_tiree


def choisir_divers(Z, n, rng):
    """Choix glouton « le plus loin des déjà choisis » : renvoie n indices de lignes de Z, bien espacés."""
    if len(Z) <= n:
        return list(range(len(Z)))
    choisis = [int(rng.integers(len(Z)))]
    dmin = np.sqrt(((Z - Z[choisis[0]]) ** 2).sum(axis=1))
    while len(choisis) < n:
        j = int(dmin.argmax())
        choisis.append(j)
        dmin = np.minimum(dmin, np.sqrt(((Z - Z[j]) ** 2).sum(axis=1)))
    return choisis


def proposer_stats(moteur, contraintes=None, n=5, graine=0, n_tirages=20000, temperature=1.0, distance_min=None,
                   diversifier=False, n_candidats=200):
    """Renvoie (res, infos). res : n persos (8 stats, famille, plus_proche, distance).
    diversifier=False : exactement le tirage du notebook 03. True : parmi n_candidats tirages acceptés,
    on garde les n les plus différents entre eux."""
    rng = np.random.default_rng(graine)
    bornes, famille, messages = lire_contraintes(moteur, contraintes)
    n_reels = _reels_conformes(moteur, bornes, famille)
    X, fam_tiree = _tirer(moteur, bornes, famille, n_tirages, rng, temperature)
    X = arrondir_stats(moteur, X)
    marge = max(temperature - 1, 0) * moteur["std"]          # température > 1 : on tolère un peu au-delà des plages

    ok = np.ones(n_tirages, dtype=bool)
    for j, s in enumerate(STATS):
        b = bornes.get(s)
        if b is not None and b["egal"] is not None:
            continue
        ok &= (X[:, j] >= moteur["bornes_obs"].loc["min", s] - marge[s]) & (X[:, j] <= moteur["bornes_obs"].loc["max", s] + marge[s])
        if b is not None:
            ok &= (X[:, j] >= b["min"]) & (X[:, j] <= b["max"])
    fam_obs = np.where(X[:, STATS.index("ATK")] >= X[:, STATS.index("MATK")], "physique", "magique")
    ok &= fam_obs == fam_tiree
    if famille:
        ok &= fam_obs == famille

    Zref = espace_z(moteur, moteur["ref"][STATS])
    if distance_min is not None:
        idx_ok = np.flatnonzero(ok)
        Zc = espace_z(moteur, X[idx_ok])
        dmin = np.sqrt(((Zc[:, None, :] - Zref[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
        ok[idx_ok[dmin < distance_min]] = False
    infos = dict(acceptes=int(ok.sum()), n_tirages=n_tirages, taux=float(ok.mean()), n_reels=n_reels,
                 messages=messages, alertes=[])
    if n_reels < 10:
        infos["alertes"].append(f"Seulement {n_reels} vrai(s) perso(s) respecte(nt) déjà ces contraintes : "
                                "la proposition s'appuie surtout sur le modèle, pas sur des exemples.")
    uniques = np.unique(X[ok], axis=0)
    if len(uniques) == 0:
        raise ValueError("Aucun tirage ne respecte ces contraintes : relâche-en une (ou élargis un min/max).")
    if diversifier:
        candidats = uniques[rng.permutation(len(uniques))[:n_candidats]]
        if temperature <= 1:
            # Choisir « le plus loin des autres » pousse vers les extrêmes : sans température, on ne garde que
            # des candidats aussi proches d'un vrai perso que 95 % des vrais persos entre eux (≤ 0,78).
            Zc = espace_z(moteur, candidats)
            dmin = np.sqrt(((Zc[:, None, :] - Zref[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
            if (dmin <= DISTANCE_P95).sum() >= n:
                candidats = candidats[dmin <= DISTANCE_P95]
        choisis = candidats[choisir_divers(espace_z(moteur, candidats), n, rng)]
    else:
        choisis = uniques[rng.permutation(len(uniques))[:n]]

    res = pd.DataFrame(choisis, columns=STATS).astype(int)
    res["famille"] = np.where(res["ATK"] >= res["MATK"], "physique", "magique")
    D = np.sqrt(((espace_z(moteur, res[STATS])[:, None, :] - Zref[None, :, :]) ** 2).sum(axis=2))
    res["plus_proche"] = moteur["ref"]["nom_complet"].values[D.argmin(axis=1)]
    res["distance"] = D.min(axis=1).round(3)
    return res, infos


def percentiles_stats(moteur, res):
    """Rang percentile (0-100) de chaque stat par rapport aux persos non free."""
    ref = moteur["ref"]
    return pd.DataFrame({s: [(ref[s] <= v).mean() * 100 for v in res[s]] for s in STATS},
                        index=res.index).round(0).astype(int)


def valider_moteur_stats(moteur, n=5000, graine=1):
    """Sans contrainte : les stats générées ressemblent-elles aux stats réelles ? Renvoie un dict de résultats."""
    rng = np.random.default_rng(graine)
    ref = moteur["ref"]
    X, _ = _tirer(moteur, {}, None, n, rng)
    X = arrondir_stats(moteur, X)
    dans = np.all((X >= moteur["bornes_obs"].loc["min"].values) & (X <= moteur["bornes_obs"].loc["max"].values), axis=1)
    gen = pd.DataFrame(X[dans], columns=STATS)
    diff = (gen.corr() - ref[STATS].corr()).abs().values
    Zr, Zg = espace_z(moteur, ref[STATS]), espace_z(moteur, gen[STATS].iloc[:1000])
    Dgr = np.sqrt(((Zg[:, None, :] - Zr[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    Drr = np.sqrt(((Zr[:, None, :] - Zr[None, :, :]) ** 2).sum(axis=2)); np.fill_diagonal(Drr, np.inf)
    return dict(
        gardes=len(gen), n=n,
        moyennes=pd.DataFrame({"moy réel": ref[STATS].mean(), "moy généré": gen.mean(),
                               "écart-type réel": ref[STATS].std(), "écart-type généré": gen.std()}).round(0).astype(int),
        ecart_corr_moyen=float(diff[np.triu_indices(8, 1)].mean()), ecart_corr_max=float(diff.max()),
        part_physiques_reel=float((ref["famille"] == "physique").mean()), part_physiques_genere=float((gen["ATK"] >= gen["MATK"]).mean()),
        distance_generee=float(np.median(Dgr)), distance_reelle=float(np.median(Drr.min(axis=1))),
        copies=float(np.mean([(ref[STATS].values == row).all(axis=1).any() for row in gen[STATS].values[:1000]])))
