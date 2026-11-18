"""Analyses avancées du notebook 01, en Plotly : voisins, dendrogramme, carte 2D (ACP), offre/demande d'états,
complexité du kit, triangles de budget. Mêmes calculs que le notebook ; chaque fonction renvoie (figure(s), tableau(x))."""
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.cluster.hierarchy import cophenet, dendrogram, fcluster, linkage
from scipy.spatial.distance import pdist, squareform
from scipy.stats import spearmanr

from .donnees import STATS
from .graphiques import AQUA, BLEU, COUL_FAMILLE, DIVERGENT, GRIS, JAUNE, MAGENTA, ORANGE, ROUGE, VERT, _figure

PALETTE = [BLEU, ORANGE, AQUA, JAUNE, MAGENTA, VERT, "#6250d6", ROUGE]       # ordre fixe (8 couleurs max)
ROLES = ["Rôle Break", "Rôle Charge", "Rôle Mode enhance"]


# ============================================================================================== voisins / groupes
def kit_par_slots(kit_complet, df_eff, slots, index):
    """Kit 0/1 : rôles (toujours) + effets lus dans les compétences choisies. Une ligne par perso de index."""
    eff = df_eff[df_eff["slot"].isin(slots) & (df_eff["effet"] != "Autre")]
    effets = (pd.crosstab(eff["perso_id"], eff["effet"]) > 0).reindex(index, fill_value=False)
    return pd.concat([kit_complet.loc[index, ROLES], effets], axis=1).astype(bool)


def construire_espace(t, kit, poids_stats=0.5):
    """Chaque perso = stats centrées-réduites + kit 0/1 (centré, mis à l'échelle). poids_stats : 1 = stats seules, 0 = kit seul."""
    kit = kit.loc[t.index]
    kit = kit.loc[:, kit.std(ddof=0) > 0].astype(float)                  # on garde les éléments qui varient
    moy, std = t[STATS].mean(), t[STATS].std(ddof=0)
    Z = (t[STATS] - moy) / std
    moy_k = kit.mean(); ech_k = np.sqrt(((kit - moy_k) ** 2).mean().sum())
    X = np.hstack([np.sqrt(poids_stats) * Z.values / np.sqrt(len(STATS)),
                   np.sqrt(1 - poids_stats) * ((kit - moy_k) / ech_k).values])
    D = squareform(pdist(X))
    iu = np.triu_indices(len(X), 1)
    plus_proche = (D + np.eye(len(X)) * 1e9).min(axis=1)
    return dict(base=t, Z=Z, kit=kit, X=X, D=D, w=poids_stats, med_paires=float(np.median(D[iu])),
                med_nn=float(np.median(plus_proche)))


def fig_voisins(esp, perso_id, k=5):
    """Les k persos les plus proches d'un perso (stats + kit selon le poids choisi)."""
    base, kit = esp["base"], esp["kit"]
    i = list(base.index).index(perso_id)
    dist = esp["D"][i].copy(); dist[i] = np.inf
    ordre = np.argsort(dist)[:k]
    v = kit.values[i]
    lignes = []
    for j in ordre:
        communs = [c for c, a, b in zip(kit.columns, kit.values[j], v) if a == 1 and b == 1]
        lignes.append({"voisin": base["nom_complet"].iloc[j], "distance": round(float(dist[j]), 3),
                       "écart de stats (écarts-types)": round(float(np.linalg.norm(esp["Z"].values[j] - esp["Z"].values[i])), 2),
                       "effets différents": int((kit.values[j] != v).sum()),
                       "en commun": ", ".join(communs[:4]) + (" …" if len(communs) > 4 else "")})
    t = pd.DataFrame(lignes)
    fig = go.Figure(go.Bar(y=t["voisin"], x=t["distance"], orientation="h", marker_color=BLEU,
                           customdata=t[["écart de stats (écarts-types)", "effets différents"]],
                           hovertemplate="%{y}<br>distance %{x:.2f}<br>stats : %{customdata[0]} écart(s)-type(s)"
                                         "<br>%{customdata[1]} effet(s) différent(s)<extra></extra>"))
    fig.add_vline(x=esp["med_nn"], line=dict(color=VERT, dash="dot"), annotation_text="voisin typique",
                  annotation_position="top")
    fig.add_vline(x=esp["med_paires"], line=dict(color=ROUGE, dash="dash"), annotation_text="2 persos au hasard",
                  annotation_position="top")
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(title="distance (court = ressemblant)",
                                                                   range=[0, esp["med_paires"] * 1.35]))
    return _figure(fig, f"Les {k} persos les plus proches de {base.loc[perso_id, 'nom_complet']}", 140 + 50 * k), t


