"""Page Vérifier mon perso : saisie à la main ou import d'un JSON, puis diagnostic."""
import streamlit as st

from app_commun import AIDE_RAPPORT, afficher_rapport, aide, donnees, titre_avec_aide
from saoub.donnees import GRILLE_100, STATS
from saoub.export import importer_persos
from saoub.moteur_kit import lister_effets
from saoub.validation import valider_perso

tout = donnees()
moteur, moteur_kit = tout["moteur"], tout["moteur_kit"]
ref = moteur["ref"]

gauche, droite = st.columns([12, 1], vertical_alignment="bottom")
gauche.title("🔍 Vérifier mon perso")
with droite:
    aide("Vérifier mon perso",
         quoi="Le diagnostic d'un perso que tu as imaginé ou reçu d'un ami, comparé aux vrais persos du jeu.",
         sert="Savoir si un perso « ressemble » à ce que font les développeurs avant de le proposer au groupe.",
         lire="Deux façons de donner le perso : le saisir (8 stats au niveau 100 + effets), ou importer un JSON. "
              "JSON acceptés : une fiche exportée par l'application, un fichier complet {\"personnages\": [...]}, "
              "le format simple {\"stats\": {...}, \"kit\": [...]}, ou un perso au format du jeu dont les compétences "
              "sont écrites (le kit est alors déduit des descriptions).",
         limites="Les stats sont comparées au niveau 100. Un effet inconnu de l'application est ignoré (et signalé).")

effets = lister_effets(moteur_kit)
connus = set(effets["effet"])
saisie, import_json = st.tabs(["✍️ Saisir", "📂 Importer un JSON"])
perso = None

with saisie:
    colonnes = st.columns(4)
    stats = {}
    for i, s in enumerate(STATS):
        pas = GRILLE_100.get(s, 1)
        defaut = int(ref[s].median() // pas * pas)
        stats[s] = colonnes[i % 4].number_input(f"{s} (de {int(ref[s].min())} à {int(ref[s].max())})", min_value=0,
                                                value=defaut, step=pas, key=f"v_{s}")
    kit = st.multiselect("Effets et rôles", list(effets["effet"]), key="v_kit", placeholder="Aucun effet")
    if st.button("Vérifier", type="primary", key="v_saisie"):
        st.session_state["v_perso"] = dict(nom="Perso saisi", stats=stats, kit=kit)

with import_json:
    fichier = st.file_uploader("Fichier JSON", type="json")
    texte = st.text_area("…ou colle le JSON ici", height=120, key="v_texte")
    contenu = fichier.getvalue().decode("utf-8") if fichier else texte
    if contenu.strip():
        try:
            importes = importer_persos(contenu, tout["effets_perso"])
        except (ValueError, KeyError, TypeError, AttributeError) as erreur:
            st.error(f"JSON illisible : {erreur}")
        else:
            i = st.selectbox(f"{len(importes)} perso(s) trouvé(s)", range(len(importes)),
                             format_func=lambda k: importes[k]["nom"]) if len(importes) > 1 else 0
            if st.button("Vérifier", type="primary", key="v_import"):
                st.session_state["v_perso"] = importes[i]

if "v_perso" in st.session_state:
    perso = st.session_state["v_perso"]
    titre_avec_aide(f"Diagnostic : {perso['nom']}", **AIDE_RAPPORT)
    inconnus = [e for e in perso["kit"] if e not in connus]
    if inconnus:
        st.warning(f"Effet(s) inconnu(s) de l'application, ignoré(s) : {', '.join(inconnus)}. "
                   "Tu peux les créer dans Création → Effets personnalisés.")
    afficher_rapport(valider_perso(moteur, moteur_kit, dict(stats=perso["stats"], kit=[e for e in perso["kit"] if e in connus])))
