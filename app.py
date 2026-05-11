import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Financiera IPSA", layout="wide", initial_sidebar_state="expanded")

# Link Base y GIDs oficiales
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
    """Limpia cualquier texto, signo o error de Excel (#VALUE!)"""
    try:
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val or "FECHA" in s_val:
            return 0.0
        # Quitamos puntos de mil y cambiamos coma a punto decimal
        s = "".join(c for c in str(v) if c.isdigit() or c in [',', '.'])
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

# --- BARRA LATERAL: BUSCADOR INTELIGENTE ---
st.sidebar.title("🔍 Consultas en Vivo")
st.sidebar.subheader("Buscador de Precios")
# El buscador ahora intenta encontrar la acción en la Bolsa de Santiago automáticamente
t_input = st.sidebar.text_input("Nemotécnico (ej: BCI, SQM-B, COPEC):", "").upper().strip()

if t_input:
    # Parche: si no tiene .SN, se lo ponemos nosotros
    t_search = t_input if ".SN" in t_input else f"{t_input}.SN"
    try:
        with st.sidebar.spinner(f"Buscando {t_input}..."):
            paper = yf.Ticker(t_search)
            info = paper.fast_info
            if 'last_price' in info:
                st.sidebar.success(f"{t_input}: ${info['last_price']:,.2f}")
                st.sidebar.caption(f"Fuente: Yahoo Finance (Bolsa de Stgo)")
            else:
                # Intento alternativo por si fast_info falla
                data = yf.download(t_search, period="1d", progress=False)
                if not data.empty:
                    st.sidebar.success(f"{t_input}: ${data['Close'].iloc[-1]:,.2f}")
                else:
                    st.sidebar.error("No se encontraron datos.")
    except:
        st.sidebar.error("Error de conexión.")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Navegar por el Excel:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Performance de Cartera Activa")
        
        # 1. Obtener IPSA real hoy para comparar
        ipsa = yf.download("^IPSA", period="2d", progress=False)['Close']
        ret_ipsa = (ipsa.iloc[-1] / ipsa.iloc[-2]) - 1 if len(ipsa) > 1 else 0.0

        # 2. Filtrar datos manuales (Fila 6 en adelante)
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna() & df_clean[2].astype(str).str.contains(r'\d')]

        if not df_clean.empty:
            ultima = df_clean.iloc[-1]
            
            # Cálculo automático del patrimonio (Suma de P * Q de cada acción)
            p_acciones = 0
            for c in range(7, df_raw.shape[1], 3):
                p_acciones += (limpiar_num(ultima[c]) * limpiar_num(ultima[c+1]))

            caja = limpiar_num(ultima[5])
            total_patrimonio = p_acciones + caja
            
            # --- MÉTRICAS DE IMPACTO ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Patrimonio Total", f"${total_patrimonio:,.0f}")
            m2.metric("Benchmark IPSA (Hoy)", f"{ret_ipsa:+.2%}")
            m3.metric("Caja (Sobrante)", f"${caja:,.0f}")
            m4.metric("Fecha de Hoy", datetime.now().strftime("%d/%m/%Y"))

            st.divider()
            
            # --- HISTORIAL CARRETERO ---
            st.subheader("📋 Registro Histórico de Investigación")
            for col_idx in range(7, df_raw.shape[1], 3):
                nombre = str(df_raw.iloc[3, col_idx]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    h = df_clean[[2, 1, col_idx, col_idx + 1]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                    h["Precio"] = h["Precio"].apply(limpiar_num)
                    h["Cantidad"] = h["Cantidad"].apply(limpiar_num)
                    # Forzamos el cálculo de la columna Total
                    h["Total ($)"] = h["Precio"] * h["Cantidad"]
                    h = h[h["Precio"] > 0]

                    with st.expander(f"📊 {nombre}"):
                        st.dataframe(h, use_container_width=True, hide_index=True)

    elif seleccion == "Omega":
        st.title("📉 Hoja Omega: Análisis de Riesgo")
        # Rango Quirúrgico: B3 a H87
        df_omega = df_raw.iloc[2:87, 1:8].copy()
        df_omega.columns = df_omega.iloc[0] # Títulos de la fila B3
        df_omega = df_omega.iloc[1:] # Datos desde B4
        
        # Limpieza de errores de Excel
        df_omega = df_omega.replace("#VALUE!", "0").replace("#VALUE", "0")
        
        st.dataframe(df_omega, use_container_width=True, hide_index=True)

    else:
        st.title(f"📄 Hoja: {seleccion}")
        # Limpieza genérica de #VALUE! para el resto de hojas
        st.dataframe(df_raw.iloc[2:].replace("#VALUE!", "0"), use_container_width=True)

except Exception as e:
    st.error(f"Error en la terminal: {e}")
