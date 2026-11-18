"""Graphiques interactifs (Plotly) de la page Graphiques : données filtrées -> (figure, tableau).
Chaque fonction renvoie aussi le tableau de données affiché, pour la vue « Voir les données »."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .donnees import STATS, table_persos
from .moteur_kit import categorie_effet

# Palette vérifiée daltonisme (validateur du skill dataviz) : ordre fixe, jamais recyclé
BLEU, ORANGE, AQUA, JAUNE, MAGENTA, VERT = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
GRIS, ROUGE = "#9e9e9e", "#e34948"
COUL_FAMILLE = {"physique": BLEU, "magique": ORANGE}
COUL_CATEGORIE = {"Rôle": BLEU, "Recollection Field": ORANGE, "Augmentation conditionnelle": AQUA,
                  "Bonus (buff)": JAUNE, "Malus sur l'ennemi": MAGENTA, "Autres mécaniques": VERT, "Personnalisé": GRIS}
GRILLES = {1: {"HP": 15, "DEF": 3, "MDEF": 3, "ATK": 5, "MATK": 5, "CRIT": 5},
           100: {"HP": 75, "DEF": 15, "MDEF": 15, "ATK": 25, "MATK": 25}}
SLOTS = {"Compétences 1 à 3 + incarnation": ["competence_1", "competence_2", "competence_3", "incarnation"],
         "Compétences 1 à 3": ["competence_1", "competence_2", "competence_3"], "Incarnation": ["incarnation"]}
PETIT_GROUPE = 10
MISE_EN_PAGE = dict(font=dict(size=13), margin=dict(l=10, r=10, t=50, b=10))   # fond et textes : thème de Streamlit


NEUTRE_MILIEU = "#c8c7c2"     # gris du milieu des échelles divergentes : visible sur fond clair comme foncé
DIVERGENT = [[0, BLEU], [0.5, NEUTRE_MILIEU], [1, ROUGE]]


def appliquer_survol(fig):
    """Bulle de survol foncée et texte clair : lisible en mode clair comme en mode foncé."""
    fig.update_layout(hoverlabel=dict(bgcolor="#262730", bordercolor=GRIS, font=dict(color="#fafafa", size=13)))
    return fig


# ---------------------------------------------------------------------------------------------- données
def table_graphiques(persos, niveau=100):
    """Une ligne par perso : identité, famille (ATK ≥ MATK = physique, comme l'outil de création), 8 stats, ordre de sortie."""
    t = table_persos(persos, niveau)
    infos = {p["id"]: (p["nom"], p["titre"]) for p in persos}
    t["nom"] = [infos[i][0] for i in t.index]
    t["titre"] = [infos[i][1] for i in t.index]
    t["famille"] = np.where(t["ATK"] >= t["MATK"], "physique", "magique")
    t["ordre"] = t.index.to_series().rank(method="first").astype(int)
    return t.drop(columns=["c1", "c2", "c3"])


def filtrer(t, df_eff, offerts=True, elements=None, armes=None, familles=None, effets=None, recherche=""):
    """Filtres de la barre latérale. Une liste vide ou None = pas de filtre. effets : persos qui ont AU MOINS un de ces effets."""
    garde = pd.Series(True, index=t.index)
    if not offerts: garde &= ~t["free"]
    if elements: garde &= t["element"].isin(elements)
    if armes: garde &= t["arme"].isin(armes)
    if familles: garde &= t["famille"].isin(familles)
    if effets: garde &= t.index.isin(df_eff.loc[df_eff["effet"].isin(effets), "perso_id"])
    if recherche.strip(): garde &= t["nom_complet"].str.contains(recherche.strip(), case=False, regex=False)
    return t[garde]


def _figure(fig, titre, hauteur=450):
    fig.update_layout(title=titre, height=hauteur, **MISE_EN_PAGE)
    return fig


# ---------------------------------------------------------------------------------------------- simple
def fig_repartition(t, par="element"):
    """Barres empilées : nombre de persos par élément (ou arme), découpé par famille."""
    tab = pd.crosstab(t[par], t["famille"]).reindex(columns=["physique", "magique"], fill_value=0)
    tab["total"] = tab.sum(axis=1)
    tab = tab.sort_values("total", ascending=False)
    tab["% physiques"] = (tab["physique"] / tab["total"] * 100).round(0).astype(int)
    fig = go.Figure()
    for fam in ["physique", "magique"]:
        fig.add_bar(x=tab.index, y=tab[fam], name=fam, marker_color=COUL_FAMILLE[fam], text=tab[fam],
                    textposition="inside", hovertemplate=f"%{{x}}<br>{fam} : %{{y}}<extra></extra>")
    fig.add_scatter(x=tab.index, y=tab["total"], mode="text", text=[f"{n} · {p} % phys." for n, p in zip(tab["total"], tab["% physiques"])],
                    textposition="top center", showlegend=False, hoverinfo="skip")
    fig.update_layout(barmode="stack", bargap=0.35, yaxis_title="Nombre de persos", xaxis_title=None,
                      yaxis_range=[0, tab["total"].max() * 1.18], legend_title="Famille")
    return _figure(fig, f"Persos par {'élément' if par == 'element' else 'arme'}, selon la famille"), tab.reset_index()


def fig_distribution(t, stat, par="element"):
    """Boîtes à moustaches + un point par perso (survol = nom). Les groupes de moins de 10 persos sont signalés."""
    n = t[par].value_counts()
    ordre = t.groupby(par)[stat].median().sort_values(ascending=False).index
    fig = go.Figure()
    for g in ordre:
        sous = t[t[par] == g]
        etiquette = f"{g}<br>(n={n[g]}{', peu' if n[g] < PETIT_GROUPE else ''})"
        fig.add_box(y=sous[stat], name=etiquette, boxpoints="all", jitter=0.4, pointpos=0, marker=dict(size=8, color=BLEU, opacity=0.6),
                    line=dict(color=BLEU, width=2), fillcolor="rgba(42,120,214,0.12)", customdata=sous[["nom_complet"]],
                    hovertemplate="%{customdata[0]}<br>" + stat + " : %{y}<extra></extra>", showlegend=False)
    fig.update_layout(yaxis_title=stat)
    resume = t.groupby(par)[stat].agg(["count", "min", "median", "max"]).loc[ordre].reset_index()
    return _figure(fig, f"{stat} selon {'l\'élément' if par == 'element' else 'l\'arme' if par == 'arme' else 'la famille'}"), resume


def top_flop(t, stat, n=5):
    """Les n meilleurs et n pires (les ex æquo au seuil sont tous gardés, comme dans le notebook)."""
    col = [stat, "nom_complet", "element", "arme"]
    haut = t[t[stat] >= t[stat].nlargest(n).min()].sort_values([stat, "nom_complet"], ascending=[False, True])[col]
    bas = t[t[stat] <= t[stat].nsmallest(n).max()].sort_values([stat, "nom_complet"])[col]
    return haut.reset_index(drop=True), bas.reset_index(drop=True)


def _percentile(serie, v):
    """Part des persos de référence en dessous de v (les égalités comptent pour moitié)."""
    return ((serie < v).sum() + (serie <= v).sum()) / (2 * len(serie)) * 100


def carte_identite(ref, valeurs, nom, comparer=None):
    """Radar des percentiles d'un perso, sur la bande 10-90 % des persos de sa famille (ref = persos de référence).
    comparer : (valeurs, nom) d'un deuxième perso à superposer. Renvoie (figure, tableau, phrase de synthèse)."""
    famille = "physique" if valeurs["ATK"] >= valeurs["MATK"] else "magique"
    groupe = ref[ref["famille"] == famille]
    pct_ref = pd.DataFrame({s: ref[s].apply(lambda v: _percentile(ref[s], v)) for s in STATS})
    pct_groupe = pct_ref.loc[groupe.index]
    bas, haut, med = pct_groupe.quantile(0.10), pct_groupe.quantile(0.90), pct_groupe.median()
    pct = pd.Series({s: _percentile(ref[s], valeurs[s]) for s in STATS})
    axes = STATS + STATS[:1]
    boucle = lambda serie: list(serie[STATS]) + [serie[STATS[0]]]
    fig = go.Figure()
    # Bande 10-90 % : un secteur semi-transparent par stat, du 10e au 90e percentile (lisible en clair comme en foncé)
    fig.add_barpolar(r=(haut - bas)[STATS].values, base=bas[STATS].values, theta=STATS, width=[0.8] * len(STATS),
                     marker=dict(color="rgba(42,120,214,0.30)", line=dict(width=0)),
                     name=f"10 à 90 % des persos {famille}s (n={len(groupe)})",
                     customdata=np.stack([bas[STATS].values, haut[STATS].values], axis=1),
                     hovertemplate="%{theta} : 80 % des persos entre %{customdata[0]:.0f} et %{customdata[1]:.0f}<extra></extra>")
    fig.add_scatterpolar(r=boucle(med), theta=axes, mode="lines", line=dict(color=BLEU, dash="dash", width=1.5),
                         name="médiane de la famille", hovertemplate="%{theta} : médiane %{r:.0f}<extra></extra>")
    fig.add_scatterpolar(r=boucle(pct), theta=axes, mode="lines+markers", line=dict(color=ROUGE, width=2.5),
                         marker=dict(size=9), name=nom, customdata=[valeurs[s] for s in axes],
                         hovertemplate="%{theta} : %{customdata} (percentile %{r:.0f})<extra></extra>")
    if comparer:
        v2, nom2 = comparer
        pct2 = pd.Series({s: _percentile(ref[s], v2[s]) for s in STATS})
        fig.add_scatterpolar(r=boucle(pct2), theta=axes, mode="lines+markers", line=dict(color=VERT, width=2.5, dash="dot"),
                             marker=dict(size=9, symbol="diamond"), name=nom2, customdata=[v2[s] for s in axes],
                             hovertemplate="%{theta} : %{customdata} (percentile %{r:.0f})<extra></extra>")
    fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100],
                                                                       gridcolor="rgba(158,158,158,0.35)"),
                                 angularaxis=dict(gridcolor="rgba(158,158,158,0.35)")),
                      legend=dict(orientation="h", y=-0.12))
    verdict = ["au-dessus" if pct[s] > haut[s] else "en dessous" if pct[s] < bas[s] else "dans la bande" for s in STATS]
    tableau = pd.DataFrame({"stat": STATS, "valeur": [valeurs[s] for s in STATS], "percentile": pct.round(0).astype(int).values,
                            "bande 10-90": [f"{bas[s]:.0f} à {haut[s]:.0f}" for s in STATS], "verdict": verdict})
    hors = int(((pct < bas) | (pct > haut)).sum())
    part = (((pct_groupe < bas) | (pct_groupe > haut)).sum(axis=1) >= hors).mean()
    phrase = (f"{hors} stat(s) hors de la bande sur 8. Parmi les {len(groupe)} persos {famille}s de référence, "
              f"{part:.0%} en ont au moins autant.")
    return _figure(fig, f"Carte d'identité : {nom}", 560), tableau, phrase


