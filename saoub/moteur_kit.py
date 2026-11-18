"""Moteur de kit : regroupement des effets rares, tirage séquentiel lissé et calibré (même calcul que le notebook 03).
Ajouts : les fonctions renvoient leurs messages (infos), option « diversifier », effets personnalisés."""
import difflib

import numpy as np
import pandas as pd

from .regles_effets import CATEGORIE_PERSO

SEUIL_RARE = 10      # un effet présent chez moins de 10 persos non free est regroupé avec des effets proches


def categorie_effet(e, cat_perso=None):
    if cat_perso and e in cat_perso: return cat_perso[e]          # effet personnalisé : catégorie choisie à sa création
    if e.startswith("Rôle"): return "Rôle"
    if e.startswith("Recollection Field"): return "Recollection Field"
    if " + : " in e: return "Augmentation conditionnelle"
    if e.startswith("Bonus"): return "Bonus (buff)"
    if e.startswith(("Malus", "Réduction")) and e != "Malus en contrepartie": return "Malus sur l'ennemi"
    return "Autres mécaniques"


def famille_effet(e, cat_perso=None):
    """Niveau 2 du regroupement : effets rares proches. None = pas de famille intermédiaire."""
    cat = categorie_effet(e, cat_perso)
    if cat == "Augmentation conditionnelle":
        return "Dégâts + (conditions rares)" if e.startswith("Dégâts +") else "Break/Charge + (conditions rares)"
    if cat == "Bonus (buff)":
        return "Bonus résistances (rares)" if "résistance" in e else "Bonus offensifs (rares)"
    return None


def construire_groupes(K, seuil=SEUIL_RARE, cat_perso=None):
    """Chaque effet -> un groupe : lui-même s'il est fréquent, sinon sa famille, sinon sa catégorie."""
    n = K.sum()
    groupe, rares = {}, []
    for e in K.columns:
        if n[e] >= seuil or categorie_effet(e, cat_perso) in ("Rôle", "Recollection Field"):
            groupe[e] = e
        else:
            rares.append(e)
    fam = {e: famille_effet(e, cat_perso) for e in rares}
    nfam = {f: int(K[[e for e in rares if fam[e] == f]].any(axis=1).sum()) for f in set(fam.values()) if f}
    for e in rares:
        f = fam[e]
        groupe[e] = f if (f and nfam[f] >= seuil) else "Rares : " + categorie_effet(e, cat_perso)
    return groupe


def _poids_suivant(G, deja, k, a=None, temperature=1.0):
    """Probabilité de chaque groupe d'être le prochain, sachant ce qu'on a déjà choisi (lissée vers la fréquence globale)."""
    Gv = G.values
    freq_all = Gv.mean(axis=0)
    masque = Gv[:, deja].all(axis=1) if deja else np.ones(len(Gv), dtype=bool)
    n_s = masque.sum()
    freq_s = Gv[masque].mean(axis=0) if n_s > 0 else np.zeros(Gv.shape[1])
    w = (n_s * freq_s + k * freq_all) / (n_s + k)
    if a is not None:
        w = w * a                                              # calibrage : corrige le biais du tirage sans remise
    if temperature != 1.0:
        w = np.where(w > 0, w, 0) ** (1.0 / temperature)       # température > 1 : on aplatit les probabilités
    w[deja] = 0
    return w, int(n_s)


def _generer_matrice(G, tailles, k, a, n, rng, depart=(), temperature=1.0):
    cols = G.shape[1]
    sorties = np.zeros((n, cols), dtype=bool)
    for i in range(n):
        taille = max(int(rng.choice(tailles)), len(depart)); deja = list(depart)
        while len(deja) < taille:
            w, _ = _poids_suivant(G, deja, k, a, temperature)
            if w.sum() <= 0: break
            deja.append(int(rng.choice(cols, p=w / w.sum())))
        sorties[i, deja] = True
    return sorties


def _calibrer(G, tailles, k, n=3000, iterations=8, graine=0):
    """Un poids par groupe pour que les fréquences générées égalent les fréquences réelles."""
    rng = np.random.default_rng(graine)
    cible = G.values.mean(axis=0)
    a = np.ones(G.shape[1])
    for _ in range(iterations):
        freq = _generer_matrice(G, tailles, k, a, n, rng).mean(axis=0)
        a = a * (np.clip(cible, 1e-3, None) / np.clip(freq, 1e-3, None)) ** 0.7
    return a


def _calibrer_conditionnel(moteur, r, pool, n=1500, iterations=8, graine=0):
    """Même calibrage pour une demande précise : cible = fréquences réelles (lissées) chez les persos qui ont r."""
    if not r:
        return moteur["a"]
    G, k = moteur["G"], moteur["k"]
    Gv = G.values
    masque = Gv[:, r].all(axis=1)
    n_m = int(masque.sum())
    f_all = Gv.mean(axis=0)
    f_m = Gv[masque].mean(axis=0) if n_m > 0 else f_all
    cible = (n_m * f_m + k * f_all) / (n_m + k)
    a = moteur["a"].copy()
    rng = np.random.default_rng(graine)
    for _ in range(iterations):
        freq = _generer_matrice(G, pool, k, a, n, rng, depart=r).mean(axis=0)
        maj = (np.clip(cible, 1e-3, None) / np.clip(freq, 1e-3, None)) ** 0.7
        maj[r] = 1.0
        a = a * maj
    return a


