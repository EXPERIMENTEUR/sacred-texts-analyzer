# -*- coding: ascii -*-
"""Graphe de personnages du Popol Vuh : entites reconnues (motifs du depot) reliees quand elles
apparaissent dans le meme paragraphe. Le poids d'un lien = nombre de paragraphes communs.
Ne montre qu'une proximite dans le texte, pas une relation etablie."""
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations

import streamlit as st

CATEGORIES_GRAPHE = {"DEITY": "Dieux", "PROPHET_FIGURE": "Personnages", "NEGATIVE_ENTITY": "Adversaires",
                     "SACRED_PLACE": "Lieux", "PEOPLE_GROUP": "Peuples"}
COULEURS = {"DEITY": "#e6a817", "PROPHET_FIGURE": "#2a7fb8", "NEGATIVE_ENTITY": "#c0392b",
            "SACRED_PLACE": "#2e8b57", "PEOPLE_GROUP": "#8e5ea2"}

def _cle(nom):
    s = nom.lower().replace("\u0153", "oe")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]", "", s)
    return s[:-1] if len(s) > 5 and s.endswith("s") else s

@st.cache_data(show_spinner="Construction du graphe...")
def construire(textes, ids, _nlp, categories):
    surfaces, cats, presence = defaultdict(Counter), defaultdict(Counter), defaultdict(set)
    par_paragraphe = []
    # Seul le repereur de motifs sert ici : on coupe le reste du modele (beaucoup plus rapide)
    desactiver = [n for n in _nlp.pipe_names if n != "entity_ruler"]
    for i, doc in enumerate(_nlp.pipe(list(textes), batch_size=200, disable=desactiver)):
        cles = set()
        for e in doc.ents:
            if e.label_ in categories:
                k = _cle(e.text)
                if k:
                    surfaces[k][e.text] += 1
                    cats[k][e.label_] += 1
                    cles.add(k)
        for k in cles:
            presence[k].add(i)
        par_paragraphe.append(cles)
    noeuds = {}
    for k in surfaces:
        meilleur = max(surfaces[k].items(), key=lambda kv: (kv[1], "-" in kv[0], kv[0]))[0]
        noeuds[k] = {"nom": meilleur, "cat": cats[k].most_common(1)[0][0], "paragraphes": len(presence[k]),
                     "mentions": sum(surfaces[k].values())}
    aretes = defaultdict(list)
    for i, cles in enumerate(par_paragraphe):
        for a, b in combinations(sorted(cles), 2):
            aretes[(a, b)].append(i)
    return noeuds, dict(aretes)

def _figure(noeuds, aretes, poids_min, actives):
    import networkx as nx
    import plotly.graph_objects as go
    g = nx.Graph()
    for (a, b), idx in aretes.items():
        if len(idx) >= poids_min and noeuds[a]["cat"] in actives and noeuds[b]["cat"] in actives:
            g.add_edge(a, b, weight=len(idx))
    if g.number_of_nodes() == 0:
        return None, g
    pos = nx.spring_layout(g, weight="weight", seed=7, k=1.2 / (g.number_of_nodes() ** 0.5))
    fig = go.Figure()
    wmax = max(d["weight"] for _, _, d in g.edges(data=True))
    for a, b, d in g.edges(data=True):
        fig.add_trace(go.Scatter(x=[pos[a][0], pos[b][0], None], y=[pos[a][1], pos[b][1], None], mode="lines",
                                 line=dict(width=0.5 + 5.0 * d["weight"] / wmax, color="rgba(120,120,120,0.45)"),
                                 hoverinfo="skip", showlegend=False))
    for cat, etiquette in CATEGORIES_GRAPHE.items():
        ks = [k for k in g.nodes if noeuds[k]["cat"] == cat]
        if not ks:
            continue
        textes = []
        for k in ks:
            voisins = sorted(g[k].items(), key=lambda kv: -kv[1]["weight"])[:5]
            lien = ", ".join("%s (%d)" % (noeuds[v]["nom"], d["weight"]) for v, d in voisins)
            textes.append("%s - %s<br>%d paragraphes, %d mentions<br>Liens : %s" % (
                noeuds[k]["nom"], etiquette, noeuds[k]["paragraphes"], noeuds[k]["mentions"], lien))
        fig.add_trace(go.Scatter(
            x=[pos[k][0] for k in ks], y=[pos[k][1] for k in ks], mode="markers+text", name=etiquette,
            text=[noeuds[k]["nom"] for k in ks], textposition="top center", textfont=dict(size=10),
            hovertext=textes, hoverinfo="text",
            marker=dict(size=[8 + 3 * noeuds[k]["paragraphes"] ** 0.5 for k in ks], color=COULEURS[cat],
                        line=dict(width=1, color="white"))))
    fig.update_layout(height=620, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(visible=False),
                      yaxis=dict(visible=False), legend=dict(orientation="h"))
    return fig, g

