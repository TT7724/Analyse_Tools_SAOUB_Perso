"""Page Graphiques : filtres communs dans la barre latérale (comme des segments Power BI), onglets Simple / Avancé."""
import streamlit as st

from app_commun import donnees, titre_avec_aide
from saoub.donnees import STATS
from saoub.graphiques_avances import (construire_espace, fig_acp, fig_complexite, fig_dendrogramme, fig_offre_demande,
                                      fig_triangles, fig_voisins, kit_par_slots, preparer_acp, table_complexite,
                                      table_offre_demande)
from saoub.graphiques import (PETIT_GROUPE, SLOTS, appliquer_survol, carte_identite, fig_correlations, fig_distribution, fig_effets,
                              fig_effets_element, fig_menu_stats, fig_ordre_sortie, fig_repartition, filtrer,
                              table_graphiques, top_flop)

tout = donnees()
df_eff = tout["df_eff"]
NOMS_PAR = {"element": "Élément", "arme": "Arme", "famille": "Famille"}


@st.cache_data(show_spinner=False)
def table(niveau, version):
    return table_graphiques(tout["persos"], niveau)


def montrer(fig, donnees_tableau, cle):
    st.plotly_chart(appliquer_survol(fig), width="stretch", key=cle)
    with st.expander("Voir les données"):
        st.dataframe(donnees_tableau, hide_index=True, width="stretch")


# ---------- filtres (barre latérale) ----------
with st.sidebar:
    st.markdown("### Filtres")
    niveau = st.radio("Niveau des stats", [100, 120, 1], horizontal=True, key="g_niveau")
    t_complet = table(niveau, tout["version"])
    n_tous, n_sans = len(t_complet), int((~t_complet["free"]).sum())
    offerts = st.radio("Persos", [True, False], key="g_offerts", horizontal=True,
                       format_func=lambda v: f"Tous ({n_tous})" if v else f"Sans les offerts ({n_sans})",
                       help="Les offerts (free) sont souvent plus faibles. La création et la vérification utilisent "
                            "toujours les persos sans les offerts.")
    elements = st.multiselect("Élément", sorted(t_complet["element"].unique()), key="g_elements", placeholder="Tous")
    armes = st.multiselect("Arme", sorted(t_complet["arme"].unique()), key="g_armes", placeholder="Toutes")
    familles = st.multiselect("Famille", ["physique", "magique"], key="g_familles", placeholder="Les deux")
    effets = st.multiselect("A au moins un de ces effets", sorted(set(df_eff["effet"]) - {"Autre"}), key="g_effets",
                            placeholder="Tous les persos")
    recherche = st.text_input("Nom ou titre contient", key="g_recherche", placeholder="ex. : Kirito")

t = filtrer(t_complet, df_eff, offerts, elements, armes, familles, effets, recherche)
ref = t_complet if offerts else t_complet[~t_complet["free"]]          # référence des percentiles (carte d'identité)

gauche, droite = st.columns([12, 1], vertical_alignment="bottom")
gauche.title("📊 Graphiques")
with droite:
    with st.popover("?", help="Comment utiliser cette page"):
        st.markdown("""#### Comment utiliser cette page
- **Filtres** (à gauche) : ils s'appliquent à **tous** les graphiques, comme les segments de Power BI. Une liste vide = pas de filtre.
- **Survol** : passe la souris sur un point ou une barre pour voir le perso et les valeurs. Clique sur une légende pour masquer une série, double-clique pour l'isoler.
- **Zoom** : sélectionne une zone ; double-clic pour revenir.
- **Voir les données** : sous chaque graphique, le tableau exact affiché.
- **Simple** : les graphiques pour tout le monde. **Avancé** : des analyses plus statistiques.
- Moins de **10 persos** dans un groupe : n'en tire pas de conclusion, c'est trop peu.""")

st.caption(f"**{len(t)} perso(s) sélectionné(s)** sur {len(t_complet)} · niveau {niveau}")
if len(t) == 0:
    st.warning("Aucun perso ne correspond à ces filtres : élargis-en un.")
    st.stop()
if len(t) < PETIT_GROUPE:
    st.warning(f"Seulement {len(t)} persos : les graphiques sont à lire comme des exemples, pas comme des tendances.")

simple, avance = st.tabs(["Simple", "Avancé"])