def ajuster_moteur_kit(tab, seuil=SEUIL_RARE, k_lissage=5, effets_perso=()):
    """effets_perso : registre des effets personnalisés (saoub.effets.charger_effets_perso()).
    Un effet personnalisé présent chez de vrais persos (phrases « à classer ») est appris comme les autres ;
    sinon il emprunte le profil de son effet « se comporte comme » au moment de la création."""
    base, kit = tab["base"], tab["kit"]
    perso = {e["nom"]: e for e in effets_perso}
    cat_perso = {nom: e["categorie"] for nom, e in perso.items()}
    K = kit.loc[~base["free"]]
    K = K.loc[:, K.sum() > 0]                                   # les effets que seuls les free ont disparaissent
    groupe = construire_groupes(K, seuil, cat_perso)
    noms = sorted(set(groupe.values()))
    G = pd.DataFrame({g: K[[e for e in groupe if groupe[e] == g]].any(axis=1) for g in noms})
    membres = {g: K[[e for e in groupe if groupe[e] == g]].sum() for g in noms}
    tailles = G.sum(axis=1).values
    a = _calibrer(G, tailles, k_lissage)
    return dict(K=K, G=G, groupe=groupe, membres=membres, k=k_lissage, tailles=tailles, a=a, perso=perso)


def verifier_noms(moteur, effets):
    connus = list(moteur["groupe"]) + list(moteur["perso"])
    inconnus = [e for e in effets if e not in connus]
    if inconnus:
        aide = {e: difflib.get_close_matches(e, connus, n=3, cutoff=0.4) for e in inconnus}
        raise ValueError(f"Effet inconnu (ou jamais présent chez un non-free) : {aide}")


def resoudre_imposes(moteur, imposes):
    """Traduit les effets personnalisés pour le moteur.
    Renvoie (pour_moteur, remplacements {effet emprunté: effet perso}, sans_donnees)."""
    verifier_noms(moteur, imposes)
    pour_moteur, remplacements, sans_donnees = [], {}, []
    directs = [e for e in imposes if e in moteur["groupe"]]
    for e in imposes:
        if e in moteur["groupe"]:
            pour_moteur.append(e)
            continue
        modele = moteur["perso"][e].get("se_comporte_comme")
        if modele in moteur["groupe"] and modele not in directs and modele not in remplacements:
            pour_moteur.append(modele); remplacements[modele] = e
        else:
            sans_donnees.append(e)
    return list(dict.fromkeys(pour_moteur)), remplacements, sans_donnees


def _jaccard(M):
    M = M.astype(int)
    inter = M @ M.T
    union = M.sum(1)[:, None] + M.sum(1)[None, :] - inter
    return 1 - inter / np.maximum(union, 1)


def _glouton(D, n, rng):
    """Choix « le plus loin des déjà choisis » dans une matrice de distances."""
    if len(D) <= n:
        return list(range(len(D)))
    choisis = [int(rng.integers(len(D)))]
    dmin = D[choisis[0]].copy()
    while len(choisis) < n:
        j = int(dmin.argmax()); choisis.append(j); dmin = np.minimum(dmin, D[j])
    return choisis


def proposer_kit(moteur, imposes=(), n=5, graine=0, temperature=1.0, diversifier=False, n_candidats=50):
    """Renvoie (kits, infos). imposes : effets/rôles exacts (y compris personnalisés).
    diversifier=False : exactement le tirage du notebook 03."""
    rng = np.random.default_rng(graine)
    imposes = list(imposes)
    pour_moteur, remplacements, sans_donnees = resoudre_imposes(moteur, imposes)
    G, cols = moteur["G"], list(moteur["G"].columns)
    r = [cols.index(g) for g in sorted({moteur["groupe"][e] for e in pour_moteur})]
    masque = G.values[:, r].all(axis=1) if r else np.ones(len(G), dtype=bool)
    n_match = int(masque.sum())
    pool = moteur["tailles"][masque] if n_match >= 10 else moteur["tailles"][moteur["tailles"] >= len(r)]
    if len(pool) == 0:
        pool = np.array([len(r)])
    infos = dict(n_reels=n_match, alertes=[])
    if 0 < n_match < 10:
        infos["alertes"].append(f"Seulement {n_match} vrai(s) perso(s) avec ces éléments : lissage fort vers les fréquences globales.")
    if n_match == 0 and r:
        infos["alertes"].append("Aucun vrai perso n'a tous ces éléments : combinaison jamais vue.")
    for e, modele in [(v, k) for k, v in remplacements.items()]:
        infos["alertes"].append(f"« {e} » (personnalisé) est tiré comme « {modele} » : aucune donnée réelle.")
    for e in sans_donnees:
        infos["alertes"].append(f"« {e} » (personnalisé) n'influence pas le reste du kit : aucune donnée réelle.")
    a_q = _calibrer_conditionnel(moteur, r, pool)

    kits, vecteurs = [], []
    for _ in range(max(n, n_candidats) if diversifier else n):
        taille = max(int(rng.choice(pool)) - len(sans_donnees), len(r))   # un effet sans données compte dans la taille
        deja = list(r)
        while len(deja) < taille:
            w, _ = _poids_suivant(G, deja, moteur["k"], a_q, temperature)
            if w.sum() <= 0: break
            deja.append(int(rng.choice(len(cols), p=w / w.sum())))
        kit = set(pour_moteur)
        for j in deja:
            g = cols[j]
            if any(moteur["groupe"][e] == g for e in pour_moteur):
                continue                                      # groupe déjà couvert par un effet imposé
            m = moteur["membres"][g]; m = m[m > 0]
            kit.add(str(rng.choice(m.index, p=(m / m.sum()).values)))
        kit = {remplacements.get(e, e) for e in kit} | set(sans_donnees)
        kits.append(sorted(kit))
        v = np.zeros(len(cols), dtype=bool); v[deja] = True; vecteurs.append(v)
    if diversifier:
        kits = [kits[i] for i in _glouton(_jaccard(np.array(vecteurs)), n, rng)]
    return kits, infos


