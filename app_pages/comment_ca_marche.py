"""Page « Comment ça marche ? » : l'outil expliqué simplement, avec les chiffres de contrôle calculés en direct."""
import streamlit as st

from app_commun import donnees
from saoub.moteur_kit import valider_moteur_kit
from saoub.moteur_stats import valider_moteur_stats

tout = donnees()
base = tout["tab"]["base"]
n_total, n_free = len(base), int(base["free"].sum())
n_ref = n_total - n_free
moteur_kit = tout["moteur_kit"]


def fr(texte):
    """Virgule décimale française."""
    return texte.replace(".", ",")


@st.cache_data(show_spinner="Calcul des chiffres de contrôle…")
def controles(version):
    return valider_moteur_stats(tout["moteur"]), valider_moteur_kit(moteur_kit)


st.title("📖 Comment ça marche ?")
st.caption("2 minutes de lecture. Les chiffres sont recalculés à partir des données actuelles.")

st.subheader("1. Les données")
st.markdown(f"""
L'outil part des **{n_total} persos** du fichier `data/personnages_fr.json` (tous de rareté 4).
Les **{n_free} persos offerts** (free) sont souvent plus faibles : ils apparaissent dans les graphiques si tu le choisis,
mais l'outil de création apprend **uniquement sur les {n_ref} autres**, pour imiter les persos « normaux » du jeu.

Les **effets** sont lus dans le texte des compétences (au niveau maximal) avec des règles de reconnaissance :
« Inflige des dégâts continus… » devient l'effet *Dégâts continus*. On obtient {tout['df_eff']['effet'].nunique()}
effets différents, plus 3 **rôles** (Break, Charge, Mode enhance) lus dans le type des compétences.
""")

st.subheader("2. Comment l'outil invente des stats")
st.markdown("""
- Les persos se rangent en deux **familles** : *physique* (ATK ≥ MATK) et *magique*. Leurs stats sont très différentes,
  donc l'outil apprend chaque famille séparément.
- Pour chaque famille, il retient la **valeur moyenne** de chaque stat et **la façon dont les stats bougent ensemble**
  (par exemple : un perso avec beaucoup de DEF a souvent beaucoup de HP).
- Quand tu fixes une contrainte (« ATK = 2800 », « SPD très haut »), il **ajuste les autres stats** en conséquence, puis
  tire au hasard **20 000 persos** et garde ceux qui respectent tes choix et restent dans les valeurs déjà vues dans le jeu.
- Les stats sont enfin **arrondies à la grille du jeu** (HP par 75, ATK/MATK par 25, DEF/MDEF par 15) ou à une valeur
  déjà utilisée (MP, CRIT, SPD).
- La **graine** est le numéro du tirage au hasard : mêmes réglages + même graine = mêmes persos.
""")
with st.expander("En savoir plus (vocabulaire statistique)"):
    st.markdown("""
Chaque famille est modélisée par une **loi normale à 8 dimensions** (une moyenne et une matrice de covariance).
Les contraintes « valeur exacte » sont appliquées par **conditionnement gaussien** ; les autres par **tirage par rejet**.
Ce modèle a été préféré à une loi unique pour tous les persos parce qu'il reproduit mieux la forme réelle de l'ATK
(test de Kolmogorov-Smirnov : 0,087 contre 0,159).
""")

st.subheader("3. Comment l'outil invente un kit")
st.markdown(f"""
- Les effets **rares** (moins de 10 persos) sont **regroupés** avec des effets proches, sinon l'outil n'aurait pas assez
  d'exemples. On obtient **{moteur_kit['G'].shape[1]} groupes**.
- L'outil choisit d'abord une **taille de kit** parmi celles des vrais persos, puis ajoute les effets **un par un** : à
  chaque étape, il favorise les effets qu'on voit **souvent avec ceux déjà choisis**.
- Si un effet que tu imposes est rare, il s'appuie davantage sur les fréquences générales (c'est le « lissage »).
- Stats et kit sont tirés **séparément** : dans les vraies données, on n'a pas trouvé de lien utile entre les deux.
""")