def fig_dendrogramme(esp, n_groupes=8):
    """Arbre de regroupement (Ward) tronqué à n_groupes ; tableau de description des groupes ; groupe de chaque perso."""
    L = linkage(esp["X"], "ward")
    coph = float(cophenet(L, pdist(esp["X"]))[0])
    etiquettes = fcluster(L, n_groupes, "maxclust")
    tailles = pd.Series(etiquettes).value_counts()
    nom_groupe = {g: f"G{r + 1}" for r, g in enumerate(tailles.index)}        # G1 = le plus gros groupe
    d = dendrogram(L, truncate_mode="lastp", p=n_groupes, no_plot=True)
    # nom des feuilles : groupe et taille (les feuilles tronquées regroupent exactement un groupe fcluster)
    feuilles = []
    for f in d["leaves"]:
        membres = [f] if f < len(esp["X"]) else _membres(L, f, len(esp["X"]))
        feuilles.append(f"{nom_groupe[etiquettes[membres[0]]]} ({len(membres)})")
    fig = go.Figure()
    for xs, ys in zip(d["icoord"], d["dcoord"]):
        fig.add_scatter(x=xs, y=ys, mode="lines", line=dict(color=BLEU, width=2), hoverinfo="skip", showlegend=False)
    fig.update_layout(xaxis=dict(tickvals=[5 + 10 * i for i in range(len(feuilles))], ticktext=feuilles),
                      yaxis_title="distance de regroupement")
    base, Z = esp["base"], esp["Z"]
    groupe = pd.Series([nom_groupe[e] for e in etiquettes], index=base.index, name="groupe")
    kit = esp["kit"]
    lignes = []
    for nom in sorted(nom_groupe.values(), key=lambda s: int(s[1:])):
        m = (groupe == nom).values
        ligne = {"groupe": nom, "persos": int(m.sum()), "% physiques": f"{(base.loc[m, 'famille'] == 'physique').mean():.0%}"}
        for r in ROLES:
            if r in kit:
                ligne[f"% {r[5:]}"] = f"{kit.loc[m, r].mean():.0%}"
        ligne.update({s: round(float(Z.loc[m, s].mean()), 1) for s in STATS})
        lignes.append(ligne)
    titre = f"{n_groupes} grands groupes de persos ({len(esp['X'])} persos, corrélation cophénétique {coph:.2f})"
    return _figure(fig, titre, 420), pd.DataFrame(lignes), groupe


def _membres(L, noeud, n):
    pile, out = [noeud], []
    while pile:
        x = pile.pop()
        if x < n: out.append(x)
        else: pile += [int(L[x - n, 0]), int(L[x - n, 1])]
    return out


# ============================================================================================== ACP
def preparer_acp(t):
    """ACP des 8 stats centrées-réduites (même calcul que le notebook : SVD, axes orientés « stats hautes = positif »)."""
    Z = (t[STATS] - t[STATS].mean()) / t[STATS].std(ddof=0)
    U, S, Vt = np.linalg.svd(Z.values, full_matrices=False)
    var = S ** 2 / (S ** 2).sum()
    scores = pd.DataFrame(U * S, columns=[f"PC{i + 1}" for i in range(len(S))], index=t.index)
    load = pd.DataFrame(Vt.T, index=STATS, columns=scores.columns)
    for c in scores.columns:
        if load[c].sum() < 0:
            scores[c] *= -1; load[c] *= -1
    return dict(t=t, scores=scores, load=load, var=var)


def eta2(scores, cat):
    """Part de la variance d'un axe expliquée par une catégorie (0 à 1)."""
    out = {}
    for c in ["PC1", "PC2"]:
        g = scores[c].groupby(cat.values)
        out[c] = float(((g.mean() - scores[c].mean()) ** 2 * g.size()).sum() / ((scores[c] - scores[c].mean()) ** 2).sum())
    return out


