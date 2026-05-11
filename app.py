import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal IPSA Pro", layout="wide")

BASE_URL = "https://docs.google.com/spreadsheets/d/1IJmrcL8f6l3qIDW7gw4CjLRBRiFkCFN4KCQeKaQbPic/export?format=csv&gid="

HOJAS = {
    "Seguimiento Cartera": "1701047918", 
    "40 acciones": "127922189",
    "Rds. 40 acciones": "67985094",
    "IPSA y Cartera": "445876639",
    "Omega": "426270219",
    "RI": "2022302992"
}

def limpiar_num(v):
    try:
        if pd.isna(v) or str(v).strip() == "" or "#VALUE" in str(v): return 0.0
        s = "".join(c for c in str(v) if c.isdigit() or c in [',', '.'])
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

# --- BARRA LATERAL: BUSCADOR Y NAVEGACIÓN ---
st.sidebar.title("🔍 Consultas y Navegación")

# 1. Buscador de Nemotécnicos
st.sidebar.subheader("Buscar Precio de Cierre")
ticker_search = st.sidebar.text_input("Ingrese Nemotécnico (ej: BCI, COPEC):", "").upper()
if ticker_search:
    try:
        data = yf.download(f"{ticker_search}.SN", period="1d", progress=False)
        if not data.empty:
            precio_actual = data['Close'].iloc[-1]
            st.sidebar.success(f"Precio {ticker_search}: ${precio_actual:,.2f}")
        else:
            st.sidebar.error("No se encontró el ticker.")
    except:
        st.sidebar.error("Error en la búsqueda.")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Ir a la hoja:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Performance de Cartera vs IPSA")
        
        # Obtener datos del IPSA Real
        ipsa_data = yf.download("^IPSA", period="2d", progress=False)['Close']
        ret_ipsa_hoy = (ipsa_data.iloc[-1] / ipsa_data.iloc[-2]) - 1

        # Limpiar datos del Excel
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna() & df_clean[2].astype(str).str.contains(r'\d')]

        if not df_clean.empty:
            # Cálculo de Valor Cartera (Sumando última posición de cada acción)
            valor_activos = 0
            for c in range(7, df_raw.shape[1], 3):
                p = limpiar_num(df_clean.iloc[-1][c])
                q = limpiar_num(df_clean.iloc[-1][c+1])
                valor_activos += (p * q)

            caja = limpiar_num(df_clean.iloc[-1][5])
            patrimonio_total = valor_activos + caja
            
            # --- MÉTRICAS SUPERIORES ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Patrimonio Total", f"${patrimonio_total:,.0f}")
            m2.metric("vs IPSA (Hoy)", f"{ret_ipsa_hoy:+.2%}", delta_color="normal")
            m3.metric("Caja Disponible", f"${caja:,.0f}")
            m4.metric("Fecha de Hoy", datetime.now().strftime("%d/%m/%Y"))

            st.divider()
            
            # --- DESPLEGABLES CON HISTORIAL ---
            for col_idx in range(7, df_raw.shape[1], 3):
                nombre = str(df_raw.iloc[3, col_idx]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    h = df_clean[[2, 1, col_idx, col_idx + 1]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                    h["Precio"] = h["Precio"].apply(limpiar_num)
                    h["Cantidad"] = h["Cantidad"].apply(limpiar_num)
                    h["Monto ($)"] = h["Precio"] * h["Cantidad"]
                    h = h[h["Precio"] > 0]

                    with st.expander(f"📊 {nombre}"):
                        st.dataframe(h, use_container_width=True, hide_index=True)

    elif seleccion == "Omega":
        st.title("📉 Hoja Omega (Análisis de Riesgo)")
        # Rango B3 a H87 -> iloc[filas 2 a 87, columnas 1 a 8]
        df_omega = df_raw.iloc[2:87, 1:8].copy()
        df_omega.columns = df_raw.iloc[2, 1:8] # Títulos de la fila B3:H3
        df_omega = df_omega.iloc[1:] # Quitar la fila de títulos duplicada
        
        # Limpiar #VALUE! por ceros para que se vea ordenado
        df_omega = df_omega.replace("#VALUE!", "0").replace("#VALUE", "0")
        
        st.dataframe(df_omega, use_container_width=True, hide_index=True)

    else:
        st.title(f"📄 Hoja: {seleccion}")
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error en la terminal: {e}")
