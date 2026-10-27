import streamlit as st
import spacy
import json
import re
import time
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
    "NEGATIVE_ENTITY", "LIFESPAN", "VISION_DREAM_STATE", "GENEALOGY", "BUILDING_TYPE",
    "HUMAN_MORPHOLOGY", "ENTITY_MORPHOLOGY", "BEING_OF_LIGHT", "KNOWLEDGE_BEARER"
}

ZONES = {
    "Moyen-Orient": ["Tanakh", "Coran", "Livre d'Enoch", "Apocalypse d'Esdras", "Testaments des 12 Patriarches", "Apocalypse de Baruch"],
    "Mesopotamie": ["Epopee de Gilgamesh", "Enuma Elish"],
    "Iran/Perse": ["Avesta"],
    "Asie du Sud": ["Rigveda (anglais)", "Samaveda (anglais)", "Upanishads"],
    "Afrique": ["Evangile de Thomas"],
    "Europe": [],
    "Ameriques": [],
    "Oceanie": []
}

CORPUS_VERS_ZONE = {}
for z, liste_corpus in ZONES.items():
    for c in liste_corpus:
        CORPUS_VERS_ZONE[c] = z

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

FICHIER_TRADUCTIONS = "traductions_fr.json"

@st.cache_resource
def _memoire_traductions():
    import os
    if os.path.exists(FICHIER_TRADUCTIONS):
        try:
            with open(FICHIER_TRADUCTIONS, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _sauver_traductions(memoire):
    with open(FICHIER_TRADUCTIONS, "w", encoding="utf-8") as f:
        json.dump(memoire, f, ensure_ascii=False)

ERREUR_TRADUCTION = {"detail": ""}

def _cle_deepl():
    import os
    return os.environ.get("DEEPL_API_KEY", "").strip()

def _traduire_deepl(texte, cle):
    import requests
    url = "https://api-free.deepl.com/v2/translate" if cle.endswith(":fx") else "https://api.deepl.com/v2/translate"
    for attente in (0, 3, 10):
        time.sleep(attente)
        try:
            r = requests.post(url, headers={"Authorization": "DeepL-Auth-Key " + cle},
                              json={"text": [texte], "source_lang": "EN", "target_lang": "FR"}, timeout=30)
            if r.status_code == 200:
                return r.json()["translations"][0]["text"]
            if r.status_code == 456:
                ERREUR_TRADUCTION["detail"] = "quota DeepL du mois epuise (code 456)"
                return None
            if r.status_code in (401, 403):
                ERREUR_TRADUCTION["detail"] = "cle DeepL refusee (code %d)" % r.status_code
                return None
            ERREUR_TRADUCTION["detail"] = "DeepL a repondu le code %d" % r.status_code
        except Exception as e:
            ERREUR_TRADUCTION["detail"] = "DeepL injoignable : %s" % e
    return None

def _traduire_google(texte):
    for attente in (0, 5, 20):
        time.sleep(attente)
        try:
            fr = GoogleTranslator(source="en", target="fr").translate(texte)
            if fr:
                return fr
        except Exception as e:
            ERREUR_TRADUCTION["detail"] = "Google : %s" % e
    return None

def traduire_francais(texte):
    """Retourne (traduction, appel_reseau). traduction vaut None en cas d'echec : un echec n'est jamais memorise."""
    memoire = _memoire_traductions()
    if texte in memoire:
        return memoire[texte], False
    cle = _cle_deepl()
    fr = _traduire_deepl(texte, cle) if cle else _traduire_google(texte)
    if fr:
        memoire[texte] = fr
        _sauver_traductions(memoire)
        return fr, True
    return None, True

def afficher_analyse_avec_versets(liste_versets):
    afficher_fr = st.checkbox("Afficher en français (traduction automatique)", key="trad_checkbox")

    st.subheader("Texte (ligne par ligne)")
    blocage, restantes, appels = False, 0, 0
    for numero, texte_verset in liste_versets:
        texte_affiche = texte_verset
        if afficher_fr:
            if texte_verset in _memoire_traductions():
                texte_affiche = _memoire_traductions()[texte_verset]
            elif blocage or appels >= 60:
                restantes += 1
            else:
                fr, _ = traduire_francais(texte_verset)
                appels += 1
                if fr is None:
                    blocage = True
                    restantes += 1
                else:
                    texte_affiche = fr
                    time.sleep(0.2 if _cle_deepl() else 1.0)
        st.write(f"**Ligne {numero}.** {texte_affiche}")

    if afficher_fr:
        st.caption("Moteur de traduction : " + ("DeepL" if _cle_deepl() else "Google (aucune cle DeepL trouvee dans DEEPL_API_KEY)"))
        if blocage:
            st.warning("Google limite temporairement les requetes de traduction. Attendez quelques minutes, puis cliquez sur 'Poursuivre la traduction'. Les lignes deja traduites sont memorisees. Detail : " + ERREUR_TRADUCTION["detail"])
        elif restantes:
            st.info(f"{restantes} ligne(s) restent en anglais : la traduction se fait par tranches de 60 lignes. Cliquez sur 'Poursuivre la traduction'.")
        if blocage or restantes:
            st.button("Poursuivre la traduction", key="trad_suite")
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
            morceaux_traduits = []
            echec = False
            for m in morceaux:
                fr, reseau = traduire_francais(m)
                if fr is None:
                    echec = True
                    break
                morceaux_traduits.append(fr)
                if reseau:
                    time.sleep(1.5)
            morceaux_traduits += morceaux[len(morceaux_traduits):]
            texte_fr = " ".join(morceaux_traduits)
            if echec:
                st.warning("Google limite temporairement les requetes de traduction : la fin du texte reste en anglais. Reessayez dans quelques minutes (les parties deja traduites sont memorisees). Detail : " + ERREUR_TRADUCTION["detail"])
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

def textes_tanakh_complet():
    resultats = []
    for livre, dossier in LIVRES_TANAKH.items():
        try:
            with open(f"../sacred-texts-json/{dossier}/{livre}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            for i, chapitre_versets in enumerate(data["text"]):
                texte_ch = " ".join(nettoyer(v) for v in chapitre_versets)
                if texte_ch.strip():
                    resultats.append((f"Tanakh - {livre} {i+1}", texte_ch))
        except Exception:
            continue
    return resultats

def textes_coran_complet():
    resultats = []
    versets_coran = charger_coran()
    chapitres = sorted(set(v["chapter"] for v in versets_coran))
    for ch in chapitres:
        versets_ch = [nettoyer(v["text"]) for v in versets_coran if v["chapter"] == ch]
        texte_ch = " ".join(versets_ch)
        if texte_ch.strip():
            resultats.append((f"Coran - Sourate {ch}", texte_ch))
    return resultats

def textes_enoch_complet():
    resultats = []
    for chapitre in range(1, 110):
        numero_fichier = f"{chapitre:02d}"
        try:
            with open(f"../sacred-texts-json/enoch/Chapter_{numero_fichier}.json", "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            texte_brut = data["text"]
            texte_sans_titres = re.sub(r"={2,}[^=]*={2,}", "", texte_brut)
            texte_sans_titres = re.sub(r"CHAPTER [IVXLC]+\.", "", texte_sans_titres)
            texte_ch = nettoyer(texte_sans_titres)
            if texte_ch.strip():
                resultats.append((f"Livre d'Enoch - Chapitre {chapitre}", texte_ch))
        except Exception:
            continue
    return resultats

def textes_rigveda_complet():
    resultats = []
    for num_livre in range(1, 11):
        num_str = f"{num_livre:02d}"
        try:
            with open(f"../sacred-texts-json/vedas/rigveda_anglais/Book_{num_str}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            for hymne in data["hymns"]:
                texte_h = nettoyer(hymne["text"])
                if texte_h.strip():
                    resultats.append((f"Rigveda - Livre {num_str} - {hymne['title']}", texte_h))
        except Exception:
            continue
    return resultats

def textes_samaveda_complet():
    resultats = []
    for num_livre in range(1, 16):
        num_str = f"{num_livre:02d}"
        try:
            with open(f"../sacred-texts-json/vedas/samaveda_anglais/Book_{num_str}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            for entree in data["data"]:
                texte_e = nettoyer(entree["content"])
                if texte_e.strip():
                    resultats.append((f"Samaveda - Livre {num_str} - {entree['chapter']}", texte_e))
        except Exception:
            continue
    return resultats

def textes_esdras_complet():
    resultats = []
    try:
        with open("../sacred-texts-json/2esdras_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for chapitre_data in data["chapters"]:
            texte_ch = " ".join(nettoyer(v["text"]) for v in chapitre_data["verses"])
            if texte_ch.strip():
                resultats.append((f"Apocalypse d'Esdras - Chapitre {chapitre_data['chapter']}", texte_ch))
    except Exception:
        pass
    return resultats

def textes_gilgamesh_complet():
    resultats = []
    try:
        with open("../sacred-texts-json/gilgamesh_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for tablette in data["tablets"]:
            texte_t = nettoyer(tablette["text"])
            if texte_t.strip():
                resultats.append((f"Gilgamesh - Tablette {tablette['tablet']}", texte_t))
    except Exception:
        pass
    return resultats

def textes_thomas_complet():
    resultats = []
    try:
        with open("../sacred-texts-json/thomas_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for logion in data["sayings"]:
            texte_l = nettoyer(logion["text"])
            if texte_l.strip():
                resultats.append((f"Thomas - Logion {logion['saying']}", texte_l))
    except Exception:
        pass
    return resultats

def textes_avesta_complet():
    resultats = []
    try:
        with open("../sacred-texts-json/avesta_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for sec in data["vendidad"]:
            t = nettoyer(sec["text"])
            if t.strip():
                resultats.append((f"Avesta - Vendidad - Fargard {sec['fargard']}", t))
        for sec in data["yashts"]:
            t = nettoyer(sec["text"])
            if t.strip():
                resultats.append((f"Avesta - Yasht {sec['yasht_numero']} {sec['yasht_nom'].title()}", t))
        for i, sec in enumerate(data["yasna"], start=1):
            t = nettoyer(sec["text"])
            if t.strip():
                resultats.append((f"Avesta - Yasna - Bloc {i} (en-tete {sec['yasna_entete_courante']})", t))
    except Exception:
        pass
    return resultats

def textes_testaments_complet():
    resultats = []
    try:
        with open("../sacred-texts-json/testaments_12_patriarches_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for testament in data["testaments"]:
            for chap in testament["chapters"]:
                t = nettoyer(chap["text"])
                if t.strip():
                    resultats.append((f"Testament de {testament['patriarch']} - ch. {chap['chapter']}", t))
    except Exception:
        pass
    return resultats

def textes_baruch_complet():
    resultats = []
    try:
        with open("../sacred-texts-json/baruch_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for livre in data["livres"]:
            nom = "2 Baruch" if livre["title"].startswith("2") else "3 Baruch"
            for chap in livre["chapters"]:
                t = nettoyer(chap["text"])
                if t.strip():
                    resultats.append((f"{nom} - {chap['chapter']}", t))
    except Exception:
        pass
    return resultats

def paragraphes_upanishad(texte):
    t = texte.replace("__NOTOC__", "")
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"={2,}[^=\n]*={2,}", "", t)
    t = re.sub(r"'{2,}", "", t)
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", t) if p.strip()]

def charger_upanishads():
    import os
    dossier = "../sacred-texts-json/upanishads"
    resultat = []
    for nom in sorted(os.listdir(dossier)):
        if nom.endswith(".json"):
            with open(os.path.join(dossier, nom), "r", encoding="utf-8-sig") as f:
                d = json.load(f)
            paras = paragraphes_upanishad(d.get("text", ""))
            if paras:
                resultat.append((nom[:-5].replace("_", " "), paras))
    return resultat

def textes_upanishads_complet():
    resultats = []
    try:
        for nom, paras in charger_upanishads():
            for i, p in enumerate(paras, 1):
                resultats.append((f"{nom} - {i}", p))
    except Exception:
        pass
    return resultats

def charger_enuma():
    with open("../sacred-texts-json/enuma_elish_complete.json", "r", encoding="utf-8") as f:
        return json.load(f)

def textes_enuma_complet():
    resultats = []
    try:
        for tab in charger_enuma()["tablets"]:
            t = " ".join(l["text"] for l in tab["lines"] if "n" in l)
            if t.strip():
                resultats.append((f"Enuma Elish - Tablette {tab['tablet']}", nettoyer(t)))
    except Exception:
        pass
    return resultats

CHARGEURS_PAR_CORPUS = {
    "Tanakh": (textes_tanakh_complet, "Moyen-Orient"),
    "Coran": (textes_coran_complet, "Moyen-Orient"),
    "Livre d'Enoch": (textes_enoch_complet, "Moyen-Orient"),
    "Apocalypse d'Esdras": (textes_esdras_complet, "Moyen-Orient"),
    "Rigveda (anglais)": (textes_rigveda_complet, "Asie du Sud"),
    "Samaveda (anglais)": (textes_samaveda_complet, "Asie du Sud"),
    "Epopee de Gilgamesh": (textes_gilgamesh_complet, "Mesopotamie"),
    "Evangile de Thomas": (textes_thomas_complet, "Afrique"),
    "Avesta": (textes_avesta_complet, "Iran/Perse"),
    "Testaments des 12 Patriarches": (textes_testaments_complet, "Moyen-Orient"),
    "Apocalypse de Baruch": (textes_baruch_complet, "Moyen-Orient"),
    "Upanishads": (textes_upanishads_complet, "Asie du Sud"),
    "Enuma Elish": (textes_enuma_complet, "Mesopotamie"),
}

@st.cache_data(show_spinner=False)
def scanner_tous_les_corpus():
    resultats_bruts = {}

    tous_les_textes = []
    for nom_corpus, (fonction_chargement, zone) in CHARGEURS_PAR_CORPUS.items():
        for source_label, texte in fonction_chargement():
            tous_les_textes.append((nom_corpus, zone, source_label, texte))

    barre = st.progress(0, text="Analyse en cours...")
    total = len(tous_les_textes)

    textes_bruts = [t[3] for t in tous_les_textes]
    docs = nlp.pipe(textes_bruts, batch_size=100)

    for i, (doc, (nom_corpus, zone, source_label, texte)) in enumerate(zip(docs, tous_les_textes)):
        for ent in doc.ents:
            if ent.label_ in CATEGORIES_PERSONNALISEES:
                cle = f"{ent.text.lower()}|||{ent.label_}"
                if cle not in resultats_bruts:
                    resultats_bruts[cle] = {"occurrences": 0, "corpus": [], "zones": []}
                resultats_bruts[cle]["occurrences"] += 1
                if nom_corpus not in resultats_bruts[cle]["corpus"]:
                    resultats_bruts[cle]["corpus"].append(nom_corpus)
                if zone not in resultats_bruts[cle]["zones"]:
                    resultats_bruts[cle]["zones"].append(zone)
        if i % 50 == 0:
            barre.progress(min(i / total, 1.0), text=f"Analyse en cours... {i}/{total} textes traites")

    barre.progress(1.0, text="Termine !")
    barre.empty()

    return resultats_bruts

def afficher_recoupement():
    st.subheader("Recoupement des patterns a travers tous les corpus")
    st.caption("Ce scan analyse la totalite des textes de tous les corpus branches. Premiere execution : peut prendre 1 a 3 minutes. Les executions suivantes sont instantanees (mise en cache).")

    if st.button("Lancer / relancer le scan complet"):
        st.cache_data.clear()

    resultats = scanner_tous_les_corpus()

    st.success(f"{len(resultats)} entites uniques detectees a travers {len(CHARGEURS_PAR_CORPUS)} corpus.")

    st.subheader("Top 20 des symboles les plus frequents (tous corpus confondus)")
    classement = sorted(
        [(cle.split("|||")[0], cle.split("|||")[1], infos["occurrences"]) for cle, infos in resultats.items()],
        key=lambda x: -x[2]
    )[:20]

    if classement:
        import pandas as pd
        df_classement = pd.DataFrame(classement, columns=["Symbole", "Categorie", "Occurrences"])
        st.bar_chart(df_classement.set_index("Symbole")["Occurrences"])
        st.dataframe(df_classement, use_container_width=True)

    recherche = st.text_input("Filtrer par mot ou categorie (optionnel)", key="filtre_recoupement")

    lignes = []
    for cle, infos in resultats.items():
        texte_ent, label = cle.split("|||")
        if len(infos["corpus"]) < 2:
            continue
        lignes.append({
            "Entite": texte_ent,
            "Categorie": label,
            "Occurrences": infos["occurrences"],
            "Corpus": ", ".join(sorted(infos["corpus"])),
            "Zones": ", ".join(sorted(infos["zones"]))
        })

    lignes.sort(key=lambda x: -x["Occurrences"])

    if recherche:
        recherche_lower = recherche.lower()
        lignes = [l for l in lignes if recherche_lower in l["Entite"].lower() or recherche_lower in l["Categorie"].lower()]

    st.write(f"**{len(lignes)} entites presentes dans au moins 2 corpus differents** (les recoupements les plus interessants) :")

    for ligne in lignes[:200]:
        st.write(f"**{ligne['Entite']}** ({ligne['Categorie']}) — {ligne['Occurrences']} occurrences — Corpus : {ligne['Corpus']} — Zones : {ligne['Zones']}")

    if len(lignes) > 200:
        st.caption(f"Affichage limite aux 200 premiers resultats sur {len(lignes)}. Affinez votre recherche pour voir davantage.")

mode = st.sidebar.radio("Mode", ["Explorer un corpus", "Recoupement inter-textes"], key="mode_select")

if mode == "Recoupement inter-textes":
    afficher_recoupement()

else:
    corpus = None

    st.sidebar.header("Navigation par zone geographique")
    zone = st.sidebar.radio("Zone", list(ZONES.keys()), key="zone_select")

    if not ZONES[zone]:
        st.sidebar.info("Aucun corpus dans cette zone pour l'instant.")
    else:
        corpus = st.sidebar.radio("Corpus", ZONES[zone], key="corpus_select")

    if corpus is None:
        st.info("Choisissez une zone contenant au moins un corpus dans le menu a gauche.")

    elif corpus == "Tanakh":
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

    elif corpus == "Apocalypse d'Esdras":
        with open("../sacred-texts-json/2esdras_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        chapitres_esdras = data["chapters"]
        titres_chapitres = [f"Chapitre {c['chapter']}" for c in chapitres_esdras]
        titre_choisi = st.selectbox("Chapitre", titres_chapitres, key="chapitre_esdras")

        index_choisi = titres_chapitres.index(titre_choisi)
        chapitre_data = chapitres_esdras[index_choisi]
        liste_versets = [(v["verse"], nettoyer(v["text"])) for v in chapitre_data["verses"]]
        afficher_analyse_avec_versets(liste_versets)

    elif corpus == "Epopee de Gilgamesh":
        with open("../sacred-texts-json/gilgamesh_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        tablettes_gilgamesh = data["tablets"]
        titres_tablettes = [f"Tablette {t['tablet']} - {t['title']}" for t in tablettes_gilgamesh]
        titre_choisi = st.selectbox("Tablette", titres_tablettes, key="tablette_gilgamesh")

        index_choisi = titres_tablettes.index(titre_choisi)
        tablette_data = tablettes_gilgamesh[index_choisi]
        texte_complet = nettoyer(tablette_data["text"])
        afficher_analyse_globale(texte_complet)

    elif corpus == "Evangile de Thomas":
        with open("../sacred-texts-json/thomas_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        logia = data["sayings"]
        groupes = [f"Logia {i}-{min(i + 9, len(logia))}" for i in range(1, len(logia) + 1, 10)]
        groupe_choisi = st.selectbox("Groupe de logia", groupes, key="groupe_thomas")

        index_groupe = groupes.index(groupe_choisi)
        debut = index_groupe * 10
        logia_du_groupe = logia[debut:debut + 10]
        liste_versets = [(s["saying"], nettoyer(s["text"])) for s in logia_du_groupe]
        afficher_analyse_avec_versets(liste_versets)

    elif corpus == "Avesta":
        with open("../sacred-texts-json/avesta_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        st.warning("Texte issu d'un OCR de scans du 19e siecle. Chaque section commence par une introduction ou un resume redige par le traducteur, et les notes de bas de page sont melangees au texte : les entites detectees melent donc texte avestique et commentaire. Decoupage approximatif (a une page pres).")

        partie = st.selectbox("Partie", ["Vendidad", "Yashts", "Yasna"], key="partie_avesta")
        if partie == "Vendidad":
            sections = data["vendidad"]
            titres = [f"Fargard {x['fargard']}" for x in sections]
        elif partie == "Yashts":
            sections = data["yashts"]
            titres = [f"Yasht {x['yasht_numero']} - {x['yasht_nom'].title()}" for x in sections]
        else:
            sections = data["yasna"]
            titres = [f"Bloc {i} (en-tete Yasna {x['yasna_entete_courante']})" for i, x in enumerate(sections, start=1)]

        titre_choisi = st.selectbox("Section", titres, key=f"section_avesta_{partie}")
        section_data = sections[titres.index(titre_choisi)]
        afficher_analyse_globale(nettoyer(section_data["text"]))

    elif corpus == "Testaments des 12 Patriarches":
        with open("../sacred-texts-json/testaments_12_patriarches_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        st.info("Traduction anglaise du 19e siecle (Ante-Nicene Fathers, vol. VIII). La datation de ce texte et la presence d'interpolations chretiennes sont debattues parmi les chercheurs. Les notes critiques du traducteur ont ete retirees.")

        testaments = data["testaments"]
        titres = [t["title"] for t in testaments]
        titre_choisi = st.selectbox("Testament", titres, key="testament_patriarche")
        testament_data = testaments[titres.index(titre_choisi)]
        liste_versets = [(c["chapter"], nettoyer(c["text"])) for c in testament_data["chapters"]]
        afficher_analyse_avec_versets(liste_versets)

    elif corpus == "Apocalypse de Baruch":
        with open("../sacred-texts-json/baruch_complete.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        st.info("Traductions anglaises de 1913 (R. H. Charles pour le 2 Baruch syriaque, H. M. Hughes pour le 3 Baruch grec), issues d'un OCR. Le commentaire des editeurs a ete retire par heuristique : quelques fragments peuvent rester. Dans le 2 Baruch, le texte est decoupe en blocs (titres de sections imprimes), pas en 87 chapitres.")

        livres = data["livres"]
        titres = [l["title"] for l in livres]
        titre_choisi = st.selectbox("Livre", titres, key="baruch_livre")
        livre_data = livres[titres.index(titre_choisi)]
        liste_versets = [(str(c["chapter"]), nettoyer(c["text"])) for c in livre_data["chapters"]]
        afficher_analyse_avec_versets(liste_versets)

    elif corpus == "Upanishads":
        st.info("Traductions anglaises de Max Muller (Sacred Books of the East, 1879 et 1884). Six textes viennent de Wikisource, cinq (Kaushitaki, Taittiriya, Brihadaranyaka, Svetasvatara, Maitrayana) d'un OCR dont les signes diacritiques sont abimes. Les notes de bas de page de Muller sont dans les fichiers, separees du texte. Les Upanishads ne sont pas tous presents : voir le depot de donnees.")

        upanishads = charger_upanishads()
        noms = [n for n, _ in upanishads]
        nom_choisi = st.selectbox("Upanishad", noms, key="upanishad_choisie")
        paras = dict(upanishads)[nom_choisi]
        liste_versets = [(i + 1, p) for i, p in enumerate(paras)]
        afficher_analyse_avec_versets(liste_versets)


    elif corpus == "Enuma Elish":
        data = charger_enuma()
        st.info("Traduction anglaise ancienne (British Museum, 1921, domaine public), tres lacunaire. Seuls les vers numerotes sont analyses ; les resumes de l'editeur moderne, les lacunes signalees et les notes sont affiches a part. Les crochets [ ] sont des restitutions.")

        tablettes = data["tablets"]
        titres = [t["title"] for t in tablettes]
        titre_choisi = st.selectbox("Tablette", titres, key="enuma_tablette")
        tab = tablettes[titres.index(titre_choisi)]
        hors_texte = [l["text"] for l in tab["lines"] if "n" not in l and l.get("kind") != "titre"]
        notes = list(tab.get("notes", [])) + [n for l in tab["lines"] for n in l.get("notes", [])]
        if hors_texte or notes:
            with st.expander("Lacunes, resumes de l'editeur et notes (hors texte antique)"):
                for h in hors_texte:
                    st.markdown("- " + h)
                for n in notes:
                    st.markdown("- *note :* " + n)
        liste_versets = [(str(l["n"]), nettoyer(l["text"])) for l in tab["lines"] if "n" in l]
        afficher_analyse_avec_versets(liste_versets)
