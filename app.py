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

LIVRES_TANAKH = {
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

@st.cache_data
def charger_coran():
    with open("../sacred-texts-json/coran/Coran_Anglais.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["quran"]

def nettoyer(texte):
    propre = re.sub(r"<i class=\"footnote\">.*?</i>", "", texte)
    propre = re.sub(r"<[^>]+>", "", propre)
    propre = re.sub(r"={2,}[^=]*={2,}", "", propre)
    propre = re.sub(r"[⌈⌉]", "", propre)
    propre = re.sub(r"\n+", " ", propre)
    propre = re.sub(r"\s{2,}", " ", propre)
    return propre.strip()

def afficher_analyse(texte_complet):
    doc = nlp(texte_complet)
    ents_filtrees = [e for e in doc.ents if e.label_ in CATEGORIES_PERSONNALISEES]

    st.subheader("Texte")
    st.write(texte_complet)

    st.subheader("Entites detectees (categories personnalisees uniquement)")
    if ents_filtrees:
        for ent in ents_filtrees:
            st.write(f"**{ent.text}** — {ent.label_}")
    else:
        st.write("Aucune entite personnalisee detectee.")

corpus = st.radio("Corpus", ["Tanakh", "Coran", "Livre d'Enoch", "Rigveda (anglais)"], key="corpus_select")

if corpus == "Tanakh":
    livre = st.selectbox("Livre", sorted(LIVRES_TANAKH.keys()), key="livre_select")
    dossier = LIVRES_TANAKH[livre]

    with open(f"../sacred-texts-json/{dossier}/{livre}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    nb_chapitres = len(data["text"])
    chapitre = st.number_input("Chapitre", min_value=1, max_value=nb_chapitres, value=1, key=f"chapitre_{livre}")

    versets = data["text"][chapitre - 1]
    texte_complet = " ".join(nettoyer(v) for v in versets)
    afficher_analyse(texte_complet)

elif corpus == "Coran":
    versets_coran = charger_coran()
    chapitres_disponibles = sorted(set(v["chapter"] for v in versets_coran))
    chapitre = st.selectbox("Sourate (numero)", chapitres_disponibles, key="sourate_select")

    versets_du_chapitre = [v for v in versets_coran if v["chapter"] == chapitre]
    texte_complet = " ".join(nettoyer(v["text"]) for v in versets_du_chapitre)
    afficher_analyse(texte_complet)

elif corpus == "Livre d'Enoch":
    chapitre = st.number_input("Chapitre", min_value=1, max_value=109, value=1, key="chapitre_enoch")
    numero_fichier = f"{chapitre:02d}"

    with open(f"../sacred-texts-json/enoch/Chapter_{numero_fichier}.json", "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    texte_complet = nettoyer(data["text"])
    afficher_analyse(texte_complet)

elif corpus == "Rigveda (anglais)":
    numero_livre = st.selectbox("Livre (Mandala)", [f"{i:02d}" for i in range(1, 11)], key="livre_rigveda")

    with open(f"../sacred-texts-json/vedas/rigveda_anglais/Book_{numero_livre}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    hymnes = data["hymns"]
    titres_hymnes = [h["title"] for h in hymnes]
    titre_choisi = st.selectbox("Hymne", titres_hymnes, key="hymne_rigveda")

    hymne = next(h for h in hymnes if h["title"] == titre_choisi)
    texte_complet = nettoyer(hymne["text"])
    afficher_analyse(texte_complet)