import streamlit as st
import spacy
import json
import re

st.set_page_config(layout="wide")
st.title("Analyseur de textes sacrés")

CATEGORIES_PERSONNALISEES = {
    "DEITY", "PROPHET_FIGURE", "CELESTIAL_BEING", "SACRED_PLACE",
    "SACRED_OBJECT", "CELESTIAL_PHENOMENON", "CONCEPT_KNOWLEDGE", "PEOPLE_GROUP"
}

@st.cache_resource
def charger_nlp():
    nlp = spacy.load("en_core_web_sm")
    ruler = nlp.add_pipe("entity_ruler", before="ner")
    ruler.from_disk("../sacred-texts-json/patterns_religieux.jsonl")
    return nlp

nlp = charger_nlp()

livre = st.selectbox("Livre", ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"], key="livre_select")

with open(f"../sacred-texts-json/torah/{livre}.json", "r", encoding="utf-8") as f:
    data = json.load(f)

nb_chapitres = len(data["text"])
chapitre = st.number_input("Chapitre", min_value=1, max_value=nb_chapitres, value=1, key=f"chapitre_{livre}")

versets = data["text"][chapitre - 1]
texte_complet = ""
for i, verset in enumerate(versets, start=1):
    propre = re.sub(r"<i class=\"footnote\">.*?</i>", "", verset)
    propre = re.sub(r"<[^>]+>", "", propre).strip()
    texte_complet += f"{propre} "

doc = nlp(texte_complet)

ents_filtrees = [e for e in doc.ents if e.label_ in CATEGORIES_PERSONNALISEES]

st.subheader("Texte")
st.write(texte_complet)

st.subheader("Entites detectees (categories personnalisees uniquement)")
if ents_filtrees:
    for ent in ents_filtrees:
        st.write(f"**{ent.text}** — {ent.label_}")
else:
    st.write("Aucune entite personnalisee detectee dans ce chapitre.")