def fig_acp(acp, couleur="famille", n_noms=5):
    t, sc, load, var = acp["t"], acp["scores"], acp["load"], acp["var"]
    cats = t[couleur].astype(str)
    fig = go.Figure()
    for i, c in enumerate(sorted(cats.unique())):
        m = (cats == c).values
        coul = COUL_FAMILLE[c] if couleur == "famille" else PALETTE[i % len(PALETTE)]   # la couleur suit la famille
        fig.add_scatter(x=sc.PC1[m], y=sc.PC2[m], mode="markers", name=f"{c} ({m.sum()})",
                        marker=dict(size=9, color=coul, opacity=0.8, line=dict(width=1, color="white")),
                        customdata=t.loc[m, ["nom_complet"]], hovertemplate="%{customdata[0]}<extra></extra>")
    k = 0.7 * np.abs(sc[["PC1", "PC2"]].values).max() / np.abs(load[["PC1", "PC2"]].values).max()
    for s in STATS:
        x, y = load.loc[s, "PC1"] * k, load.loc[s, "PC2"] * k
        fig.add_annotation(x=x, y=y, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                           arrowhead=2, arrowwidth=1.5, arrowcolor=GRIS, text="")
        fig.add_annotation(x=x * 1.12, y=y * 1.12, text=f"<b>{s}</b>", showarrow=False)
    loin = np.hypot(sc.PC1, sc.PC2).sort_values(ascending=False).index[:n_noms]
    for rang, i in enumerate(loin):                         # décalages alternés pour limiter les chevauchements
        fig.add_annotation(x=sc.PC1[i], y=sc.PC2[i], text=t.loc[i, "nom_complet"], showarrow=True, arrowwidth=1,
                           arrowcolor=GRIS, ax=(40 if rang % 2 else -40), ay=(-18 - 14 * (rang % 3)), font=dict(size=10))

    def axe(p):
        top = load[p].abs().sort_values(ascending=False).index[:3]
        return f"{p} : {var[int(p[2:]) - 1]:.0%} ({', '.join(f'{s} ' + ('+' if load.loc[s, p] > 0 else '−') for s in top)})"
    fig.update_layout(xaxis_title=axe("PC1"), yaxis_title=axe("PC2"), legend_title=couleur)
    tableau = load[["PC1", "PC2", "PC3"]].round(2).reset_index(names="stat")
    resume = pd.DataFrame([{"catégorie": c, **{f"eta² {k}": round(v, 2) for k, v in eta2(sc, t[c].astype(str)).items()}}
                           for c in ["famille", "element", "arme"]])
    titre = f"Carte 2D des persos (stats) : PC1 + PC2 = {var[:2].sum():.0%} de l'information"
    return _figure(fig, titre, 620), tableau, resume


# ============================================================================================== offre / demande
NIVEAUX_COMPETENCE_100 = {"competence_1": 3, "competence_2": 3, "competence_3": 2, "incarnation": 3}
ETATS = {
    "Dégâts continus": dict(offre=r"Inflige des dégâts continus", demande=r"subissant (des )?dégâts continus"),
    "Malus de résistance phys./mag.": dict(offre=r"[Rr]ésistances? (physique|magique)(?![^,.()]*soi-même)[^,.()]*-[0-9]+ ?%",
                                           demande=r"subissant un malus de résistance physique"),
    "Malus de résistance d'élément": dict(offre=r"[Rr]ésistance à l.élément [^ ]+ -[0-9]+", demande=r"malus de résistance d.élément"),
}


def table_offre_demande(persos, ids, niveau=100, avec_incarnation=True):
    """1 ligne par perso : F_i = fournit l'état i, D_i = en profite (description du niveau de compétence du perso)."""
    slots = ["competence_1", "competence_2", "competence_3"] + (["incarnation"] if avec_incarnation else [])
    lignes = []
    for p in persos:
        if p["id"] not in ids:
            continue
        textes = []
        for s in slots:
            niveaux = p["competences"][s]["niveaux"]
            if niveau == 120:
                n = niveaux[-1] if niveaux else {}
            else:
                n = next((x for x in niveaux if x["niveau"] == NIVEAUX_COMPETENCE_100[s]), {})
            textes.append(n.get("description") or "")
        ligne = {"perso_id": p["id"], "nom_complet": p["nom_complet"], "element": p["element"]}
        for i, r in enumerate(ETATS.values()):
            ligne[f"F_{i}"] = int(any(re.search(r["offre"], x) for x in textes))
            ligne[f"D_{i}"] = int(any(re.search(r["demande"], x) for x in textes))
        lignes.append(ligne)
    return pd.DataFrame(lignes)


