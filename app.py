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
    """Limpia los datos del Excel para que Python los entienda"""
    try:
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val: return 0.0
        s = "".join(c for c in str(v) if c.isdigit() or c in [',', '.'])
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

def formato_chile(valor):
    """Transforma un número a formato chileno: 1.234.567,89"""
    return f"{valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

# --- BARRA LATERAL ---
st.sidebar.title("🛠️ Herramientas")

# 1. Buscador (Yahoo Finance)
with st.sidebar.expander("🔍 Buscador de Precios", expanded=True):
    t_input = st.text_input("Nemotécnico (ej: BCI, LTM):", "").upper().strip()
    if t_input:
        t_search = t_input if ".SN" in t_input else f"{t_input}.SN"
        try:
            stock = yf.Ticker(t_search)
            hist = stock.history(period="1d")
            if not hist.empty:
                st.success(f"{t_input}: ${formato_chile(hist['Close'].iloc[-1])}")
            else: st.error("Sin datos.")
        except: st.error("Error de conexión.")

# 2. Calculadora
with st.sidebar.expander("🧮 Calculadora de Montos", expanded=False):
    c_precio = st.number_input("Precio ($)", min_value=0.0, step=1.0)
    c_cant = st.number_input("Cantidad", min_value=0, step=1)
    st.info(f"**Monto:**\n${formato_chile(c_precio * c_cant)}")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Hoja actual:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Terminal de Gestión Activa")
        
        # Benchmarking IPSA
        try:
            ipsa = yf.download("^IPSA", period="2d", progress=False)['Close']
            ret_ipsa = (ipsa.iloc[-1] / ipsa.iloc[-2]) - 1
        except: ret_ipsa = 0.0

        # Datos reales (Fila 6 en adelante)
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna()] # Filtro por fecha en Columna C

        # OBTENEMOS ÚLTIMA FILA PARA MÉTRICAS
        ultima = df_clean.iloc[-1]
        
        # LEEMOS DIRECTO DEL EXCEL (COLUMNA E = índice 4)
        valor_cartera_excel = limpiar_num(ultima[4])
        caja_sobrante = limpiar_num(ultima[5]) # Columna F
        # Patrimonio Total = E6 (que ya incluye F y G en tu fórmula)
        patrimonio_total = valor_cartera_excel 

        # --- MÉTRICAS SUPERIORES ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Valor Cartera (E)", f"${formato_chile(valor_cartera_excel)}")
        m2.metric("IPSA Hoy", f"{ret_ipsa:+.2%}")
        m3.metric("Caja (F)", f"${formato_chile(caja_sobrante)}")
        m4.metric("Hoy", datetime.now().strftime("%d/%m/%Y"))

        st.divider()

        # --- EVOLUCIÓN (COLUMNA E DIRECTA) ---
        st.subheader("📈 Evolución Diaria del Valor de Cartera (Columna E)")
        df_evol = df_clean[[2, 1, 4]].copy()
        df_evol.columns = ["Fecha", "Periodo", "Total Cartera ($)"]
        # Formateamos los números para la tabla
        df_evol["Total Cartera ($)"] = df_evol["Total Cartera ($)"].apply(limpiar_num).apply(formato_chile)
        st.dataframe(df_evol, use_container_width=True, hide_index=True)

        st.divider()

        # --- DESPLEGABLES (PRECIO, CANTIDAD Y MONTO DEL EXCEL) ---
        st.subheader("📋 Detalle Individual por Acción")
        num_cols = df_raw.shape[1]
        for c in range(7, num_cols, 3):
            if c + 2 < num_cols:
                nombre = str(df_raw.iloc[3, c]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    # Leemos Precio (c), Cantidad (c+1) y Monto (c+2) directo del Excel
                    h = df_clean[[2, 1, c, c+1, c+2]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio", "Cantidad", "Monto ($)"]
                    
                    # Formatear datos para la tabla
                    for col in ["Precio", "Cantidad", "Monto ($)"]:
                        h[col] = h[col].apply(limpiar_num).apply(formato_chile)

                    with st.expander(f"🔹 {nombre}"):
                        st.dataframe(h, use_container_width=True, hide_index=True)

    elif seleccion == "Omega":
        st.title("📉 Hoja Omega")
        df_omega = df_raw.iloc[2:87, 1:8].copy()
        df_omega.columns = df_omega.iloc[0]
        st.dataframe(df_omega.iloc[1:].replace("#VALUE!", "0"), use_container_width=True, hide_index=True)

    else:
        st.title(f"📄 Hoja: {seleccion}")
        st.dataframe(df_raw.iloc[2:].replace("#VALUE!", "0"), use_container_width=True)

except Exception as e:
    st.error(f"Error detectado: {e}")
