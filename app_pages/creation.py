"""Page Création : réglages (listes déroulantes) -> propositions de persos -> validation de chacune."""
import json
import random

import pandas as pd
import streamlit as st

from app_commun import AIDE_RAPPORT, afficher_rapport, chemins, donnees, recharger, titre_avec_aide
from saoub.creation import creer_persos
from saoub.donnees import GRILLE_100, STATS
from saoub.effets import CATEGORIES_CREABLES, ajouter_effet_perso, liste_effets, supprimer_effet_perso
from saoub.export import ajouter_au_fichier, en_texte_json, fiche_perso, id_libre
from saoub.interface import FAMILLES, NIVEAUX_STAT, ORIGINALITE, cle_params, contraintes_depuis_choix, resume
from saoub.moteur_kit import lister_effets
from saoub.validation import valider_perso

tout = donnees()
moteur, moteur_kit = tout["moteur"], tout["moteur_kit"]
ref = moteur["ref"]
etat = st.session_state


@st.cache_data(max_entries=100, show_spinner="Création des persos…")
def generer(cle, graine, version, _moteur, _moteur_kit):
    """Mis en cache : revenir à des réglages + graine déjà vus est instantané. version = date du chargement des données."""
    p = json.loads(cle)
    persos, infos = creer_persos(_moteur, _moteur_kit, p["contraintes"], p["imposes"], n=p["n"], graine=graine,
                                 diversifier=p["diversifier"], **ORIGINALITE[p["originalite"]])
    rapports = [valider_perso(_moteur, _moteur_kit, x) for x in persos]
    return persos, infos, rapports


# ---------- valeurs par défaut des réglages (une seule fois par session) ----------
defauts = {"graine": 0, "c_famille": next(iter(FAMILLES)), "c_effets": [], "c_orig": "Classique", "c_div": True, "c_n": 5,
           "historique": []}
