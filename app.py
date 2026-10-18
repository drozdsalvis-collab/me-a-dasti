import streamlit as st
import pandas as pd
import tempfile
import os
from openai import OpenAI

st.set_page_config(page_title="Meža Dastošanas Asistents", layout="wide")

st.title("🌲 Meža Dastošanas Balss Asistents (API)")
st.write("Augšupielādē telefona audio ierakstu – tas tiks apstrādāts sekundes laikā.")

# API atslēgas ievade drošībai sānjoslā
with st.sidebar:
    st.subheader("Iestatījumi")
    api_key_input = st.text_input("Ievadi savu OpenAI API atslēgu:", type="password")
    st.markdown("---")
    st.markdown("**Instrukcija:** Fails tiek nosūtīts uz OpenAI API, nodrošinot 100% precizitāti un ātrumu bez servera bremzēšanas.")

uploaded_file = st.file_uploader(
    "Izvēlies audio ierakstu (.m4a, .mp3, .wav):", 
    type=["mp3", "wav", "m4a", "caf", "aac", "mp4"]
)

def parse_diametrs(word):
    word_clean = word.strip(",.-")
    if word_clean.isdigit():
        val = int(word_clean)
        if 6 <= val <= 70:
            return val
    
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
        "bēr": "Bērzs",
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
    
    rekošais_stavs = "1. stāvs"
    treniska_suga = "Egle"
    rekošais_sortiments = "L"
    
    i = 0
    while i < len(words):
        word = words[i].strip(",.-")
        
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
            
        if word in ["melnais", "baltais"] and i + 1 < len(words) and "alksn" in words[i+1]:
            treniska_suga = "Melnalksnis" if "melnais" in word else "Baltalksnis"
            i += 2
            continue

        matched_suga = None
        for key, val in sugu_kartpe.items():
            if word == key or word.startswith(key):
                matched_suga = val
                break
        
        if matched_suga:
            treniska_suga = matched_suga
            i += 1
            continue
            
        diam = parse_diametrs(word)
        if diam is not None:
            dati.append({
                "Stāvs": rekošais_stavs,
                "Suga": treniska_suga,
                "Sortiments": rekošais_sortiments,
                "Diametrs": diam
            })
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
    if not api_key_input:
        st.warning("Lūdzu, ievadi savu OpenAI API atslēgu sānjoslā kreisajā pusē, lai turpinātu.")
    else:
        if st.button("Sākt audio faila apstrādi", type="primary"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name

            with st.spinner("Notiek zibenīga faila apstrāde caur OpenAI API..."):
                try:
                    client = OpenAI(api_key=api_key_input)
                    
                    with open(tmp_path, "rb") as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="lv",
                            prompt="Egle, priede, bērzs, apse, melnalksnis, baltalksnis, liepa, ozols, osis, malka, puse, lieta, stāvs, 8, 12, 16, 20, 24, 28, 32, 36"
                        )
                    
                    teksts = transcript.text.lower()
                    st.info(f"**Atpazītais teksts:**\n\n\"{teksts}\"")
                    
                    dati = parsat_tekstu(teksts)
                    
                    if dati:
                        df = pd.DataFrame(dati)
                        st.success("Dastlapa veiksmīgi sagatavota!")
                        
                        st.subheader("📋 Pilna Dastošanas Lapa")
                        dastlapa_df = izveidot_dastlapu_matrix(df)
                        st.dataframe(dastlapa_df, use_container_width=True)
                        
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
                        st.warning("Tekstā neizdevās atpazīt datus. Pārbaudi ierakstu.")
                except Exception as e:
                    st.error(f"Kļūda apstrādē: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
