import streamlit as st
import whisper
import pandas as pd
import tempfile
import os

st.set_page_config(page_title="Meža Dastošanas Asistents", layout="wide")

st.title("🌲 Meža Dastošanas Balss Asistents")
st.write("Augšupielādē audio ierakstu, un programma automātiski aizpildīs dastošanas lapas tabulu.")

@st.cache_resource
def load_whisper_model():
    # Izmantojam 'small' modeli, kas daudz labāk un precīzāk apstrādā latviešu valodu un meža terminus
    return whisper.load_model("small")

with st.spinner("Notiek balss atpazīšanas modeļa ielāde (tas var aizņemt mirkli)..."):
    model = load_whisper_model()

uploaded_file = st.file_uploader(
    "Izvēlies audio ierakstu:", 
    type=["mp3", "wav", "m4a", "caf", "aac", "mp4", "ogg"]
)

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
    
    words = teksts.split()
    dati = []
    rekošais_stavs = "1. stāvs"
    treniska_suga = None
    rekošais_sortiments = "L" # L = Lieta (zāģbaļķis)
    
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
            
        # Sortiments (L, PL, M)
        if word in ["puse", "puslietas", "pl"]:
            rekošais_sortiments = "PL"
            i += 1
            continue
        elif word in ["malka", "m"]:
            rekošais_sortiments = "M"
            i += 1
            continue
        elif word in ["lieta", "l"]:
            rekošais_sortiments = "L"
            i += 1
            continue
        
        # Suga
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
                elif next_word in ["malka", "m"]:
                    rekošais_sortiments = "M"
                    i += 1
                    continue
                elif next_word in ["lieta", "l"]:
                    rekošais_sortiments = "L"
                    i += 1
                    continue
                    
                if next_word.isdigit():
                    dati.append({
                        "Stāvs": rekošais_stavs,
                        "Suga": treniska_suga,
                        "Sortiments": rekošais_sortiments,
                        "Diametrs": int(next_word)
                    })
                    rekošais_sortiments = "L"
                    i += 1
                else:
                    break
        else:
            if word.isdigit() and treniska_suga:
                dati.append({
                    "Stāvs": rekošais_stavs,
                    "Suga": treniska_suga,
                    "Sortiments": rekošais_sortiments,
                    "Diametrs": int(word)
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
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    if st.button("Sākt audio apstrādi", type="primary"):
        with st.spinner("Notiek balss atpazīšana latviešu valodā..."):
            # Stingri pasakām modelim, ka tā ir latviešu valoda, un iedodam sākuma promptu ar terminiem
            result = model.transcribe(
                tmp_path, 
                language="lv", 
                initial_prompt="Egle, priede, bērzs, apse, alksnis, malka, puse, diametrs, stāvs, 8, 12, 16, 20, 24, 28, 32, 36"
            )
            teksts = result["text"].lower()
            
            st.info(f"**Atpazītais teksts:**\n\n\"{teksts}\"")
            
            dati = parsat_tekstu(teksts)
            
            if dati:
                df = pd.DataFrame(dati)
                
                st.success("Dastošanas lapa sagatavota!")
                
                st.subheader("📋 Dastošanas Lapa (Koku skaits pa sugām un sortimentiem)")
                dastlapa_df = izveidot_dastlapu_matrix(df)
                st.dataframe(dastlapa_df, use_container_width=True)
                
                with st.expander("Skatīt detalizētu sarakstu (katru koku atsevišķi)"):
                    st.dataframe(df, use_container_width=True)
                
                csv = dastlapa_df.to_csv().encode('utf-8')
                st.download_button(
                    label="📥 Lejupielādēt Dastlapu (CSV / Excel)",
                    data=csv,
                    file_name="dastlapa.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Neizdevās atpazīt nevienu koku. Pārbaudi, vai ierakstā skaidri nosaukta suga un izmērs.")

    if os.path.exists(tmp_path):
        os.remove(tmp_path)
