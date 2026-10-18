import streamlit as st
import pandas as pd

st.set_page_config(page_title="Meža Dastošanas Asistents", layout="wide")

st.title("🌲 Meža Dastošanas Asistents")
st.write("Mobilā dastošanas lapa. Noklikšķini zemāk esošajā lodziņā un izmanto telefona tastatūras mikrofonu, lai diktētu datus.")

# Lodziņš, kurā telefona tastatūras mikrofons ieraksta tavu balsi tieši tekstā
teksts_input = st.text_area(
    "Datu ievade (vai diktēšana):", 
    placeholder="Piemēram: egle puse 24, egle malka 24, otrais stāvs egle 12..."
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
        "liepa": "Liepa"
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
        elif word in ["otrais", "2.", "otrā"]:
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

if st.button("Ģenerēt Dastlapu", type="primary"):
    if teksts_input.strip():
        dati = parsat_tekstu(teksts_input)
        if dati:
            df = pd.DataFrame(dati)
            st.success("Dastlapa veiksmīgi sagatavota!")
            dastlapa_df = izveidot_dastlapu_matrix(df)
            st.dataframe(dastlapa_df, use_container_width=True)
            
            with st.expander("Skatīt koku sarakstu"):
                st.dataframe(df, use_container_width=True)
            
            csv = dastlapa_df.to_csv().encode('utf-8')
            st.download_button("📥 Lejupielādēt Dastlapu (CSV)", data=csv, file_name="dastlapa.csv", mime="text/csv")
        else:
            st.warning("Neizdevās atpazīt datus. Pārbaudi ievadīto tekstu.")
    else:
        st.warning("Lūdzu, ievadi vai diktē datus.")