# ======================================================================================== SIMPLE
with simple:
    titre_avec_aide(
        "Répartition des persos",
        quoi="Le nombre de persos par élément (ou par arme), découpé en physiques (bleu) et magiques (orange).",
        sert="Voir quels éléments ou armes sont les plus fournis, et s'ils penchent vers le physique ou le magique.",
        lire="Hauteur totale = nombre de persos ; au-dessus, la part de physiques. Un perso est physique si ATK ≥ MATK.",
        limites="Un élément avec peu de persos peut avoir un pourcentage extrême par hasard.")
    par = st.radio("Regrouper par", ["element", "arme"], format_func=NOMS_PAR.get, horizontal=True, key="g_rep_par")
    montrer(*fig_repartition(t, par), "rep")

    titre_avec_aide(
        "Distribution d'une stat",
        quoi="Pour chaque groupe : une boîte (du quart le plus bas au quart le plus haut, trait = médiane) et un point par perso.",
        sert="Comparer une stat entre éléments, armes ou familles, et repérer les persos qui sortent du lot.",
        lire="Boîte haute = groupe fort sur cette stat ; boîte longue = valeurs très variées. Les groupes sont triés par médiane. "
             "Survole un point pour voir le perso.",
        limites=f"« peu » = moins de {PETIT_GROUPE} persos : la boîte n'est pas fiable. Comparer l'ATK des magiques n'a pas "
                "beaucoup de sens : filtre par famille.")
    c1, c2 = st.columns(2)
    stat = c1.selectbox("Stat", STATS, index=2, key="g_dist_stat")
    par = c2.selectbox("Comparer par", list(NOMS_PAR), format_func=NOMS_PAR.get, key="g_dist_par")
    montrer(*fig_distribution(t, stat, par), "dist")

    titre_avec_aide(
        "Les meilleurs et les pires",
        quoi="Les 5 persos les plus hauts et les 5 plus bas sur une stat (les ex æquo sont tous affichés).",
        sert="Trouver rapidement les records de la sélection.",
        lire="Tableau trié : à gauche du plus haut au moins haut, à droite du plus bas au moins bas.")
    stat_top = st.selectbox("Stat", STATS, key="g_top_stat")
    haut, bas = top_flop(t, stat_top)
    a, b = st.columns(2)
    a.markdown(f"**Les plus hauts en {stat_top}**"); a.dataframe(haut, hide_index=True, width="stretch")
    b.markdown(f"**Les plus bas en {stat_top}**"); b.dataframe(bas, hide_index=True, width="stretch")

    titre_avec_aide(
        "Carte d'identité d'un perso",
        quoi="Un radar : chaque branche est une stat, en percentile (0 = le plus bas, 100 = le plus haut). La zone bleue = "
             "là où se trouvent 80 % des persos de la même famille (de 10 % à 90 %), le pointillé = leur médiane.",
        sert="Voir d'un coup d'œil le profil d'un perso (tank, rapide, fragile…) et le comparer à un autre.",
        lire="Le perso (rouge) hors de la zone bleue = stat inhabituelle pour sa famille. La phrase sous le graphique dit "
             "si c'est rare : « 40 % en ont au moins autant » = profil courant.",
        limites="Référence = tous les persos du niveau choisi (sans les offerts si tu les as exclus), pas seulement la "
                "sélection : sinon la bande changerait à chaque filtre.")
    noms = dict(zip(t["nom_complet"], t.index))
    tous = dict(zip(t_complet["nom_complet"], t_complet.index))
    c1, c2 = st.columns(2)
    choix = c1.selectbox("Perso (tape pour chercher)", sorted(noms), key="g_carte_perso")
    autre = c2.selectbox("Comparer avec (facultatif)", sorted(tous), index=None, key="g_carte_autre", placeholder="Aucun")
    valeurs = t_complet.loc[noms[choix], STATS].to_dict()
    comparer = (t_complet.loc[tous[autre], STATS].to_dict(), autre) if autre else None
    fig, tableau, phrase = carte_identite(ref, valeurs, choix, comparer)
    montrer(fig, tableau, "carte")
    st.caption(phrase)

    titre_avec_aide(
        "Effets des compétences",
        quoi="Pour chaque effet : le nombre de persos de la sélection qui l'ont, coloré par catégorie.",
        sert="Voir quels effets sont courants ou rares, par exemple pour un élément ou une arme (filtres à gauche).",
        lire="Barre longue = effet courant. Survole une barre pour le pourcentage de persos.",
        limites="Effets lus dans la description du niveau maximal de chaque compétence, avec les règles de l'outil "
                "(les rôles Break / Charge / Mode enhance ne sont pas dedans).")
    slots = st.radio("Compétences", list(SLOTS), horizontal=True, key="g_eff_slots")
    eff_sel = df_eff[df_eff["perso_id"].isin(t.index) & df_eff["slot"].isin(SLOTS[slots])]
    montrer(*fig_effets(eff_sel, len(t)), "effets")

