import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="IPSA Terminal Histórica", layout="wide")

URL_GOOGLE = "https://docs.google.com/spreadsheets/d/1IJmrcL8f6l3qIDW7gw4CjLRBRiFkCFN4KCQeKaQbPic/edit?usp=sharing"
CSV_URL = URL_GOOGLE.replace("/edit?usp=sharing", "/export?format=csv")

st.title("🏛️ Terminal de Gestión Activa: app-acciones")
st.markdown("_Sincronizado con el registro manual del equipo_")
st.markdown("---")

try:
    # 1. CARGA COMPLETA DE DATOS
    raw_df = pd.read_csv(CSV_URL, header=None)
    
    # Identificamos los Tickers (Están en la fila 4 del Excel -> índice 3)
    fila_tickers = 3
    tickers_principales = ["ANDINAB", "BCI", "BSANTANDER", "CENCOMALLS", "MALLPLAZA", 
                          "PARAUCO", "SALFACORP", "SQMB", "ECL", "ENELCHILE", 
                          "ILC", "OROBLANCO", "ENELGXCH", "NORTEGRAN", "SQMA"]
    
    # 2. SECCIÓN DE MÉTRICAS (Última fila con datos)
    df_con_fecha = raw_df[raw_df[2].notna()].iloc[4:] # Saltamos encabezados
    ultima_fila = df_con_fecha.iloc[-1]
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Valor Total Cartera", f"${float(str(ultima_fila[4]).replace('.','')):,.0f}")
    with m2:
        st.metric("Caja (Sobrante)", f"${float(str(ultima_fila[5]).replace('.','')):,.0f}")
    with m3:
        st.metric("Fecha de Cierre", str(ultima_fila[2]))

    st.divider()

    # 3. GENERACIÓN DE DESPLEGABLES CON HISTORIAL
    st.subheader("📋 Detalle Histórico por Título")
    
    # Listas para separar los 15 principales de los "Otros"
    encontrados = []
    otros = []

    # Mapeamos todas las columnas del Excel
    for col_idx in range(7, raw_df.shape[1], 3):
        nombre_ticker = str(raw_df.iloc[fila_tickers, col_idx]).strip()
        
        if nombre_ticker and nombre_ticker != "nan":
            # Creamos el DataFrame histórico para esta acción específica
            # Columnas: Fecha (2), Periodo (1), Precio (idx), Cantidad (idx+1), Total (idx+2)
            historial_accion = df_con_fecha[[2, 1, col_idx, col_idx + 1, col_idx + 2]].copy()
            historial_accion.columns = ["Fecha", "Periodo", "Precio Cierre", "N° Acciones", "Monto Total"]
            
            if nombre_ticker.upper() in tickers_principales:
                encontrados.append((nombre_ticker, historial_accion))
            else:
                otros.append((nombre_ticker, historial_accion))

    # Mostrar los 15 principales
    for ticker, data in encontrados:
        with st.expander(f"📉 {ticker}"):
            st.write(f"**Historial de investigación manual para {ticker}:**")
            st.dataframe(data, use_container_width=True, hide_index=True)

    # 4. APARTADO PARA "OTROS TÍTULOS"
    if otros:
        st.divider()
        st.subheader("📂 Otros Títulos (Fuera de los 15 principales)")
        for ticker, data in otros:
            with st.expander(f"📎 {ticker} (Opcional)"):
                st.dataframe(data, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error al procesar el historial: {e}")
    st.info("Asegúrate de que no haya celdas vacías en las columnas de Fecha o Periodo.")
