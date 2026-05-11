import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Financiera IPSA", layout="wide")

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
    """Convierte texto de Excel a número, eliminando comas conflictivas"""
    try:
        if pd.isna(v): return 0.0
        # Quita comas y espacios para que Python pueda hacer la matemática
        s_val = str(v).strip().replace(',', '') 
        if s_val == "" or "#VALUE" in s_val.upper() or "FECHA" in s_val.upper(): return 0.0
        return float(s_val)
    except:
        return 0.0

def formato_excel(valor):
    """Asegura que el valor esté limpio antes de darle formato 1,234,567.89"""
    val_num = limpiar_num(valor) # <- ESTA ES LA MAGIA QUE ARREGLA EL ERROR
    return "{:,.2f}".format(val_num)

# --- BARRA LATERAL ---
st.sidebar.title("🛠️ Herramientas de Control")

with st.sidebar.expander("🔍 Buscador de Precios", expanded=True):
    t_input = st.text_input("Nemotécnico (ej: BCI, LTM):", "").upper().strip()
    if t_input:
        t_search = t_input if ".SN" in t_input else f"{t_input}.SN"
        try:
            stock = yf.Ticker(t_search)
            hist = stock.history(period="1d")
            if not hist.empty:
                st.success(f"{t_input}: ${formato_excel(hist['Close'].iloc[-1])}")
        except: st.sidebar.error("Error de conexión.")

with st.sidebar.expander("🧮 Calculadora de Montos", expanded=False):
    c_precio = st.number_input("Precio ($)", min_value=0.0, step=1.0, format="%.2f")
    c_cant = st.number_input("Cantidad", min_value=0, step=1)
    st.info(f"**Monto:**\n${formato_excel(c_precio * c_cant)}")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Navegar por el Excel:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Terminal de Gestión Activa")
        
        # 1. IPSA Live
        var_ipsa = 0.0
        try:
            ipsa_data = yf.download("^IPSA", period="2d", progress=False)['Close']
            if len(ipsa_data) > 1:
                var_ipsa = (ipsa_data.iloc[-1] / ipsa_data.iloc[-2]) - 1
        except: pass

        # 2. Limpieza de datos
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna()] # Filas con fecha

        # --- MOTOR DE CÁLCULO ---
        def calcular_patrimonio(fila):
            suma_acciones = 0
            for c in range(7, len(fila), 3):
                if c + 1 < len(fila):
                    suma_acciones += (limpiar_num(fila[c]) * limpiar_num(fila[c+1]))
            return suma_acciones + limpiar_num(fila[5]) + limpiar_num(fila[6])

        df_clean['Patrimonio_Total'] = df_clean.apply(calcular_patrimonio, axis=1)

        # 3. FILTRAR PARA MÉTRICAS (Buscamos la última fila con dinero real)
        df_con_dinero = df_clean[df_clean['Patrimonio_Total'] > 0]

        if not df_con_dinero.empty:
            ultimo_dato = df_con_dinero.iloc[-1]
            val_total = ultimo_dato['Patrimonio_Total']
            caja_f = limpiar_num(ultimo_dato[5])

            # --- MÉTRICAS SUPERIORES ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Valor Total Cartera", f"${formato_excel(val_total)}")
            m2.metric("Variación IPSA (Live)", f"{var_ipsa:+.2%}")
            m3.metric("Caja Sobrante (F)", f"${formato_excel(caja_f)}")
            m4.metric("Fecha de Hoy", datetime.now().strftime("%d/%m/%Y"))

            st.divider()

            # --- TABLA DE EVOLUCIÓN ---
            st.subheader("📈 Evolución Diaria del Patrimonio")
            df_evol =
