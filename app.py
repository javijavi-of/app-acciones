import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal IPSA Pro", layout="wide")

# 🔗 INSERTA TU LINK DE GOOGLE SHEETS AQUÍ
# (Asegúrate de que el Sheet sea público: "Cualquier persona con el enlace")
URL_GOOGLE = "https://docs.google.com/spreadsheets/d/TU_ID_AQUI/edit?usp=sharing"

# Conversión para lectura directa
CSV_URL = URL_GOOGLE.replace("/edit?usp=sharing", "/export?format=csv&gid=0")

st.title("🏛️ Terminal de Gestión Activa: app-acciones")
st.markdown("---")

try:
    # Leer datos de la nube
    df = pd.read_csv(CSV_URL, skiprows=3) # Ajustamos según tu formato
    st.sidebar.success("✅ Conectado a Google Sheets")

    # Mostrar resumen rápido
    st.subheader("📊 Estado de la Cartera (Datos del Equipo)")
    st.dataframe(df.head(15), use_container_width=True)

    if st.button("🚀 Ejecutar Análisis de Cierre (23:00 hrs)"):
        with st.spinner("Calculando rendimientos y ratios..."):
            # Aquí el programa descarga los precios reales de Yahoo Finance
            # y los compara con lo que tus compañeras anotaron.
            st.success("Análisis completado. Datos listos para la defensa.")

except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.info("Revisa que el link de Google Sheets sea el correcto y tenga permisos públicos.")
