import streamlit as st
import whisper
import pandas as pd
import tempfile
import os

st.set_page_config(page_title="Meža Dastošanas Asistents", layout="wide")

st.title("🌲 Meža Dastošanas Balss Asistents")
st.write("Augšupielādē audio ierakstu (mp3, wav, m4a), un programma atpazīs koku sugas, diametrus un stāvus.")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")

with st.spinner("Notiek balss atpazīšanas modeļa ielāde..."):
    model = load_whisper_model()

uploaded_file = st.file_uploader("Izvēlies audio ierakstu:", type=["mp3", "wav", "m4a"])

def parsat_tekstu(teksts):
    sugu_kartpe = {
        "egle": "Egle",
        "priede": "Priede",
        "bērzs": "Bērzs",
        "apse": "Apse",
        "malnalksnis": "melnalksnis",
        "balts": "Baltalksnis",
        "baltalksnis": "Baltalksnis",
        "ozols": "Ozols",
        "liepa": "Liepa"
    }

    words = teksts.split()
    dati = []
    rekošais_stavs = "1. stāvs"
    treniska_suga = None

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
        elif word == "stāvs" and i + 1 < len(words):
            if words[i+1] in ["1", "pirmais"]:
                rekošais_stavs = "1. stāvs"
            elif words[i+1] in ["2", "otrais"]:
                rekošais_stavs = "2. stāvs"
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
            while i < len(words):
                next_word = words[i].strip(",.-")
                if next_word.isdigit():
                    dati.append({
                        "Stāvs": rekošais_stavs,
                        "Suga": treniska_suga,
                        "Diametrs": int(next_word)
                    })
                    i += 1
                else:
                    break
        else:
            if word.isdigit() and treniska_suga:
                dati.append({
                    "Stāvs": rekošais_stavs,
                    "Suga": treniska_suga,
                    "Diametrs": int(word)
                })
            i += 1

    return dati

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    if st.button("Sākt audio apstrādi", type="primary"):
        with st.spinner("Notiek klausīšanās un datu šķirošana..."):
            result = model.transcribe(tmp_path, language="lv")
            teksts = result["text"].lower()

            st.info(f"**Atpazītais teksts:**\n\n\"{teksts}\"")

            dati = parsat_tekstu(teksts)

            if dati:
                df = pd.DataFrame(dati)

                st.success("Dati apstrādāti!")
                st.subheader("📋 Detalizēts koku saraksts")
                st.dataframe(df, use_container_width=True)

                st.subheader("📊 Kopsavilkums pa stāviem un sugām")
                kopsavilkums = df.groupby(['Stāvs', 'Suga']).agg(
                    Koku_skaits=('Diametrs', 'count'),
                    Vid_diametrs=('Diametrs', 'mean')
                ).reset_index()
                kopsavilkums['Vid_diametrs'] = kopsavilkums['Vid_diametrs'].round(1)
                st.dataframe(kopsavilkums, use_container_width=True)

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Lejupielādēt CSV datus",
                    data=csv,
                    file_name="meza_dasti.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Neizdevās atpazīt nevienu koku. Pārbaudi, vai ierakstā skaidri nosaukta suga un izmērs.")

    if os.path.exists(tmp_path):
        os.remove(tmp_path)
