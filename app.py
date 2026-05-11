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
    """Limpia datos: maneja comas como miles y puntos como decimales"""
    try:
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val: return 0.0
        # Eliminamos la coma de miles para que Python lo procese
        s = s_val.replace(',', '')
        return float(s)
    except: return 0.0

def formato_excel(valor):
    """Formato: 1,234,567.89"""
    try:
        return "{:,.2f}".format(float(valor))
    except: return "0.00"

# --- BARRA LATERAL ---
st.sidebar.title("🛠️ Herramientas")

with st.sidebar.expander("🔍 Buscador de Precios", expanded=True):
    t_input = st.text_input("Nemotécnico (ej: BCI, LTM):", "").upper().strip()
    if t_input:
        t_search = t_input if ".SN" in t_input else f"{t_input}.SN"
        try:
            stock = yf.Ticker(t_search)
            hist = stock.history(period="1d")
            if not hist.empty:
                st.success(f"{t_input}: {formato_excel(hist['Close'].iloc[-1])}")
        except: st.sidebar.error("Error de conexión.")

with st.sidebar.expander("🧮 Calculadora de Montos", expanded=False):
    c_precio = st.number_input("Precio ($)", min_value=0.0, step=1.0, format="%.2f")
    c_cant = st.number_input("Cantidad", min_value=0, step=1)
    st.info(f"**Monto:**\n{formato_excel(c_precio * c_cant)}")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Ir a:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Terminal de Gestión Activa")
        
        # 1. IPSA en Vivo
        var_ipsa = 0.0
        try:
            ipsa_data = yf.download("^IPSA", period="2d", progress=False)['Close']
            if len(ipsa_data) > 1:
                var_ipsa = (ipsa_data.iloc[-1] / ipsa_data.iloc[-2]) - 1
        except: pass

        # 2. Datos del Excel
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna()] # Filtro de filas con fecha

        # --- MOTOR DE CÁLCULO (LA LÓGICA QUE TE FUNCIONÓ) ---
        def auditor_cartera(fila):
            suma_acciones = 0
            for c in range(7, len(fila), 3):
                if c + 1 < len(fila):
                    suma_acciones += (limpiar_num(fila[c]) * limpiar_num(fila[c+1]))
            # Suma F (5) y G (6)
            return suma_acciones + limpiar_num(fila[5]) + limpiar_num(fila[6])

        df_clean['Patrimonio_Calculado'] = df_clean.apply(auditor_cartera, axis=1)

        # 3. LÓGICA DE MÉTRICAS (DESFASE 1 DÍA)
        if len(df_clean) >= 2:
            # Tomamos la penúltima fila (ayer) para el valor de la métrica
            # Si solo hay una fila, tomamos esa.
            fila_metrica = df_clean.iloc[-2] if len(df_clean) > 1 else df_clean.iloc[-1]
            
            val_cartera_ayer = fila_metrica['Patrimonio_Calculado']
            caja_ayer = limpiar_num(fila_metrica[5])
            
            # --- MÉTRICAS SUPERIORES ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Valor de Cartera (Cierre)", f"${formato_excel(val_cartera_ayer)}")
            m2.metric("IPSA (Live)", f"{var_ipsa:+.2%}")
            m3.metric("Caja Sobrante (F)", f"${formato_excel(caja_ayer)}")
            m4.metric("Fecha de Hoy", datetime.now().strftime("%d/%m/%Y"))

            st.divider()

            # --- TABLA DE EVOLUCIÓN ---
            st.subheader("📈 Evolución Diaria del Patrimonio")
            df_evol = df_clean[[2, 1, 'Patrimonio_Calculado']].copy()
            df_evol.columns = ["Fecha", "Periodo", "Patrimonio Total ($)"]
            df_evol["Patrimonio Total ($)"] = df_evol["Patrimonio Total ($)"].apply(formato_excel)
            st.dataframe(df_evol, use_container_width=True, hide_index=True)

            st.divider()

            # --- DETALLE POR ACCIÓN ---
            st.subheader("📋 Detalle de Títulos")
            for c in range(7, df_raw.shape[1], 3):