def fig_offre_demande(p):
    lignes = []
    for i, nom in enumerate(ETATS):
        f, d = p[f"F_{i}"] == 1, p[f"D_{i}"] == 1
        lignes.append(dict(état=nom, fournit_seul=int((f & ~d).sum()), les_deux=int((f & d).sum()), profite_seul=int((~f & d).sum())))
    r = pd.DataFrame(lignes).set_index("état")
    fig1 = go.Figure()
    for col, lab, c in [("fournit_seul", "Fournit seulement", BLEU), ("les_deux", "Fournit ET en profite (autonome)", AQUA),
                        ("profite_seul", "En profite seulement (dépend d'un allié)", ORANGE)]:
        fig1.add_bar(y=r.index, x=r[col], orientation="h", name=lab, marker_color=c, text=r[col], textposition="inside",
                     hovertemplate="%{y}<br>" + lab + " : %{x}<extra></extra>")
    fig1.update_layout(barmode="stack", yaxis=dict(autorange="reversed"), xaxis_title="Nombre de persos",
                       legend=dict(orientation="h", y=-0.45, x=0))
    elems = sorted(p["element"].unique())
    M, T = np.zeros((len(ETATS), len(elems))), []
    for i in range(len(ETATS)):
        ligne = []
        for j, e in enumerate(elems):
            s = p[p["element"] == e]
            f, d = int(s[f"F_{i}"].sum()), int(s[f"D_{i}"].sum())
            M[i, j] = f - d; ligne.append(f"{f}/{d}")
        T.append(ligne)
    vmax = max(1, np.abs(M).max())
    # bleu = plus de fournisseurs, rouge = plus de profitants (comme le notebook)
    fig2 = go.Figure(go.Heatmap(z=-M, x=elems, y=list(ETATS), text=T, texttemplate="%{text}", colorscale=DIVERGENT,
                                zmin=-vmax, zmax=vmax, xgap=2, ygap=2, showscale=False,
                                hovertemplate="%{y} · %{x}<br>fournisseurs / profitants : %{text}<extra></extra>"))
    fig2.update_layout(yaxis=dict(autorange="reversed"))
    r["autonomie"] = (r["les_deux"] / (r["les_deux"] + r["profite_seul"]).replace(0, np.nan)).round(2)
    fig1.update_layout(margin=dict(b=110))
    return (_figure(fig1, f"Qui fournit un état ennemi, qui en profite ? ({len(p)} persos)", 380),
            _figure(fig2, "Par élément : fournisseurs / profitants (bleu = plus de fournisseurs, rouge = plus de profitants)", 330),
            r.reset_index())


# ============================================================================================== complexité
def table_complexite(t, df_eff, inclure_rf=False):
    """1 ligne par perso : nombre d'effets distincts du kit + indice de puissance (moyenne des stats centrées-réduites,
    avec la meilleure de ATK/MATK)."""
    eff = df_eff[df_eff["perso_id"].isin(t.index) & (df_eff["effet"] != "Autre")][["perso_id", "effet"]].drop_duplicates()
    if not inclure_rf:
        eff = eff[~eff["effet"].str.startswith("Recollection Field")]
    st = t[["nom_complet"] + STATS].copy()
    st["principale"] = st[["ATK", "MATK"]].max(axis=1)
    cols = ["HP", "MP", "principale", "DEF", "MDEF", "CRIT", "SPD"]
    st["puissance"] = ((st[cols] - st[cols].mean()) / st[cols].std(ddof=0)).mean(axis=1)
    st["n_effets"] = eff.groupby("perso_id")["effet"].nunique().reindex(st.index, fill_value=0).astype(int)
    return st


def rho_ic(x, y, n_boot=1000, graine=0):
    """Corrélation de Spearman + intervalle de confiance à 95 % par bootstrap."""
    r = spearmanr(x, y).statistic
    rng = np.random.default_rng(graine); n = len(x); xv, yv = np.asarray(x), np.asarray(y)
    b = [spearmanr(xv[i], yv[i]).statistic for i in (rng.integers(0, n, n) for _ in range(n_boot))]
    return float(r), float(np.nanpercentile(b, 2.5)), float(np.nanpercentile(b, 97.5))