st.subheader("4. Comment l'outil vérifie un perso")
st.markdown("""
Pour chaque perso (proposé, saisi ou importé), l'outil compare tout aux vrais persos :
- **percentile** de chaque stat (90 = plus haut que 90 % des vrais persos), **plage** déjà vue, respect de la **grille** ;
- **distance au vrai perso le plus proche** : entre vrais persos, elle vaut en général **0,41**, et 95 % sont sous **0,78**.
  Au-delà, le perso est atypique ; à 0, c'est une copie ;
- **kit le plus proche** et paires d'effets **jamais vues ensemble** chez les vrais persos.

Un ⚠ veut dire « à vérifier », pas « interdit » : par exemple, 21 à 32 % des vrais persos sont hors grille sur une stat.
""")

st.subheader("5. Ce que l'outil ne sait pas faire")
st.markdown("""
- **Il ne connaît pas les combats.** Il propose des persos *plausibles* (qui ressemblent à ce que font les développeurs),
  pas des persos *forts* ni *équilibrés*. Rare ne veut pas dire intéressant.
- Il ne distingue pas les **compétences** (1, 2, 3, incarnation) : le kit est une liste d'effets pour tout le perso.
- Il n'écrit pas les **textes, puissances et coûts en MP** des compétences : la fiche exportée les laisse vides.
- Un **effet personnalisé** n'a aucune donnée réelle : il emprunte le comportement d'un effet existant si tu le choisis.
- Avec peu de persos (moins de 10 dans un groupe), **aucune conclusion** n'est fiable : l'application le signale.
- Lien stats ↔ kit : la page Graphiques (Avancé) montre un **lien faible** entre la richesse du kit et la force des
  stats (ρ ≈ +0,19 sans les offerts). Trop faible pour être utilisé par la création, mais réel.
""")

st.subheader("6. Les chiffres de contrôle")
st.markdown("Pour vérifier que l'outil imite bien le jeu, on génère des milliers de persos **sans contrainte** et on les "
            "compare aux vrais :")
vs, vk = controles(tout["version"])
c1, c2, c3 = st.columns(3)
c1.metric("Physiques : réel → généré", f"{vs['part_physiques_reel']:.0%} → {vs['part_physiques_genere']:.0%}")
c2.metric("Liens entre stats (écart moyen)", fr(f"{vs['ecart_corr_moyen']:.2f}"), help="Écart moyen entre les corrélations "
          "réelles et générées (0 = identiques, 1 = rien à voir)")
c3.metric("Copies exactes d'un vrai perso", f"{vs['copies']:.0%}")
c1, c2, c3 = st.columns(3)
c1.metric("Taille du kit : réel → généré", fr(f"{vk['taille_reelle']:.2f} → {vk['taille_generee']:.2f}"))
c2.metric("Fréquence des effets (écart moyen)", fr(f"{vk['ecart_freq_moyen']:.1f} point"), help="Écart moyen, en points de "
          "pourcentage, entre la fréquence réelle et générée de chaque groupe d'effets")
c3.metric("Kits identiques à un vrai kit", fr(f"{vk['copies']:.1%}"))
with st.expander("Le détail, et les limites connues"):
    st.dataframe(vs["moyennes"], width="stretch")
    st.markdown(f"""
- Les persos générés sont un peu **plus loin** de leur plus proche vrai perso que les vrais entre eux
  ({fr(f"{vs['distance_generee']:.2f}")} contre {fr(f"{vs['distance_reelle']:.2f}")}) : ils sont nouveaux, sans être bizarres.
- L'**écart-type des HP** généré est un peu plus petit que le réel : l'outil rejette les valeurs jamais vues, ce qui
  resserre les extrêmes.
- Les liens entre effets sont bien reproduits dans leur sens (corrélation entre les deux tableaux de liens :
  {fr(f"{vk['corr_liens']:.2f}")}) mais un peu **adoucis** par le lissage.
""")