def lister_effets(moteur):
    """Noms utilisables, avec effectif chez les non-free, groupe de calcul et catégorie (effets personnalisés à la fin)."""
    n = moteur["K"].sum()
    cat_perso = {nom: e["categorie"] for nom, e in moteur["perso"].items()}
    t = pd.DataFrame({"effet": n.index, "persos": n.values, "groupe": [moteur["groupe"][e] for e in n.index]})
    t["catégorie"] = t["effet"].map(lambda e: categorie_effet(e, cat_perso))
    t = t.sort_values(["catégorie", "persos"], ascending=[True, False])
    sans = [dict(effet=nom, persos=0, groupe=f"comme : {e.get('se_comporte_comme') or 'aucun'}", catégorie=CATEGORIE_PERSO)
            for nom, e in moteur["perso"].items() if nom not in n.index]
    return pd.concat([t, pd.DataFrame(sans)], ignore_index=True) if sans else t.reset_index(drop=True)


def valider_moteur_kit(moteur, n=3000, graine=1):
    """Sans contrainte : les kits générés ressemblent-ils aux kits réels ? (au niveau des groupes)"""
    rng = np.random.default_rng(graine)
    G, cols = moteur["G"], list(moteur["G"].columns)
    Gen = pd.DataFrame(_generer_matrice(G, moteur["tailles"], moteur["k"], moteur["a"], n, rng), columns=cols)
    f_r, f_g = G.mean(), Gen.mean()
    cr, cg = G.astype(float).corr().values, Gen.astype(float).corr().values
    iu = np.triu_indices(len(cols), 1)
    reels = {tuple(x) for x in G.values.astype(int)}
    return dict(ecart_freq_moyen=float(np.abs(f_r - f_g).mean() * 100), ecart_freq_max=float(np.abs(f_r - f_g).max() * 100),
                corr_liens=float(np.corrcoef(np.nan_to_num(cr)[iu], np.nan_to_num(cg)[iu])[0, 1]),
                taille_reelle=float(G.sum(axis=1).mean()), taille_generee=float(Gen.sum(axis=1).mean()),
                copies=float(np.mean([tuple(x) in reels for x in Gen.values.astype(int)])))


def verifier_conditionnel(moteur, imposes, n=2000, graine=2):
    """Quand on impose des effets, les AUTRES éléments bougent-ils comme chez les vrais persos qui les ont ?
    Renvoie (n_reels, corrélation des écarts ou None si < 10 persos, table)."""
    rng = np.random.default_rng(graine)
    pour_moteur, _, _ = resoudre_imposes(moteur, imposes)
    G, cols = moteur["G"], list(moteur["G"].columns)
    r = [cols.index(g) for g in sorted({moteur["groupe"][e] for e in pour_moteur})]
    masque = G.values[:, r].all(axis=1)
    pool = moteur["tailles"][masque] if masque.sum() >= 10 else moteur["tailles"][moteur["tailles"] >= len(r)]
    a_q = _calibrer_conditionnel(moteur, r, pool)
    gen = pd.DataFrame(_generer_matrice(G, pool, moteur["k"], a_q, n, rng, depart=r), columns=cols)
    t = pd.DataFrame({"global %": G.mean() * 100, "réel (avec) %": G[masque].mean() * 100, "généré %": gen.mean() * 100})
    t = t.drop(index=[cols[j] for j in r])
    ecart_r, ecart_g = t["réel (avec) %"] - t["global %"], t["généré %"] - t["global %"]
    corr = float(ecart_r.corr(ecart_g)) if masque.sum() >= 10 else None
    return int(masque.sum()), corr, t.reindex(ecart_r.abs().sort_values(ascending=False).index)
