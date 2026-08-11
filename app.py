import streamlit as st
import spacy
import json
import re
from deep_translator import GoogleTranslator

st.set_page_config(layout="wide")
st.title("Analyseur de textes sacrés")

CATEGORIES_PERSONNALISEES = {
    "DEITY", "PROPHET_FIGURE", "CELESTIAL_BEING", "SACRED_PLACE",
    "SACRED_OBJECT", "CELESTIAL_PHENOMENON", "CONCEPT_KNOWLEDGE", "PEOPLE_GROUP",
    "SYMBOLIC_NUMBER", "ELEMENT", "COLOR_SYMBOLIC", "METAL_MATERIAL",
    "CARDINAL_DIRECTION", "CELESTIAL_BODY", "ANIMAL_SYMBOLIC", "PHYSICAL_DESCRIPTOR",
    "SACRED_EVENT", "RITUAL_PRACTICE", "AFTERLIFE_CONCEPT", "SACRED_TEXT",
    "COSMIC_STRUCTURE", "TIME_CONCEPT", "PLANT_SYMBOLIC", "SOUND_PHENOMENON",
    "BODY_PART_SYMBOLIC", "SOCIAL_ROLE", "KNOWLEDGE_TRANSMISSION", "PHENOMENON_NAMING",
    "NEGATIVE_ENTITY", "LIFESPAN", "VISION_DREAM_STATE"
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

@st.cache_data
def traduire_francais(texte):
    try:
        return GoogleTranslator(source="en", target="fr").translate(texte)
    except Exception as e:
        return f"[Erreur de traduction : {e}]"

def afficher_analyse_avec_versets(liste_versets):
    afficher_fr = st.checkbox("Afficher en français (traduction automatique)", key="trad_checkbox")

    st.subheader("Texte (ligne par ligne)")
    for numero, texte_verset in liste_versets:
        if afficher_fr:
            with st.spinner(f"Traduction ligne {numero}..."):
                texte_affiche = traduire_francais(texte_verset)
        else:
            texte_affiche = texte_verset
        st.write(f"**Ligne {numero}.** {texte_affiche}")

    if afficher_fr:
        st.caption("Traduction automatique — l'analyse ci-dessous reste basee sur le texte anglais original.")

    st.subheader("Entites detectees, avec numero de ligne")
    resultats = []
    for numero, texte_verset in liste_versets:
        doc = nlp(texte_verset)
        for ent in doc.ents:
            if ent.label_ in CATEGORIES_PERSONNALISEES:
                resultats.append((numero, ent.text, ent.label_))

    if resultats:
        for numero, texte_ent, label in resultats:
            st.write(f"**Ligne {numero}** — {texte_ent} — {label}")
    else:
        st.write("Aucune entite personnalisee detectee.")

def afficher_analyse_globale(texte_complet):
    afficher_fr = st.checkbox("Afficher en français (traduction automatique)", key="trad_checkbox")

    doc = nlp(texte_complet)
    ents_filtrees = [e for e in doc.ents if e.label_ in CATEGORIES_PERSONNALISEES]

    st.subheader("Texte")
    if afficher_fr:
        with st.spinner("Traduction en cours..."):
            morceaux = [texte_complet[i:i+4500] for i in range(0, len(texte_complet), 4500)]
            texte_fr = " ".join(traduire_francais(m) for m in morceaux)
        st.write(texte_fr)
        st.caption("Traduction automatique — l'analyse ci-dessous reste basee sur le texte anglais original.")
    else:
        st.write(texte_complet)

    st.caption("Ce corpus n'est pas decoupe par verset dans les donnees source : la position exacte n'est pas disponible, seulement la presence dans le texte.")
    st.subheader("Entites detectees (categories personnalisees uniquement)")
    if ents_filtrees:
        for ent in ents_filtrees:
            st.write(f"**{ent.text}** — {ent.label_}")
    else:
        st.write("Aucune entite personnalisee detectee.")

corpus = st.radio("Corpus", ["Tanakh", "Coran", "Livre d'Enoch", "Rigveda (anglais)", "Samaveda (anglais)"], key="corpus_select")

if corpus == "Tanakh":
    livre = st.selectbox("Livre", sorted(LIVRES_TANAKH.keys()), key="livre_select")
    dossier = LIVRES_TANAKH[livre]

    with open(f"../sacred-texts-json/{dossier}/{livre}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    nb_chapitres = len(data["text"])
    chapitre = st.number_input("Chapitre", min_value=1, max_value=nb_chapitres, value=1, key=f"chapitre_{livre}")

    versets = data["text"][chapitre - 1]
    liste_versets = [(i + 1, nettoyer(v)) for i, v in enumerate(versets)]
    afficher_analyse_avec_versets(liste_versets)

elif corpus == "Coran":
    versets_coran = charger_coran()
    chapitres_disponibles = sorted(set(v["chapter"] for v in versets_coran))
    chapitre = st.selectbox("Sourate (numero)", chapitres_disponibles, key="sourate_select")

    versets_du_chapitre = [v for v in versets_coran if v["chapter"] == chapitre]
    liste_versets = [(v["verse"], nettoyer(v["text"])) for v in versets_du_chapitre]
    afficher_analyse_avec_versets(liste_versets)

elif corpus == "Livre d'Enoch":
    chapitre = st.number_input("Chapitre", min_value=1, max_value=109, value=1, key="chapitre_enoch")
    numero_fichier = f"{chapitre:02d}"

    with open(f"../sacred-texts-json/enoch/Chapter_{numero_fichier}.json", "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    texte_brut = data["text"]
    texte_sans_titres = re.sub(r"={2,}[^=]*={2,}", "", texte_brut)
    texte_sans_titres = re.sub(r"CHAPTER [IVXLC]+\.", "", texte_sans_titres)
    paragraphes = [p for p in texte_sans_titres.split("\n\n") if p.strip()]
    liste_versets = [(i + 1, nettoyer(p)) for i, p in enumerate(paragraphes) if nettoyer(p)]
    afficher_analyse_avec_versets(liste_versets)

elif corpus == "Rigveda (anglais)":
    numero_livre = st.selectbox("Livre (Mandala)", [f"{i:02d}" for i in range(1, 11)], key="livre_rigveda")

    with open(f"../sacred-texts-json/vedas/rigveda_anglais/Book_{numero_livre}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    hymnes = data["hymns"]
    titres_hymnes = [h["title"] for h in hymnes]
    titre_choisi = st.selectbox("Hymne", titres_hymnes, key="hymne_rigveda")

    hymne = next(h for h in hymnes if h["title"] == titre_choisi)
    strophes = [s for s in hymne["text"].split("p: ") if s.strip()]
    liste_versets = [(i + 1, nettoyer(s)) for i, s in enumerate(strophes) if nettoyer(s)]
    afficher_analyse_avec_versets(liste_versets)

elif corpus == "Samaveda (anglais)":
    numero_livre = st.selectbox("Livre", [f"{i:02d}" for i in range(1, 16)], key="livre_samaveda")

    with open(f"../sacred-texts-json/vedas/samaveda_anglais/Book_{numero_livre}.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    entrees = data["data"]
    titres_entrees = [f"{e['chapter']} - {e['title']}" for e in entrees]
    titre_choisi = st.selectbox("Chapitre / Decade", titres_entrees, key="chapitre_samaveda")

    index_choisi = titres_entrees.index(titre_choisi)
    entree = entrees[index_choisi]
    strophes = [s for s in entree["content"].split("p:") if s.strip()]
    liste_versets = [(i + 1, nettoyer(s)) for i, s in enumerate(strophes) if nettoyer(s)]
    afficher_analyse_avec_versets(liste_versets)