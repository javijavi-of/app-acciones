import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="IPSA Terminal Histórica", layout="wide")

URL_GOOGLE = "https://docs.google.com/spreadsheets/d/1IJmrcL8f6l3qIDW7gw4CjLRBRiFkCFN4KCQeKaQbPic/edit?usp=sharing"
CSV_URL = URL_GOOGLE.replace("/edit?usp=sharing", "/export?format=csv")

st.title("🏛️ Terminal de Gestión Activa: app-acciones")
st.markdown("_Historial sincronizado del equipo_")
st.markdown("---")

try:
    # 1. CARGA DE DATOS BRUTOS
    raw_df = pd.read_csv(CSV_URL, header=None)
    
    # 2. DEFINICIÓN DE COORDENADAS (Basado en tu Excel)
    fila_nombres = 3  # Fila 4 del Excel donde están los nombres (ANDINAB, etc.)
    fila_inicio_datos = 5 # Fila donde empiezan los registros diarios (Fecha, Precio...)
    
    # Lista de tus 15 acciones principales
    principales_lista = ["ANDINAB", "BCI", "BSANTANDER", "CENCOMALLS", "MALLPLAZA", 
                         "PARAUCO", "SALFACORP", "SQMB", "ECL", "ENELCHILE", 
                         "ILC", "OROBLANCO", "ENELGXCH", "NORTEGRAN", "SQMA"]

    # 3. FILTRADO DE FILAS CON DATOS REALES
    # Filtramos para quedarnos solo con las filas que tienen una Fecha válida (Columna C / Índice 2)
    df_limpio = raw_df.iloc[fila_inicio_datos:].copy()
    df_limpio = df_limpio[df_limpio[2].notna()] # Solo filas con fecha

    # 4. MÉTRICAS GENERALES (Tomadas de la última fila registrada)
    if not df_limpio.empty:
        ultima_fila = df_limpio.iloc[-1]
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Valor Total Cartera", f"${float(str(ultima_fila[4]).replace('.','')):,.0f}")
        with m2:
            st.metric("Caja (Sobrante)", f"${float(str(ultima_fila[5]).replace('.','')):,.0f}")
        with m3:
            st.metric("Último Cierre", str(ultima_fila[2]))

    st.divider()

    # 5. PROCESAMIENTO DE CADA ACCIÓN
    st.subheader("📋 Detalle Histórico por Título")
    
    col_activos_principales = []
    col_activos_otros = []

    # Recorremos el Excel buscando columnas de acciones (empiezan en H / Índice 7)
    for c in range(7, raw_df.shape[1], 3):
        nombre = str(raw_df.iloc[fila_nombres, c]).strip().upper()
        
        if nombre and nombre != "NAN" and "UNNAMED" not in nombre:
            # Construimos la tabla histórica para ESTA acción
            # Columnas: Fecha (2), Periodo (1), Precio (c), Cantidad (c+1), Total (c+2)
            historia = df_limpio[[2, 1, c, c+1, c+2]].copy()
            historia.columns = ["Fecha", "Periodo", "Precio Cierre", "N° Acciones", "Monto Total"]
            
            # Limpieza de datos: quitar filas donde el precio sea 0 o NaN
            historia = historia[historia["Precio Cierre"].notna()]
            
            if nombre in principales_lista:
                col_activos_principales.append((nombre, historia))
            else:
                col_activos_otros.append((nombre, historia))

    # --- MOSTRAR LOS 15 PRINCIPALES ---
    for ticker, tabla in col_activos_principales:
        with st.expander(f"📉 {ticker} (Ver Historial)"):
            st.dataframe(tabla, use_container_width=True, hide_index=True)

    # --- MOSTRAR OTROS TÍTULOS ---
    if col_activos_otros:
        st.divider()
        with st.container():
            st.subheader("📂 Otros Títulos Detectados")
            for ticker, tabla in col_activos_otros:
                with st.expander(f"📎 {ticker}"):
                    st.dataframe(tabla, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error al organizar los datos: {e}")
    st.info("Revisa que no existan celdas combinadas en la zona de datos del Google Sheet.")
