import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="IPSA Terminal Pro", layout="wide")

# Tu link real
URL_GOOGLE = "https://docs.google.com/spreadsheets/d/1IJmrcL8f6l3qIDW7gw4CjLRBRiFkCFN4KCQeKaQbPic/edit?usp=sharing"

# Transformación de link a CSV
CSV_URL = URL_GOOGLE.replace("/edit?usp=sharing", "/export?format=csv")

st.title("🏛️ Terminal de Gestión Activa: app-acciones")

try:
    # 1. INTENTO DE LECTURA ROBUSTA
    # 'on_bad_lines' hace que no se caiga si hay filas raras
    # 'skiprows' cámbialo si tu tabla no empieza en la fila 1
    df = pd.read_csv(CSV_URL, on_bad_lines='skip') 
    
    st.sidebar.success("✅ Sincronizado con Google Sheets")

    st.subheader("📊 Vista Previa de tus Datos")
    st.write("Si no ves tus acciones abajo, ajusta las filas del Excel:")
    st.dataframe(df)

    # 2. LÓGICA DE ACTUALIZACIÓN
    if st.button("🚀 Calcular Valor de Cartera"):
        st.info("Buscando precios en la Bolsa de Santiago...")
        # Aquí el programa hará la magia con yfinance
        st.balloons()

except Exception as e:
    st.error(f"Hubo un problema al leer el Excel: {e}")
    st.info("💡 Consejo: Asegúrate de que los datos en Google Sheets empiecen desde la celda A1 o que no haya celdas combinadas en la tabla.")