def fig_complexite(st):
    n = len(st)
    r, lo, hi = rho_ic(st["n_effets"], st["puissance"])
    rng = np.random.default_rng(1)
    fig1 = go.Figure()
    fig1.add_scatter(x=st["n_effets"] + rng.uniform(-.2, .2, n), y=st["puissance"], mode="markers", name="persos",
                     marker=dict(size=8, color=BLEU, opacity=0.6), customdata=st[["nom_complet", "n_effets"]],
                     hovertemplate="%{customdata[0]}<br>%{customdata[1]} effets · puissance %{y:.2f}<extra></extra>")
    med = st.groupby("n_effets")["puissance"].agg(["median", "size"])
    med = med[med["size"] >= 5]
    fig1.add_scatter(x=med.index, y=med["median"], mode="lines+markers", name="médiane (groupes d'au moins 5 persos)",
                     line=dict(color=ROUGE, width=3), marker=dict(size=9), customdata=med["size"],
                     hovertemplate="%{x} effets : médiane %{y:.2f} (n=%{customdata})<extra></extra>")
    fig1.add_hline(y=0, line=dict(color=GRIS, width=1))
    fig1.update_layout(xaxis_title="Nombre d'effets distincts dans le kit (hors Recollection Field)",
                       yaxis_title="Indice de puissance", legend=dict(orientation="h", y=-0.25))
    cols = ["HP", "MP", "principale", "DEF", "MDEF", "CRIT", "SPD"]
    res = pd.DataFrame([(c, *rho_ic(st["n_effets"], st[c], n_boot=500)) for c in cols], columns=["stat", "rho", "bas", "haut"])
    res = res.sort_values("rho")
    fig2 = go.Figure(go.Bar(y=res["stat"], x=res["rho"], orientation="h", marker_color=AQUA,
                            error_x=dict(type="data", symmetric=False, array=res["haut"] - res["rho"],
                                         arrayminus=res["rho"] - res["bas"], color=GRIS),
                            customdata=res[["bas", "haut"]],
                            hovertemplate="%{y} : ρ = %{x:.2f} [%{customdata[0]:.2f} ; %{customdata[1]:.2f}]<extra></extra>"))
    fig2.add_vline(x=0, line=dict(color=GRIS))
    fig2.update_layout(xaxis_title="Corrélation de Spearman avec le nombre d'effets")
    titre1 = f"Kit plus complexe = stats plus fortes ?  ρ = {r:+.2f} [{lo:+.2f} ; {hi:+.2f}] ({n} persos)"
    return _figure(fig1, titre1, 450), _figure(fig2, "Stat par stat (barre = intervalle à 95 %)", 380), res.round(2)


# ============================================================================================== triangles
GROUPES_STATS = {"Attaque": ["principale", "CRIT"], "Défense": ["HP", "DEF", "MDEF"], "Tempo": ["MP", "SPD"]}
CIBLES = ["Soi-même", "Alliés", "Ennemis"]


def cible_effet(e):
    """À qui profite / nuit l'effet ? None = ignoré (Recollection Field, Autre, contrepartie, attaque supp.)."""
    if e.startswith("Recollection Field") or e in ("Autre", "Malus en contrepartie", "Attaque supplémentaire"):
        return None
    if " + : " in e or "(soi" in e or e in ("Multiplication Charge/Break (soi)", "Attaque avec coût en HP",
                                             "Absorption de HP", "Contre-attaque", "Provocation"):
        return "Soi-même"
    if "(alliés)" in e or "(cible non précisée)" in e or e in ("Guérison / soin de statut", "Restauration de MP (alliés)"):
        return "Alliés"
    if e.startswith(("Malus", "Réduction")) or e == "Dégâts continus":
        return "Ennemis"
    return None


def table_budget_stats(t):
    st = t[["nom_complet", "famille"] + STATS].copy()
    st["principale"] = st[["ATK", "MATK"]].max(axis=1)
    cols = sorted({c for g in GROUPES_STATS.values() for c in g})
    rel = st[cols] / st[cols].mean()                        # 1.0 = stat moyenne des persos affichés
    for g, cs in GROUPES_STATS.items():
        st[g] = rel[cs].mean(axis=1)
    tot = st[list(GROUPES_STATS)].sum(axis=1)
    for g in GROUPES_STATS:
        st["part_" + g] = st[g] / tot
    return st


