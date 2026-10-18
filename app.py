import streamlit as st
import pandas as pd
import speech_recognition as sr
import os
from pydub import AudioSegment
import tempfile

st.set_page_config(page_title="Meža Dastošanas Asistents", layout="wide")

st.title("🌲 Meža Dastošanas Balss Asistents")
st.write("Augšupielādē audio failu no sava telefona (piemēram, balss ierakstu), un programma to automātiski atpazīs un sakārtos tabulā.")

uploaded_file = st.file_uploader(
    "Izvēlies audio ierakstu (.m4a, .wav, .mp3):", 
    type=["m4a", "wav", "mp3", "aac", "caf"]
)

def parse_diametrs(word):
    word_clean = word.strip(",.-")
    if word_clean.isdigit():
        return int(word_clean)
    
    if "čaitr" in word_clean or "četr" in word_clean or "četri" in word_clean or "štētri" in word_clean:
        return 24
    if "diod" in word_clean or "divp" in word_clean or "divas" in word_clean:
        return 12
    if "sašt" in word_clean or "sešp" in word_clean or "sešpadsmit" in word_clean:
        return 16
    if "astoņ" in word_clean:
        return 8
    if "divd" in word_clean or "divdesmit" in word_clean:
        return 20
    if "tasto" in word_clean or "trīs" in word_clean:
        return 32
    if "desmit" in word_clean or "des" in word_clean:
        return 10
    
    return None

def parsat_tekstu(teksts):
    sugu_kartpe = {
        "egle": "Egle",
        "priede": "Priede",
        "bērzs": "Bērzs",
        "apse": "Apse",
        "alksnis": "Alksnis",
        "balts": "Baltalksnis",
        "baltalksnis": "Baltalksnis",
        "blīgzna": "Blīgzna",
        "kļava": "Kļava",
        "osis": "Osis",
        "vītols": "Vītols",
        "goba": "Goba",
        "ozols": "Ozols",
        "līpa": "Līpa"
    }
    
    words = teksts.lower().split()
    dati = []
    rekošais_stavs = "1. stāvs"
    treniska_suga = None
    rekošais_sortiments = "L"
    
    i = 0
    while i < len(words):
        word = words[i].strip(",.-")
        
        if word in ["pirmais", "1.", "pirmā"]:
            rekošais_stavs = "1. stāvs"
            i += 1
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
        
        matched_suga = None
        for key, val in sugu_kartpe.items():
            if word == key or word.startswith(key):
                matched_suga = val
                break
        
        if matched_suga:
            treniska_suga = matched_suga
            i += 1
            while i < len(words):
                next_word = words[i].strip(",.-")
                if next_word in ["puse", "puslietas", "pl"]:
                    rekošais_sortiments = "PL"
                    i += 1
                    continue
                elif next_word in ["malka", "malta", "m"]:
                    rekošais_sortiments = "M"
                    i += 1
                    continue
                elif next_word in ["lieta", "l"]:
                    rekošais_sortiments = "L"
                    i += 1
                    continue
                    
                diam = parse_diametrs(next_word)
                if diam is not None:
                    dati.append({
                        "Stāvs": rekošais_stavs,
                        "Suga": treniska_suga,
                        "Sortiments": rekošais_sortiments,
                        "Diametrs": diam
                    })
                    rekošais_sortiments = "L"
                    i += 1
                else:
                    break
        else:
            diam = parse_diametrs(word)
            if diam is not None and treniska_suga:
                dati.append({
                    "Stāvs": rekošais_stavs,
                    "Suga": treniska_suga,
                    "Sortiments": rekošais_sortiments,
                    "Diametrs": diam
                })
                rekošais_sortiments = "L"
            i += 1
            
    return dati

def izveidot_dastlapu_matrix(df):
    pakapes = [8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60]
    pivot = pd.pivot_table(
        df, 
        index='Diametrs', 
        columns=['Suga', 'Sortiments'], 
        aggfunc='size', 
        fill_value=0
    )
    pivot = pivot.reindex(pakapes, fill_value=0)
    pivot.index.name = 'Diametra pakāpe'
    return pivot

if uploaded_file is not None:
    if st.button("Sākt audio faila apstrādi", type="primary"):
        with st.spinner("Notiek audio konvertēšana un balss atpazīšana..."):
            try:
                suffix = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
                    tmp_in.write(uploaded_file.read())
                    in_path = tmp_in.name
                
                wav_path = in_path + ".wav"
                sound = AudioSegment.from_file(in_path)
                sound.export(wav_path, format="wav")
                
                r = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio_data = r.record(source)
                    teksts = r.recognize_google(audio_data, language="lv-LV").lower()
                
                os.remove(in_path)
                os.remove(wav_path)
                
                st.info(f"**Atpazītais teksts:**\n\n\"{teksts}\"")
                
                dati = parsat_tekstu(teksts)
                if dati:
                    df = pd.DataFrame(dati)
                    st.success("Dastošanas lapa sagatavota!")
                    dastlapa_df = izveidot_dastlapu_matrix(df)
                    st.dataframe(dastlapa_df, use_container_width=True)
                    
                    csv = dastlapa_df.to_csv().encode('utf-8')
                    st.download_button("📥 Lejupielādēt Dastlapu (CSV)", data=csv, file_name="dastlapa.csv", mime="text/csv")
                else:
                    st.warning("Tekstā neizdevās atpazīt nevienu koku. Pārbaudi ierakstu.")
            except Exception as e:
                st.error(f"Kļūda apstrādē: {e}")