def fig_effets(df_eff_sel, n_persos):
    """Nombre de persos (de la sélection) par effet, coloré par catégorie."""
    g = (df_eff_sel.groupby("effet")["perso_id"].nunique().rename("persos").reset_index()
         .query("effet != 'Autre'").sort_values(["persos", "effet"], ascending=[True, False]))
    g["catégorie"] = g["effet"].map(categorie_effet)
    g["% des persos"] = (g["persos"] / max(n_persos, 1) * 100).round(0).astype(int)
    fig = go.Figure()
    for cat, coul in COUL_CATEGORIE.items():
        sous = g[g["catégorie"] == cat]
        if len(sous):
            fig.add_bar(y=sous["effet"], x=sous["persos"], orientation="h", name=cat, marker_color=coul,
                        text=sous["persos"], textposition="outside", customdata=sous[["% des persos"]],
                        hovertemplate="%{y}<br>%{x} persos (%{customdata[0]} %)<extra></extra>")
    fig.update_layout(barmode="stack", yaxis=dict(categoryorder="array", categoryarray=list(g["effet"])),
                      xaxis_title="Nombre de persos", legend_title="Catégorie", bargap=0.25)
    return _figure(fig, f"Effets présents ({len(g)} effets, {n_persos} persos)", max(420, 24 * len(g) + 120)), \
        g.sort_values("persos", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------------------------- avancé
def fig_effets_element(df_eff_sel, t, seuil=PETIT_GROUPE):
    """Carte de chaleur effet x élément : nombre de persos, couleur = écart à ce que le hasard donnerait (en écarts-types,
    loi hypergéométrique comme dans le notebook). Couleur neutre si l'effet concerne moins de `seuil` persos."""
    n_el = t["element"].value_counts()
    elements = list(n_el.index)
    N = int(n_el.sum())
    cnt = (df_eff_sel[df_eff_sel["effet"] != "Autre"].drop_duplicates(["perso_id", "effet"])
           .pipe(lambda d: pd.crosstab(d["effet"], d["element"])).reindex(columns=elements, fill_value=0))
    k = cnt.sum(axis=1)
    cnt, k = cnt.loc[k.sort_values(ascending=False).index], k.sort_values(ascending=False)
    pp = (k / N).values[:, None]
    attendu = pp * n_el.values[None, :]
    var = n_el.values[None, :] * pp * (1 - pp) * (N - n_el.values[None, :]) / max(N - 1, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.nan_to_num((cnt.values - attendu) / np.sqrt(var))
    z[(k < seuil).values] = 0
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{e} (n={n_el[e]})" for e in elements], y=[f"{e} ({k[e]})" for e in cnt.index], text=cnt.values,
        texttemplate="%{text}", colorscale=DIVERGENT, zmin=-3, zmax=3, xgap=2, ygap=2,
        customdata=np.round(attendu, 1), colorbar=dict(title="écart<br>(écarts-types)"),
        hovertemplate="%{y} · %{x}<br>%{text} persos (attendu ≈ %{customdata})<br>écart %{z:.1f}<extra></extra>"))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return _figure(fig, "Effets par élément (couleur = plus ou moins que le hasard)", max(450, 24 * len(cnt) + 140)), cnt.reset_index()


