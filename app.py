import streamlit as st
import whisper
import pandas as pd
import tempfile
import os

st.set_page_config(page_title="Meža Dastošanas Asistents", layout="wide")

st.title("🌲 Meža Dastošanas Balss Asistents")
st.write("Augšupielādē telefona audio ierakstu (.m4a, .mp3, .wav), un programma atpazīs visas sugas, sortimentus un diametrus.")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")

with st.spinner("Notiek balss atpazīšanas modeļa sagatavošana..."):
    model = load_whisper_model()

uploaded_file = st.file_uploader(
    "Izvēlies audio ierakstu:", 
    type=["mp3", "wav", "m4a", "caf", "aac", "mp4"]
)

def parse_diametrs(word):
    word_clean = word.strip(",.-")
    if word_clean.isdigit():
        val = int(word_clean)
        if 6 <= val <= 70: # Reālas dastošanas diametra robežas
            return val
    
    # Fonētiskās korekcijas skaitļiem
    if "čaitr" in word_clean or "četr" in word_clean or "četri" in word_clean or "štētri" in word_clean:
        return 24
    if "diod" in word_clean or "divp" in word_clean or "divas" in word_clean or "divpadsmit" in word_clean:
        return 12
    if "sašt" in word_clean or "sešp" in word_clean or "sešpadsmit" in word_clean:
        return 16
    if "astoņ" in word_clean or "astoņi" in word_clean:
        return 8
    if "divd" in word_clean or "divdesmit" in word_clean:
        return 20
    if "tasto" in word_clean or "trīs" in word_clean or "trīsdesmit" in word_clean:
        return 32
    if "desmit" in word_clean or "des" in word_clean:
        return 10
    if "četrdesmit" in word_clean:
        return 40
    if "sešdesmit" in word_clean:
        return 60
    
    return None

def parsat_tekstu(teksts):
    sugu_kartpe = {
        "egle": "Egle",
        "egla": "Egle",
        "priede": "Priede",
        "priedes": "Priede",
        "bērzs": "Bērzs",
        "bērzi": "Bērzs",
        "apse": "Apse",
        "apses": "Apse",
        "melnalksnis": "Melnalksnis",
        "melnais": "Melnalksnis",
        "baltalksnis": "Baltalksnis",
        "baltais": "Baltalksnis",
        "alksnis": "Melnalksnis",
        "blīgzna": "Blīgzna",
        "kļava": "Kļava",
        "osis": "Osis",
        "vītols": "Vītols",
        "goba": "Goba",
        "ozols": "Ozols",
        "liepa": "Liepa"
    }
    
    words = teksts.lower().split()
    dati = []
    
    # Elastīga stāvokļa mainīgie (State Machine)
    rekošais_stavs = "1. stāvs"
    treniska_suga = "Egle" # Noklusējuma suga, ja pirmajā mirklī nav nosaukta
    rekošais_sortiments = "L" # Noklusējuma sortiments: Lieta (L)
    
    i = 0
    while i < len(words):
        word = words[i].strip(",.-")
        
        # Stāvi
        if word in ["pirmais", "1."] and i + 1 < len(words) and "stāv" in words[i+1]:
            rekošais_stavs = "1. stāvs"
            i += 2
            continue
        elif word in ["otrais", "2."] and i + 1 < len(words) and "stāv" in words[i+1]:
            rekošais_stavs = "2. stāvs"
            i += 2
            continue
        elif word in ["otrais", "2.", "otrā", "oģrā"]:
            rekošais_stavs = "2. stāvs"
            i += 1
            continue
            
        # Sortimenti
        if word in ["puse", "puslietas", "pl"]:
            rekošais_sortiments = "PL"
            i += 1
            continue
        elif word in ["malka", "malta", "m"]:
            rekošais_sortiments = "M"
            i += 1
            continue
        elif word in ["lieta", "l"]:
            rekošais_sortiments = "L"
            i += 1
            continue
            
        # Alksniskās saliktās sugas
        if word in ["melnais", "baltais"] and i + 1 < len(words) and "alksn" in words[i+1]:
            treniska_suga = "Melnalksnis" if "melnais" in word else "Baltalksnis"
            i += 2
            continue

        # Parastās sugas
        matched_suga = None
        for key, val in sugu_kartpe.items():
            if word == key:
                matched_suga = val
                break
        
        if matched_suga:
            treniska_suga = matched_suga
            i += 1
            continue
            
        # Pārbaudām vai vārds ir diametrs
        diam = parse_diametrs(word)
        if diam is not None:
            dati.append({
                "Stāvs": rekošais_stavs,
                "Suga": treniska_suga,
                "Sortiments": rekošais_sortiments,
                "Diametrs": diam
            })
            # Pēc diametra nolasīšanas sortiments atgriežas uz noklusējuma 'L' (Lieta), ja vien nebija minēts citādi
            rekošais_sortiments = "L"
            i += 1
            continue
            
        i += 1
            
    return dati

def izveidot_dastlapu_matrix(df):
    pakapes = [8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60]
    sugas = ["Egle", "Priede", "Bērzs", "Apse", "Melnalksnis", "Baltalksnis", "Ozols", "Osis", "Liepa", "Kļava", "Vītols", "Goba", "Blīgzna"]
    sortimenti = ["L", "PL", "M"]
    
    index_tuples = []
    for suga in sugas:
        for sort in sortimenti:
            index_tuples.append((suga, sort))
    
    multi_index = pd.MultiIndex.from_tuples(index_tuples, names=['Suga', 'Sortiments'])
    
    if not df.empty:
        pivot = pd.pivot_table(
            df, 
            index='Diametrs', 
            columns=['Suga', 'Sortiments'], 
            aggfunc='size', 
            fill_value=0
        )
    else:
        pivot = pd.DataFrame(index=pakapes)

    pivot = pivot.reindex(index=pakapes, columns=multi_index, fill_value=0)
    pivot.index.name = 'Diametra pakāpe'
    
    return pivot

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    if st.button("Sākt audio faila apstrādi", type="primary"):
        with st.spinner("Notiek balss atpazīšana un visu koku šķirošana..."):
            try:
                result = model.transcribe(
                    tmp_path, 
                    language="lv", 
                    initial_prompt="Egle, priede, bērzs, apse, melnalksnis, baltalksnis, liepa, ozols, osis, malka, puse, lieta, diametrs, stāvs, 8, 12, 16, 20, 24, 28, 32, 36"
                )
                teksts = result["text"].lower()
                
                st.info(f"**Whisper atpazītais teksts (pārbaudei):**\n\n\"{teksts}\"")
                
                dati = parsat_tekstu(teksts)
                
                if dati:
                    df = pd.DataFrame(dati)
                    st.success("Dastlapa veiksmīgi sagatavota!")
                    
                    st.subheader("📋 Pilna Dastošanas Lapa")
                    dastlapa_df = izveidot_dastlapu_matrix(df)
                    st.dataframe(dastlapa_df, use_container_width+True)
                    
                    with st.expander("Skatīt detalizētu koku sarakstu"):
                        st.dataframe(df, use_container_width=True)
                    
                    csv = dastlapa_df.to_csv().encode('utf-8')
                    st.download_button(
                        label="📥 Lejupielādēt Dastlapu (CSV)",
                        data=csv,
                        file_name="dastlapa.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("Tekstā neizdevās atpazīt datus. Pārbaudi, vai ierakstā skaidri nosaukta suga un izmērs.")
            except Exception as e:
                st.error(f"Kļūda apstrādē: {e}")

    if os.path.exists(tmp_path):
        os.remove(tmp_path)