# ======================================================================================== AVANCÉ
with avance:
    titre_avec_aide(
        "Effets par élément",
        quoi="Une case par effet et par élément : le nombre de persos. La couleur compare ce nombre à ce que le hasard "
             "donnerait si les effets étaient répartis sans tenir compte de l'élément.",
        sert="Repérer les effets « typiques » d'un élément (rouge) ou qu'il évite (bleu).",
        lire="Gris = comme le hasard. Rouge = plus que prévu, bleu = moins ; l'échelle est en écarts-types : au-delà de 2, "
             "c'est net. Survole une case pour le nombre attendu.",
        limites=f"Couleur neutre pour les effets de moins de {PETIT_GROUPE} persos. Avec 59 effets × 7 éléments, quelques "
                "cases colorées apparaissent par pur hasard : regarde les tendances, pas une case isolée.")
    slots_a = st.radio("Compétences", list(SLOTS), horizontal=True, key="g_eff_el_slots")
    montrer(*fig_effets_element(df_eff[df_eff["perso_id"].isin(t.index) & df_eff["slot"].isin(SLOTS[slots_a])], t), "eff_el")

    titre_avec_aide(
        "Corrélations entre les stats",
        quoi="Pour chaque paire de stats, un nombre entre -1 et 1 (corrélation de Pearson).",
        sert="Comprendre les « règles de construction » : quelles stats montent ensemble, lesquelles s'opposent.",
        lire="Proche de 1 (rouge) : quand l'une monte, l'autre aussi. Proche de -1 (bleu) : quand l'une monte, l'autre "
             "baisse (ATK et MATK : -0,78 sans les offerts, physiques contre magiques ; seulement -0,2 avec, car les offerts sont "
             "faibles dans les deux). Proche de 0 : pas de lien en ligne droite.",
        limites="Mélanger physiques et magiques crée des corrélations à cause des deux familles : filtre par famille pour "
                "voir les liens à l'intérieur d'une famille.")
    montrer(*fig_correlations(t), "corr")

    titre_avec_aide(
        "Menu des valeurs de stats",
        quoi="Pour chaque stat : combien de persos ont exactement chaque valeur. Bleu = valeur sur la « grille » du jeu "
             "(niveau 1 : HP par 15, ATK/MATK par 5, DEF/MDEF par 3, CRIT par 5 ; niveau 100 : × 5).",
        sert="Voir que les développeurs choisissent leurs stats dans un « menu » de valeurs, ce qui sert à l'outil de création.",
        lire="Pic haut = valeur très réutilisée. Beaucoup de bleu = la grille est bien respectée. Le tableau donne la part "
             "sur la grille et le poids des 5 valeurs les plus fréquentes.",
        limites="Le filtre « Niveau » à gauche choisit le niveau affiché ; au niveau 120, aucune grille n'est définie.")
    montrer(*fig_menu_stats(t, niveau), "menu")

    titre_avec_aide(
        "Stats selon l'ordre de sortie",
        quoi="Une stat pour chaque perso, rangés par id (≈ ordre de sortie), avec une moyenne glissante sur 10 persos.",
        sert="Vérifier s'il y a une « inflation » : les persos récents sont-ils plus forts ?",
        lire="Courbe épaisse qui monte = les persos récents ont plus de cette stat. « score » = moyenne des 8 stats "
             "ramenées à la même échelle (sinon les HP écrasent tout).",
        limites="L'id n'est qu'une approximation de la date de sortie. Dans tes notebooks, aucun lien net n'a été trouvé.")
    stat_o = st.selectbox("Stat", ["score"] + STATS, key="g_ordre_stat")
    montrer(*fig_ordre_sortie(t, stat_o), "ordre")

    if len(t) < PETIT_GROUPE:
        st.info(f"Les analyses suivantes demandent au moins {PETIT_GROUPE} persos : élargis les filtres.")
        st.stop()

    # ---------- voisins et groupes ----------
    titre_avec_aide(
        "Voisins et groupes de persos",
        quoi="Chaque perso est décrit par ses 8 stats et son kit (rôles + effets). On mesure la « distance » entre deux "
             "persos : courte = ils se ressemblent. Le curseur règle le poids des stats par rapport au kit.",
        sert="Trouver les persos qui ressemblent le plus à un perso donné, et voir les grandes « familles » de persos "
             "que les développeurs ont créées.",
        lire="Voisins : barre courte = très ressemblant ; le trait vert = distance habituelle au plus proche voisin, le "
             "trait rouge = deux persos pris au hasard. Arbre : chaque branche du bas est un groupe (G1 = le plus gros) ; "
             "plus deux branches se rejoignent haut, plus les groupes sont différents. Dans le tableau, les colonnes de "
             "stats donnent l'écart moyen du groupe (en écarts-types : +1 = nettement au-dessus de la moyenne).",
        limites="Les groupes dépendent du poids stats/kit et du nombre de groupes choisi : ce sont des repères, pas des "
                "catégories officielles. Corrélation cophénétique (fidélité de l'arbre aux distances) : au-dessus de "
                "0,7 c'est bon, autour de 0,4 l'arbre simplifie beaucoup.")
    c1, c2 = st.columns(2)
    slots_v = c1.radio("Kit lu dans", list(SLOTS), index=1, horizontal=True, key="g_vois_slots")
    poids = c2.slider("Poids des stats (0 = kit seul, 1 = stats seules)", 0.0, 1.0, 0.5, 0.1, key="g_vois_poids")
    kit_v = kit_par_slots(tout["tab"]["kit"], df_eff, SLOTS[slots_v], t.index)
    esp = construire_espace(t, kit_v, poids)
    c1, c2 = st.columns([3, 1])
    noms_t = dict(zip(t["nom_complet"], t.index))
    perso_v = c1.selectbox("Perso", sorted(noms_t), key="g_vois_perso")
    k = c2.slider("Nombre de voisins", 3, 10, 5, key="g_vois_k")
    montrer(*fig_voisins(esp, noms_t[perso_v], k), "voisins")
    n_groupes = st.slider("Nombre de groupes", 2, min(12, len(t) - 1), min(8, len(t) - 1), key="g_dendro_n")
    fig_d, tab_d, groupe = fig_dendrogramme(esp, n_groupes)
    montrer(fig_d, tab_d, "dendro")
    choix_g = st.selectbox("Voir les persos d'un groupe", list(tab_d["groupe"]), key="g_dendro_g")
    st.dataframe(t.loc[groupe[groupe == choix_g].index, ["nom_complet", "element", "arme", "famille"]],
                 hide_index=True, width="stretch")

    # ---------- ACP ----------
    titre_avec_aide(
        "Carte 2D des persos (ACP)",
        quoi="Les 8 stats résumées en 2 axes (analyse en composantes principales) : chaque point est un perso, les "
             "flèches montrent dans quelle direction chaque stat augmente.",
        sert="Voir d'un seul coup d'œil comment les persos se répartissent : qui est « tank », qui est « attaquant », "
             "et si un élément ou une arme forme un groupe à part.",
        lire="Deux persos proches sur la carte ont des stats proches. Un point loin du centre dans la direction d'une "
             "flèche a beaucoup de cette stat. Le titre de chaque axe donne la part de l'information qu'il garde et ses "
             "3 stats principales. Le tableau « eta² » dit combien la catégorie explique l'axe (0 = rien, 1 = tout).",
        limites="Deux axes ne gardent qu'une partie de l'information (voir le titre) : deux points proches peuvent "
                "différer sur ce qui n'est pas affiché. Les noms affichés sont ceux des persos les plus excentrés.")
    c1, c2 = st.columns(2)
    couleur = c1.selectbox("Couleur selon", ["famille", "element", "arme"], format_func=lambda c: NOMS_PAR[c],
                           key="g_acp_couleur")
    n_noms = c2.slider("Noms affichés (les plus excentrés)", 0, 15, 5, key="g_acp_noms")
    fig_a, charges, eta = fig_acp(preparer_acp(t), couleur, n_noms)
    montrer(fig_a, charges, "acp")
    st.dataframe(eta, hide_index=True)

    # ---------- offre / demande ----------
    titre_avec_aide(
        "Offre et demande d'états ennemis",
        quoi="Pour 3 états qu'on peut infliger à l'ennemi (dégâts continus, malus de résistance physique/magique, "
             "malus de résistance d'élément) : qui les fournit, qui en profite (dégâts augmentés contre un ennemi dans "
             "cet état), qui fait les deux.",
        sert="Voir quels persos sont autonomes et lesquels dépendent d'un allié : utile pour composer une équipe.",
        lire="Vert-bleu (aqua) = autonome. Orange = profite sans fournir : il lui faut un coéquipier fournisseur. "
             "« autonomie » = part des profitants qui fournissent eux-mêmes. Carte par élément : « 5/2 » = 5 fournisseurs, "
             "2 profitants ; bleu = plus de fournisseurs que de profitants.",
        limites="Détection par mots-clés dans les descriptions, au niveau de compétence du perso (niveau 100 : "
                "compétences 3/3/2 et incarnation 3 ; niveau 120 : niveau max). Au niveau 1 du filtre, on utilise la "
                "règle du niveau 100. Certains effets ne sont pas encore reconnus (note de ton notebook).")
    avec_inc = st.checkbox("Inclure l'incarnation", value=True, key="g_od_inc")
    od = table_offre_demande(tout["persos"], set(t.index), 120 if niveau == 120 else 100, avec_inc)
    f1, f2, r_od = fig_offre_demande(od)
    st.plotly_chart(appliquer_survol(f1), width="stretch", key="od1")
    montrer(f2, r_od, "od2")

    # ---------- complexité ----------
    titre_avec_aide(
        "Complexité du kit et puissance",
        quoi="Pour chaque perso : le nombre d'effets différents de son kit (hors Recollection Field) et un indice de "
             "puissance (moyenne de ses stats ramenées à la même échelle, avec la meilleure de ATK/MATK).",
        sert="Répondre à : « un kit plus riche va-t-il avec des stats plus fortes (ou plus faibles) ? »",
        lire="ρ (rho, corrélation de Spearman) : 0 = pas de lien, +1 = plus d'effets va toujours avec plus de puissance, "
             "-1 = l'inverse. Entre crochets, l'intervalle à 95 % : s'il contient 0, le lien n'est pas établi. Le "
             "deuxième graphique fait la même chose stat par stat.",
        limites="Corrélation ne veut pas dire cause. L'intervalle vient d'un ré-échantillonnage (bootstrap) : il peut "
                "bouger un peu d'une version de données à l'autre.")
    avec_rf = st.checkbox("Compter les Recollection Field", value=False, key="g_cx_rf")

    @st.cache_data(show_spinner="Calcul des corrélations…")
    def complexite(ids, avec_rf, version):
        return fig_complexite(table_complexite(t.loc[list(ids)], df_eff, avec_rf))
    f1, f2, r_cx = complexite(tuple(t.index), avec_rf, tout["version"])
    st.plotly_chart(appliquer_survol(f1), width="stretch", key="cx1")
    montrer(f2, r_cx, "cx2")

    # ---------- triangles ----------
    titre_avec_aide(
        "Triangles de budget",
        quoi="Deux triangles. Stats : la part de la force du perso qui va à l'attaque (ATK/MATK + CRIT), à la défense "
             "(HP + DEF + MDEF) et au tempo (MP + SPD), chaque stat comparée à la moyenne. Kit : la part de ses effets qui "
             "visent lui-même, ses alliés ou les ennemis.",
        sert="Voir si les développeurs donnent à tous les persos le même « budget » réparti différemment, et quels "
             "persos sont spécialisés.",
        lire="Un point près d'un coin = perso très tourné vers ce côté ; au centre (croix grise = moyenne) = équilibré. "
             "Le triangle est zoomé sur les données : lis les graduations sur les bords. Survole un point pour son nom.",
        limites="Kit : seulement les persos avec au moins 3 effets classés (Recollection Field, attaque supplémentaire "
                "et contreparties sont ignorés). Les points du triangle de kit sont légèrement décalés pour ne pas se "
                "superposer.")
    f1, f2, r_tr = fig_triangles(t, df_eff)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(appliquer_survol(f1), width="stretch", key="tri1")
    with c2:
        st.plotly_chart(appliquer_survol(f2), width="stretch", key="tri2")
    with st.expander("Voir les données"):
        st.dataframe(r_tr, hide_index=True, width="stretch")