def fig_correlations(t):
    c = t[STATS].corr()
    fig = go.Figure(go.Heatmap(z=c.values, x=STATS, y=STATS, text=c.round(2).values, texttemplate="%{text}",
                               colorscale=DIVERGENT, zmin=-1, zmax=1, xgap=2, ygap=2, colorbar=dict(title="corrélation"),
                               hovertemplate="%{y} et %{x} : %{z:.2f}<extra></extra>"))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return _figure(fig, f"Corrélations entre les stats ({len(t)} persos)", 520), c.round(2).reset_index(names="stat")


def fig_menu_stats(t_niveau, niveau):
    """Pour chaque stat : combien de persos ont EXACTEMENT chaque valeur. En bleu : valeurs sur la grille du jeu."""
    pas = GRILLES.get(niveau, {})
    fig = make_subplots(rows=2, cols=4, subplot_titles=STATS, vertical_spacing=0.18, horizontal_spacing=0.06)
    lignes = []
    for i, s in enumerate(STATS):
        c = t_niveau[s].value_counts().sort_index()
        sur = (c.index % pas[s] == 0) if s in pas else np.zeros(len(c), dtype=bool)
        couleurs = np.where(sur, BLEU, GRIS)
        r, col = i // 4 + 1, i % 4 + 1
        fig.add_bar(x=c.index, y=c.values, marker_color=couleurs, width=max((c.index.max() - c.index.min()) / 150, 0.5),
                    showlegend=False, row=r, col=col, hovertemplate=f"{s} = %{{x}} : %{{y}} persos<extra></extra>")
        part = f"{(t_niveau[s] % pas[s] == 0).mean():.0%} sur la grille (pas {pas[s]})" if s in pas else "pas de grille"
        lignes.append(dict(stat=s, valeurs_distinctes=len(c), grille=part,
                           part_des_5_plus_frequentes=f"{c.nlargest(5).sum() / len(t_niveau):.0%}"))
    return _figure(fig, f"Menu des valeurs de stats, niveau {niveau} (bleu = sur la grille)", 560), pd.DataFrame(lignes)