def table_budget_kit(t, df_eff, min_effets=3):
    eff = df_eff[df_eff["perso_id"].isin(t.index)][["perso_id", "effet"]].drop_duplicates()
    eff = eff.assign(cible=eff["effet"].map(cible_effet)).dropna(subset=["cible"])
    k = eff.groupby(["perso_id", "cible"]).size().unstack(fill_value=0).reindex(columns=CIBLES, fill_value=0)
    k["n"] = k[CIBLES].sum(axis=1)
    k = k[k["n"] >= min_effets]                             # trop peu d'effets : la part n'a pas de sens
    for c in CIBLES:
        k["part_" + c] = k[c] / k["n"]
    return k.join(t[["nom_complet", "famille"]], how="inner")


def _ternaire(parts, noms, familles, noms_persos, titre, jitter=0.0):
    """Triangle zoomé automatiquement sur les données (Plotly Scatterternary)."""
    P = parts.values.astype(float)
    moy = P.mean(axis=0)                                    # moyenne calculée avant le petit décalage visuel
    if jitter:
        P = np.clip(P + np.random.default_rng(0).normal(0, jitter, P.shape), 0.001, None)
        P = P / P.sum(axis=1, keepdims=True)
    mins = np.maximum(P.min(axis=0) - 0.03, 0)
    if mins.sum() > 0.9:
        mins = mins * 0.9 / mins.sum()
    fig = go.Figure()
    for fam, coul in (("physique", BLEU), ("magique", ORANGE)):
        m = (familles == fam).values
        if m.any():
            fig.add_scatterternary(a=P[m, 0], b=P[m, 1], c=P[m, 2], mode="markers", name=f"{fam} ({m.sum()})",
                                   marker=dict(size=8, color=coul, opacity=0.75, line=dict(width=1, color="white")),
                                   customdata=noms_persos[m], hovertemplate="%{customdata}<br>" + noms[0] + " %{a:.0%} · "
                                   + noms[1] + " %{b:.0%} · " + noms[2] + " %{c:.0%}<extra></extra>")
    fig.add_scatterternary(a=[moy[0]], b=[moy[1]], c=[moy[2]], mode="markers", name="moyenne",
                           marker=dict(symbol="cross", size=14, color=GRIS),
                           hovertemplate="moyenne<br>%{a:.0%} · %{b:.0%} · %{c:.0%}<extra></extra>")
    axe = lambda nom, mn: dict(title=dict(text=nom), min=float(mn), tickformat=".0%", gridcolor="rgba(158,158,158,0.35)")
    fig.update_layout(ternary=dict(aaxis=axe(noms[0], mins[0]), baxis=axe(noms[1], mins[1]), caxis=axe(noms[2], mins[2]),
                                   bgcolor="rgba(0,0,0,0)"), legend=dict(orientation="h", y=-0.12))
    fig = _figure(fig, titre, 540)
    fig.update_layout(margin=dict(l=70, r=70, t=90, b=40))         # place pour les noms des coins
    return fig


def fig_triangles(t, df_eff):
    st = table_budget_stats(t)
    kit = table_budget_kit(t, df_eff)
    f1 = _ternaire(st[["part_" + g for g in GROUPES_STATS]], list(GROUPES_STATS), st["famille"], st["nom_complet"].values,
                   "Budget de STATS<br><sup>où va la force du perso ?</sup>")
    f2 = _ternaire(kit[["part_" + c for c in CIBLES]], CIBLES, kit["famille"], kit["nom_complet"].values,
                   f"Budget de KIT<br><sup>à qui s'adressent les effets ? ({len(kit)} persos)</sup>",
                   jitter=0.012)
    resume = pd.DataFrame(
        [{"budget": "stats", "part": g, "moyenne": f"{st['part_' + g].mean():.1%}",
          "min – max": f"{st['part_' + g].min():.1%} – {st['part_' + g].max():.1%}"} for g in GROUPES_STATS]
        + [{"budget": "kit", "part": c, "moyenne": f"{kit['part_' + c].mean():.1%}",
            "min – max": f"{kit['part_' + c].min():.1%} – {kit['part_' + c].max():.1%}"} for c in CIBLES])
    return f1, f2, resume
