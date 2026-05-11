import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="IPSA Terminal Histórica", layout="wide")

URL_GOOGLE = "https://docs.google.com/spreadsheets/d/1IJmrcL8f6l3qIDW7gw4CjLRBRiFkCFN4KCQeKaQbPic/edit?usp=sharing"
CSV_URL = URL_GOOGLE.replace("/edit?usp=sharing", "/export?format=csv")

st.title("🏛️ Terminal de Gestión Activa: app-acciones")
st.markdown("_Historial sincronizado del equipo (Registro Manual)_")
st.markdown("---")

def limpiar_numero(valor):
    """Limpia formatos de moneda chilena (puntos y comas)"""
    try:
        if pd.isna(valor) or str(valor).strip() == "": 
            return 0.0
        # Quitamos puntos de miles y cambiamos coma decimal por punto
        s = str(valor).replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

try:
    # 1. CARGA DE DATOS
    raw_df = pd.read_csv(CSV_URL, header=None)
    
    # 2. SEPARACIÓN DE DATOS
    fila_nombres = 3
    fila_inicio_datos = 5
    
    df_datos = raw_df.iloc[fila_inicio_datos:].copy()
    # Solo filas que tengan una fecha (Columna C / Índice 2)
    df_datos = df_datos[df_datos[2].notna()]

    # 3. MÉTRICAS SUPERIORES
    if not df_datos.empty:
        ultima = df_datos.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Valor Total Cartera", f"${limpiar_numero(ultima[4]):,.0f}")
        c2.metric("Caja (Sobrante)", f"${limpiar_numero(ultima[5]):,.0f}")
        c3.metric("Última Fecha", str(ultima[2]))
    
    st.divider()

    # 4. PROCESAMIENTO DE ACCIONES
    principales = ["ANDINAB", "BCI", "BSANTANDER", "CENCOMALLS", "MALLPLAZA", 
                   "PARAUCO", "SALFACORP", "SQMB", "ECL", "ENELCHILE", 
                   "ILC", "OROBLANCO", "ENELGXCH", "NORTEGRAN", "SQMA"]
    
    found_principales = []
    found_otros = []

    # Recorremos las columnas buscando acciones (Desde índice 7 de 3 en 3)
    for col in range(7, raw_df.shape[1], 3):
        nombre = str(raw_df.iloc[fila_nombres, col]).strip().upper()
        
        if nombre and nombre != "NAN" and "UNNAMED" not in nombre:
            # Construimos la tabla histórica de esta acción
            hist = df_datos[[2, 1, col, col+1, col+2]].copy()
            hist.columns = ["Fecha", "Periodo", "Precio Cierre", "N° Acciones", "Total"]
            
            # Limpiamos los números de las 3 columnas financieras
            for c_name in ["Precio Cierre", "N° Acciones", "Total"]:
                hist[c_name] = hist[c_name].apply(limpiar_numero)

            if nombre in principales:
                found_principales.append((nombre, hist))
            else:
                found_otros.append((nombre, hist))

    # --- RENDERIZADO VISUAL ---
    st.subheader("📋 Historial por Título (15 Principales)")
    for name, data in found_principales:
        with st.expander(f"📈 {name} - Ver historial de investigación manual"):
            st.dataframe(data, use_container_width=True, hide_index=True)

    if found_otros:
        st.divider()
        st.subheader("📂 Otros Títulos en Cartera")
        for name, data in found_otros:
            with st.expander(f"📎 {name}"):
                st.dataframe(data, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error al organizar el historial: {e}")