def afficher_graphe_popol(chapitres, nettoyer, nlp):
    try:
        import networkx  # noqa: F401
        import plotly.graph_objects  # noqa: F401
    except ImportError:
        st.warning("Bibliotheques manquantes. Installation : python -m pip install networkx plotly")
        return
    st.caption("Deux entites sont reliees quand elles apparaissent dans le meme paragraphe de la traduction de "
               "Brasseur ; le poids d'un lien est le nombre de paragraphes communs. Cela montre une proximite dans "
               "le texte, pas une relation etablie. Seules les entites des motifs du depot sont prises en compte.")
    if nlp is None:
        st.warning("Modele francais manquant : python -m spacy download fr_core_news_sm")
        return
    if not st.checkbox("Calculer le graphe (quelques secondes la premiere fois)", key="graphe_actif"):
        return
    portee = st.selectbox("Portee", ["Livre entier"] + [n for n, _ in chapitres], key="graphe_portee")
    textes, ids = [], []
    for nom, paras in chapitres:
        if portee != "Livre entier" and nom != portee:
            continue
        for i, p in enumerate(paras):
            textes.append(nettoyer(p))
            ids.append((nom, i + 1))
    noeuds, aretes = construire(tuple(textes), tuple(ids), nlp, tuple(CATEGORIES_GRAPHE))
    if not aretes:
        st.info("Aucun lien : pas assez d'entites dans ce passage.")
        return
    wmax = max(len(v) for v in aretes.values())
    col1, col2 = st.columns(2)
    with col1:
        actives = st.multiselect("Categories", list(CATEGORIES_GRAPHE), default=list(CATEGORIES_GRAPHE),
                                 format_func=lambda c: CATEGORIES_GRAPHE[c], key="graphe_cats")
    with col2:
        poids_min = st.slider("Poids minimum d'un lien (paragraphes communs)", 1, max(2, wmax),
                              min(2, wmax) if portee == "Livre entier" else 1, key="graphe_poids")
    fig, g = _figure(noeuds, aretes, poids_min, set(actives))
    if fig is None:
        st.info("Aucun lien ne passe ces filtres.")
        return
    st.caption("%d entites, %d liens affiches." % (g.number_of_nodes(), g.number_of_edges()))
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)
    top = sorted(((len(idx), a, b) for (a, b), idx in aretes.items()
                  if noeuds[a]["cat"] in actives and noeuds[b]["cat"] in actives), reverse=True)[:25]
    st.markdown("**Liens les plus forts**")
    st.dataframe([{"Entite A": noeuds[a]["nom"], "Entite B": noeuds[b]["nom"], "Paragraphes communs": n}
                  for n, a, b in top], hide_index=True)
    if top:
        etiquettes = ["%s - %s (%d)" % (noeuds[a]["nom"], noeuds[b]["nom"], n) for n, a, b in top]
        choix = st.selectbox("Verifier un lien dans le texte", etiquettes, key="graphe_verif")
        n, a, b = top[etiquettes.index(choix)]
        for i in aretes[(a, b)][:5]:
            nom, num = ids[i]
            st.markdown("*%s, paragraphe %d* : %s" % (nom, num, textes[i][:600]))
