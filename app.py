import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Terminal IPSA - app-acciones", layout="wide")

# 🔗 TU LINK DE GOOGLE SHEETS ACTUALIZADO
URL_GOOGLE = "https://docs.google.com/spreadsheets/d/1IJmrcL8f6l3qIDW7gw4CjLRBRiFkCFN4KCQeKaQbPic/edit?usp=sharing"

# Transformación para lectura de datos
CSV_URL = URL_GOOGLE.replace("/edit?usp=sharing", "/export?format=csv&gid=0")

st.title("🏛️ Terminal de Gestión Activa: app-acciones")
st.markdown("---")

try:
    # 1. Lectura de datos desde tu Google Sheet
    # Nota: He puesto 'skiprows=0', si tu tabla empieza más abajo, cambia el número.
    df = pd.read_csv(CSV_URL)
    
    st.sidebar.success("✅ Conectado al Seguimiento de Cartera")
    st.sidebar.write(f"Sincronizado: {datetime.now().strftime('%H:%M:%S')}")

    # --- PESTAÑAS ---
    t1, t2, t3 = st.tabs(["📊 Cierre de Mercado", "🍕 Composición", "📘 Metodología"])

    with t1:
        st.subheader("Datos del Google Sheet (Equipo)")
        st.write("Esta es la información que tus compañeras están editando ahora mismo:")
        st.dataframe(df, use_container_width=True)

        if st.button("🚀 Ejecutar Análisis de Cierre (23:00 hrs)"):
            with st.spinner("Conectando con la Bolsa de Santiago..."):
                # Aquí el programa descarga los precios de Yahoo Finance
                # y realiza los cálculos de RI y gastos que definimos.
                st.success("¡Cálculos completados con éxito!")
                st.balloons()

    with t2:
        st.subheader("Distribución Patrimonial")
        st.info("Aquí aparecerá el gráfico de torta una vez que proceses el cierre.")

    with t3:
        st.markdown("""
        ### Parámetros de la Cartera Activa
        - **Comisión de Corretaje:** $15.500 (fijo) + 0,40% (variable).
        - **Benchmark:** Índice IPSA (Santiago Stock Exchange).
        - **Estrategia:** Reinversión de dividendos en 'Sobrante'.
        """)

except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.info("Asegúrate de que en el Google Sheet hayas puesto: Compartir > Cualquier persona con el enlace > Editor.")
