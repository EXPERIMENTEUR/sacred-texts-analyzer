import streamlit as st
import spacy
import json
import re

st.set_page_config(layout="wide")
st.title("Analyseur de textes sacrés")

CATEGORIES_PERSONNALISEES = {
    "DEITY", "PROPHET_FIGURE", "CELESTIAL_BEING", "SACRED_PLACE",
    "SACRED_OBJECT", "CELESTIAL_PHENOMENON", "CONCEPT_KNOWLEDGE", "PEOPLE_GROUP",
    "SYMBOLIC_NUMBER", "ELEMENT", "COLOR_SYMBOLIC", "METAL_MATERIAL",
    "CARDINAL_DIRECTION", "CELESTIAL_BODY", "ANIMAL_SYMBOLIC", "PHYSICAL_DESCRIPTOR",
    "SACRED_EVENT", "RITUAL_PRACTICE", "AFTERLIFE_CONCEPT", "SACRED_TEXT",
    "COSMIC_STRUCTURE", "TIME_CONCEPT", "PLANT_SYMBOLIC", "SOUND_PHENOMENON",
    "BODY_PART_SYMBOLIC", "SOCIAL_ROLE"
}

@st.cache_resource
def charger_nlp():
    nlp = spacy.load("en_core_web_sm")
    ruler = nlp.add_pipe("entity_ruler", before="ner")
    ruler.from_disk("../sacred-texts-json/patterns_religieux.jsonl")
    return nlp

nlp = charger_nlp()

LIVRES = {
    "Genesis": "torah", "Exodus": "torah", "Leviticus": "torah", "Numbers": "torah", "Deuteronomy": "torah",
    "Joshua": "neviim", "Judges": "neviim", "I_Samuel": "neviim", "II_Samuel": "neviim",
    "I_Kings": "neviim", "II_Kings": "neviim", "Isaiah": "neviim", "Jeremiah": "neviim",
    "Ezekiel": "neviim", "Hosea": "neviim", "Joel": "neviim", "Amos": "neviim",
    "Obadiah": "neviim", "Jonah": "neviim", "Micah": "neviim", "Nahum": "neviim",
    "Habakkuk": "neviim", "Zephaniah": "neviim", "Haggai": "neviim", "Zechariah": "neviim", "Malachi": "neviim",
    "Psalms": "ketuvim", "Proverbs": "ketuvim", "Job": "ketuvim", "Song_of_Songs": "ketuvim",
    "Ruth": "ketuvim", "Lamentations": "ketuvim", "Ecclesiastes": "ketuvim", "Esther": "ketuvim",
    "Daniel": "ketuvim", "Ezra": "ketuvim", "Nehemiah": "ketuvim", "I_Chronicles": "ketuvim", "II_Chronicles": "ketuvim"
}

livre = st.selectbox("Livre", sorted(LIVRES.keys()), key="livre_select")
dossier = LIVRES[livre]

with open(f"../sacred-texts-json/{dossier}/{livre}.json", "r", encoding="utf-8") as f:
    data = json.load(f)

nb_chapitres = len(data["text"])
chapitre = st.number_input("Chapitre", min_value=1, max_value=nb_chapitres, value=1, key=f"chapitre_{livre}")

versets = data["text"][chapitre - 1]
texte_complet = ""
for verset in versets:
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