def fig_ordre_sortie(t, stat):
    """Une stat selon l'ordre de sortie (id croissant) : courbe brute + moyenne glissante sur 10 persos.
    « score » = moyenne des 8 stats centrées-réduites (évite que les HP écrasent le total)."""
    d = t.sort_values("ordre").copy()
    if stat == "score":
        d["score"] = ((d[STATS] - d[STATS].mean()) / d[STATS].std()).mean(axis=1).round(3)
    d["moyenne glissante"] = d[stat].rolling(10, center=True).mean()
    fig = go.Figure()
    fig.add_scatter(x=d["ordre"], y=d[stat], mode="lines+markers", line=dict(color=BLEU, width=1), opacity=0.35,
                    marker=dict(size=5), name=stat, customdata=d[["nom_complet"]],
                    hovertemplate="%{customdata[0]}<br>rang %{x} : %{y}<extra></extra>")
    fig.add_scatter(x=d["ordre"], y=d["moyenne glissante"], mode="lines", line=dict(color=BLEU, width=3),
                    name="moyenne glissante (10 persos)", hovertemplate="rang %{x} : %{y:.0f}<extra></extra>")
    fig.update_layout(xaxis_title="Ordre de sortie (rang par id)", yaxis_title=stat, legend=dict(orientation="h", y=-0.2))
    return _figure(fig, f"{stat} selon l'ordre de sortie"), d[["ordre", "nom_complet", stat, "moyenne glissante"]]