for s in STATS:
    defauts[f"c_niv_{s}"] = "Libre"
    defauts[f"c_egal_{s}"] = int(ref[s].median() // GRILLE_100.get(s, 1) * GRILLE_100.get(s, 1))
    defauts[f"c_min_{s}"], defauts[f"c_max_{s}"] = int(ref[s].min()), int(ref[s].max())
for k, v in defauts.items():
    etat.setdefault(k, v)


def lire_reglages():
    choix = {s: {"niveau": etat[f"c_niv_{s}"], "egal": etat[f"c_egal_{s}"], "min": etat[f"c_min_{s}"],
                 "max": etat[f"c_max_{s}"]} for s in STATS}
    return dict(contraintes=contraintes_depuis_choix(etat["c_famille"], choix), imposes=list(etat["c_effets"]),
                originalite=etat["c_orig"], diversifier=etat["c_div"], n=etat["c_n"])


def nouvelle_graine():
    etat["graine"] = random.randint(0, 99999)


def valider_reglages():
    etat["params_valides"] = lire_reglages()
    etat["ui_valide"] = {k: etat[k] for k in etat if str(k).startswith("c_")}


def revenir():
    choix = etat["retour_histo"]
    if choix is None:
        return
    entree = etat["historique"][choix]
    for k, v in entree["ui"].items():
        etat[k] = v
    etat["graine"], etat["params_valides"], etat["ui_valide"] = entree["graine"], entree["params"], entree["ui"]
    etat["retour_histo"] = None


def afficher_historique():
    libelles = [h["resume"] for h in etat["historique"]]
    if libelles:
        zone_historique.selectbox("Revenir à un résultat précédent", range(len(libelles)), index=None, key="retour_histo",
                                  format_func=lambda i: libelles[i], on_change=revenir,
                                  placeholder=f"{len(libelles)} résultat(s) dans l'historique")


# ---------- en-tête et tutoriel ----------
gauche, droite = st.columns([12, 1], vertical_alignment="bottom")
gauche.title("🛠️ Création de perso")
with droite:
    with st.popover("?", help="Tutoriel de la page"):
        st.markdown("""#### Tutoriel : créer un perso en 4 étapes
1. **Stats** : choisis la famille et, si tu veux, un niveau pour certaines stats (« Très haut », « Valeur exacte »…). Laisse « Libre » ce qui t'est égal : le moteur le déduira de ce que font les développeurs.
2. **Kit** : choisis les effets ou rôles que le perso doit **absolument** avoir. Le moteur complète le reste.
3. **Originalité et graine** : « Classique » ressemble aux vrais persos, « Audacieux » s'en éloigne. La **graine** est le numéro du tirage : même réglages + même graine = mêmes persos.
4. Clique **Créer**, puis ouvre chaque proposition pour lire son diagnostic.

**À savoir** : l'outil propose des persos *plausibles* (qui ressemblent aux 181 vrais persos non offerts, niveau 100), pas des persos *forts* : il n'a aucune donnée de combat. Chaque section a son propre bouton « ? ».""")

# ---------- 1. Stats ----------
titre_avec_aide(
    "1. Stats",
    quoi="Les 8 stats au niveau 100. Chaque liste déroulante fixe une contrainte sur une stat.",
    sert="Orienter le perso : un tank (HP, DEF, MDEF hauts), un canon de verre (ATK haute, DEF basse), etc.",
    lire="« Très haut » = parmi les 20 % les plus hauts des vrais persos. « Valeur exacte » est arrondie à la grille du jeu "
         "(HP par 75, ATK/MATK par 25, DEF/MDEF par 15). Les stats « Libre » suivent les corrélations réelles "
         "(ex. : plus de DEF va souvent avec plus de HP).",
    limites="Trop de contraintes ensemble peuvent être impossibles : un message te demande alors d'en relâcher une.")
st.selectbox("Famille", list(FAMILLES), key="c_famille")
colonnes = st.columns(4)
for i, s in enumerate(STATS):
    with colonnes[i % 4]:
        st.selectbox(f"{s}  (de {int(ref[s].min())} à {int(ref[s].max())})", list(NIVEAUX_STAT), key=f"c_niv_{s}")
        pas = GRILLE_100.get(s, 1)
        if etat[f"c_niv_{s}"] == "Valeur exacte…":
            st.number_input(f"{s} exact", step=pas, min_value=0, key=f"c_egal_{s}", label_visibility="collapsed")
        elif etat[f"c_niv_{s}"] == "Fourchette…":
            a, b = st.columns(2)
            a.number_input("min", step=pas, min_value=0, key=f"c_min_{s}")
            b.number_input("max", step=pas, min_value=0, key=f"c_max_{s}")

# ---------- 2. Kit ----------
titre_avec_aide(
    "2. Kit (effets imposés)",
    quoi="Les rôles (Break, Charge, Mode enhance) et effets que le perso doit avoir. Le nombre entre parenthèses = "
         "nombre de vrais persos (non offerts) qui l'ont.",
    sert="Partir d'une idée (« un perso à dégâts continus ») et laisser le moteur compléter un kit cohérent.",
    lire="Laisse vide pour un kit typique. Le moteur ajoute les effets qui vont souvent avec ceux que tu imposes. "
         "La taille du kit suit celle des vrais persos (médiane 5).",
    limites="Un effet présent chez moins de 10 vrais persos donne peu d'exemples : le moteur s'appuie alors sur les "
            "fréquences générales. Les compétences (1, 2, 3, incarnation) ne sont pas distinguées.")
effets = lister_effets(moteur_kit)
comptes = dict(zip(effets["effet"], effets["persos"]))
etat["c_effets"] = [e for e in etat["c_effets"] if e in comptes]      # un effet personnalisé supprimé disparaît
st.multiselect("Effets et rôles imposés", list(effets["effet"]), key="c_effets", placeholder="Aucun : kit libre",
               format_func=lambda e: f"{e} ({comptes[e]} persos)" if comptes[e] else f"{e} (personnalisé)")

with st.expander(f"➕ Effets personnalisés ({len(tout['effets_perso'])}) et phrases à classer"):
    titre_avec_aide(
        "Effets personnalisés",
        quoi="Des effets qui n'existent pas (encore) dans le jeu, enregistrés dans data/effets_personnalises.json.",
        sert="Imaginer une nouvelle mécanique et l'imposer dans un kit, ou nommer une phrase de compétence qu'aucune "
             "règle ne reconnaît (« phrases à classer », par exemple après une mise à jour du jeu).",
        lire="« Se comporte comme » : le moteur tire le reste du kit comme si le perso avait cet effet existant. "
             "Sans modèle, l'effet est ajouté au kit sans influencer le reste. Si tu rattaches des phrases à classer, "
             "les persos qui les ont comptent comme de vrais exemples.",
        limites="Un effet sans phrase n'a aucune donnée réelle : chaque perso qui l'utilise reçoit une alerte. "
                "Créer ou supprimer un effet recharge les moteurs (≈ 5 s, pour tout le monde).")
    if "message_effet" in etat:
        st.success(etat.pop("message_effet"))
    a_classer = tout["a_classer"]
    st.markdown(f"**Phrases à classer** : {len(a_classer)}")
    if len(a_classer):
        st.dataframe(a_classer.rename(columns={"p": "phrase (nombres remplacés par N)", "nb_persos": "persos"}),
                     hide_index=True, width="stretch")
    jeu = liste_effets(tout["df_eff"], tout["effets_perso"])["jeu"]
    with st.form("nouvel_effet", clear_on_submit=True):
        st.markdown("**Créer un effet**")
        nom = st.text_input("Nom", placeholder="ex. : Vol de MP", key="n_nom")
        f1, f2 = st.columns(2)
        categorie = f1.selectbox("Catégorie", CATEGORIES_CREABLES, index=len(CATEGORIES_CREABLES) - 1, key="n_cat")
        modele = f2.selectbox("Se comporte comme", ["(aucun modèle)"] + jeu, key="n_modele")
        description = st.text_area("Description (facultatif)", height=68)
        phrases = st.multiselect("Phrases à classer rattachées (facultatif)", list(a_classer["p"]), key="n_phrases")
        if st.form_submit_button("Créer l'effet"):
            try:
                ajouter_effet_perso(nom, categorie, jeu, se_comporte_comme=None if modele == "(aucun modèle)" else modele,
                                    description=description, phrases=phrases, chemin=chemins()["effets"])
            except ValueError as erreur:
                st.error(str(erreur))
            else:
                etat["message_effet"] = f"Effet « {' '.join(nom.split())} » créé : il est dans la liste du kit."
                recharger()
                st.rerun()
    if tout["effets_perso"]:
        st.markdown("**Effets existants**")
        st.dataframe([{"nom": e["nom"], "catégorie": e["categorie"], "se comporte comme": e["se_comporte_comme"] or "—",
                       "phrases": len(e["phrases"]), "créé le": e["cree_le"]} for e in tout["effets_perso"]],
                     hide_index=True, width="stretch")
        d1, d2 = st.columns([3, 1], vertical_alignment="bottom")
        a_supprimer = d1.selectbox("Supprimer un effet", [e["nom"] for e in tout["effets_perso"]], index=None,
                                   placeholder="Choisis un effet", key="n_suppr")
        if d2.button("Supprimer", disabled=a_supprimer is None, key="n_bouton_suppr"):
            supprimer_effet_perso(a_supprimer, chemin=chemins()["effets"])
            etat["message_effet"] = f"Effet « {a_supprimer} » supprimé."
            recharger()
            st.rerun()

# ---------- 3. Originalité, nombre, graine ----------
titre_avec_aide(
    "3. Originalité et graine",
    quoi="L'originalité règle à quel point les persos s'éloignent des vrais. La graine est le numéro du tirage au hasard.",
    sert="Graine : retrouver exactement un résultat (même réglages + même graine = mêmes persos). "
         "🎲 en tire une nouvelle ; tu peux aussi la taper à la main.",
    lire="Classique : comme les vrais persos. Original : écarte les persos trop proches d'un vrai (distance ≥ 0,6) "
         "et varie davantage le kit. Audacieux : élargit les stats (peut sortir des valeurs vues) et le kit. "
         "« Propositions variées » : les persos proposés sont choisis pour être différents entre eux.",
    limites="Rare ne veut pas dire intéressant : l'outil ne sait pas si un perso original est bon en combat.")
c1, c2, c3 = st.columns([3, 2, 2])
c1.select_slider("Originalité", list(ORIGINALITE), key="c_orig")
c2.slider("Nombre de propositions", 1, 8, key="c_n")
c3.toggle("Propositions variées", key="c_div")
g1, g2, g3 = st.columns([2, 1, 4], vertical_alignment="bottom")
g1.number_input("Graine", min_value=0, max_value=99999, step=1, key="graine")
g2.button("🎲", help="Nouvelle graine au hasard", on_click=nouvelle_graine)
zone_historique = g3.empty()            # remplie en fin de page, une fois l'historique à jour

st.button("Créer", type="primary", on_click=valider_reglages, width="stretch")

# ---------- 4. Résultats ----------
if "params_valides" not in etat:
    st.info("Règle ce que tu veux puis clique **Créer**.")
    st.stop()
if {k: etat[k] for k in etat["ui_valide"]} != etat["ui_valide"]:
    st.caption("✏️ Réglages modifiés : clique **Créer** pour les appliquer (la graine, elle, s'applique tout de suite).")

params, graine = etat["params_valides"], etat["graine"]
try:
    persos, infos, rapports = generer(cle_params(params), graine, tout["version"], moteur, moteur_kit)
except ValueError as erreur:
    st.error(f"Impossible de créer ces persos : {erreur}")
    afficher_historique()
    st.stop()

entree = dict(resume=resume(params, graine), graine=graine, params=params, ui=etat["ui_valide"])
if all(h["resume"] != entree["resume"] for h in etat["historique"]):
    etat["historique"].insert(0, entree)
    del etat["historique"][20:]
afficher_historique()

titre_avec_aide(
    "4. Propositions",
    quoi="Les persos proposés, puis le diagnostic de chacun dans son onglet.",
    sert="Comparer les propositions d'un coup d'œil, puis vérifier celle qui te plaît.",
    lire="Distance : ressemblance des stats avec le vrai perso le plus proche. Entre vrais persos, elle vaut en général "
         "0,41 et 95 % sont sous 0,78. Percentile : 90 = plus haut que 90 % des vrais persos. ⚠ = point à vérifier, "
         "pas forcément une erreur (21 à 32 % des vrais persos sont hors grille, par exemple).",
    limites="Stats et kit sont tirés séparément : dans les vraies données, ils n'ont pas de lien mesurable.")
for message in infos["stats"]["messages"]:
    st.info(message)
for alerte in infos["stats"]["alertes"] + infos["kit"]["alertes"]:
    st.warning(alerte)
st.caption(f"Tirages de stats acceptés : {infos['stats']['acceptes']} sur {infos['stats']['n_tirages']} "
           f"({infos['stats']['taux']:.1%}) · vrais persos avec tous les effets imposés : {infos['kit']['n_reels']}")

apercu = pd.DataFrame([{"Perso": f"Perso {i + 1}", "Famille": r["famille"], **x["stats"], "Taille du kit": len(x["kit"]),
                        "Distance": round(r["distance"], 2), "⚠": len(r["alertes"])}
                       for i, (x, r) in enumerate(zip(persos, rapports))])
st.dataframe(apercu, hide_index=True, width="stretch")

for onglet, r in zip(st.tabs([f"Perso {i + 1}" for i in range(len(persos))]), rapports):
    with onglet:
        afficher_rapport(r)

# ---------- 5. Export ----------
titre_avec_aide(
    "5. Exporter un perso",
    quoi="La fiche du perso choisi au format JSON du jeu : stats aux niveaux 1, 80, 100 et 120, kit proposé, réglages.",
    sert="Garder un perso (fichier data/personage_new.json) ou l'envoyer à tes amis (téléchargement).",
    lire="L'id est proposé automatiquement (premier id libre à partir de 999000001). Les niveaux 1, 80 et 120 sont "
         "déduits du niveau 100 avec les rapports des vrais persos (exacts pour HP, ATK, MATK, DEF, MDEF).",
    limites="Les compétences (noms, textes, puissances, MP) sont des emplacements vides à écrire à la main.")
elements = sorted({p["element"] for p in tout["persos"] if not p["free"]})
armes = sorted({p["arme"] for p in tout["persos"] if not p["free"]})
etat.setdefault("e_id", id_libre(tout["persos"], chemins()["nouveaux"]))
e1, e2, e3 = st.columns(3)
choix = e1.selectbox("Perso à exporter", range(len(persos)), format_func=lambda i: f"Perso {i + 1}", key="e_choix")
nom = e2.text_input("Nom", key="e_nom", placeholder="ex. : Eugeo")
titre = e3.text_input("Titre", key="e_titre", placeholder="ex. : Chevalier de glace")
e4, e5, e6 = st.columns(3)
element = e4.selectbox("Élément", elements, key="e_element")
arme = e5.selectbox("Arme", armes, key="e_arme")
id_perso = e6.number_input("Id", min_value=1, step=1, key="e_id")
description = st.text_area("Description (facultatif)", key="e_description", height=68)

if not nom.strip() or not titre.strip():
    st.info("Donne un nom et un titre au perso pour pouvoir l'exporter.")
    st.stop()
titre_complet = titre.strip() if titre.strip().startswith("[") else f"[{titre.strip()}]"
try:
    fiche = fiche_perso(persos[choix], tout["persos"], int(id_perso), nom.strip(), titre_complet, element, arme,
                        description=description, parametres=dict(graine=graine, **params))
except ValueError as erreur:
    st.error(str(erreur))
    st.stop()


def ajouter():
    try:
        etat["message_export"] = ("success", ajouter_au_fichier(fiche, chemins()["nouveaux"], remplacer=etat["e_remplacer"]))
        etat["e_id"] = id_libre(tout["persos"], chemins()["nouveaux"])
    except ValueError as erreur:
        etat["message_export"] = ("error", str(erreur))


x1, x2, x3 = st.columns([2, 2, 1], vertical_alignment="center")
x1.download_button("⬇️ Télécharger la fiche (JSON)", en_texte_json(fiche), file_name=f"perso_{fiche['id']}.json",
                   mime="application/json", width="stretch")
x2.button("💾 Ajouter à data/personage_new.json", on_click=ajouter, width="stretch")
x3.checkbox("remplacer", key="e_remplacer", help="Écrase le perso du fichier qui a le même id")
if "message_export" in etat:
    genre, texte = etat.pop("message_export")
    (st.success if genre == "success" else st.error)(texte)
