import streamlit as st
from openai import OpenAI
import json
import pandas as pd
import io

st.set_page_config(page_title="Meža Dastošanas Asistents", layout="wide")

st.title("🌲 Meža Dastošanas Balss Apstrāde")
st.write("Augšupielādē meža balss ierakstu, lai automātiski iegūtu gatavu dastošanas tabulu.")

DASTOSANAS_PROMPTS = """
Tu esi profesionāls meža taksācijas datu apstrādātājs.
Tavs vienīgais uzdevums ir pārvērst meža dastošanas balss transkriptu tīrā JSON datu strukturētā sarakstā.

KOKU SUGAS: Priede, Egle, Bērzs, Melnalksnis, Baltalksnis, Apse, Liepa, Ozols, Osis u.c.

KATEGORIJAS / SORTIMENTI (OBLIGĀTI):
1. Noklusētā kategorija skaitlim uzreiz aiz sugas ir "L" (Lietas koksne).
2. Ja starp skaitļiem vai aiz skaitļa tiek pateikts "puse", "pus" vai "PL":
   - Visi skaitļi PIRMS vārda "puse" pieder pie kategorijas "L".
   - Skaitlis (vai skaitļi), kas seko TIEŠI AIZ vārda "puse", pieder pie kategorijas "PL" (Puslietas koksne).
3. Ja tiek pateikts "malka", "mal" vai "M", sekojošie skaitļi pieder pie "Malka".

PIEMĒRS:
Ievade: "Bērzs 24 puse 28"
Iznākums:
- Suga: Bērzs, Diametrs: 24, Kategorija: L
- Suga: Bērzs, Diametrs: 28, Kategorija: PL

Izvades formāts: TIKAI tīrs JSON masīvs bez papildu teksta:
[
  {"suga": "Bērzs", "diametrs": 24, "kategorija": "L"},
  {"suga": "Bērzs", "diametrs": 28, "kategorija": "PL"}
]
"""

api_key = st.secrets.get("OPENAI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("Ievadi OpenAI API Atslēgu:", type="password")

uploaded_file = st.file_uploader("Pievieno audio failu (.mp3, .wav, .m4a)", type=["mp3", "wav", "m4a"])

if uploaded_file and api_key:
    try:
        # Inicializē jauno OpenAI klientu
        client = OpenAI(api_key=api_key)
        
        if st.button("Sākt apstrādi"):
            with st.spinner("Transkribē audio tekstā..."):
                # Jaunā sintakse audio transkripcijai
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=uploaded_file, 
                    language="lv",
                    prompt="Priede, Egle, Bērzs, Melnalksnis, Baltalksnis, Apse, Liepa, puse, malka, diametrs"
                )
                
                full_transcript = transcript.text
                
                st.subheader("1. Atpazītais teksts:")
                st.info(full_transcript)
                
            with st.spinner("Kārto datus tabulā (L, PL, Malka)..."):
                # Jaunā sintakse čatam / datu strukturēšanai
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": DASTOSANAS_PROMPTS},
                        {"role": "user", "content": f"Apstrādā šo transkriptu: {full_transcript}"}
                    ],
                    temperature=0
                )
                
                raw_json = response.choices[0].message.content.strip()
                if raw_json.startswith("```json"):
                    raw_json = raw_json[7:-3].strip()
                elif raw_json.startswith("```"):
                    raw_json = raw_json[3:-3].strip()
                        
                data = json.loads(raw_json)
                df = pd.DataFrame(data)
                
                st.subheader("2. Gatavā dastlapa:")
                st.dataframe(df, use_container_width=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Dastlapa')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Lejuplādēt Excel failu",
                    data=excel_data,
                    file_name="dastlapa.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                    
    except Exception as e:
        st.error(f"Kļūda apstrādē: {e}")
