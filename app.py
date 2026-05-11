import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal IPSA - Gestión Activa", layout="wide")

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
    """Limpia formatos chilenos y errores de Excel"""
    try:
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val: return 0.0
        s = "".join(c for c in str(v) if c.isdigit() or c in [',', '.'])
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

# --- BARRA LATERAL: HERRAMIENTAS ---
st.sidebar.title("🛠️ Herramientas de Control")

# 1. Buscador de Precios Real-Time (CORREGIDO)
with st.sidebar.expander("🔍 Buscador de Precios (Bolsa Stgo)", expanded=True):
    t_input = st.text_input("Nemotécnico (ej: BCI, LTM, CHILE):", "").upper().strip()
    if t_input:
        t_search = t_input if ".SN" in t_input else f"{t_input}.SN"
        try:
            # Usamos Ticker().history para evitar errores de conexión comunes
            stock = yf.Ticker(t_search)
            hist = stock.history(period="1d")
            if not hist.empty:
                precio_cierre = hist['Close'].iloc[-1]
                st.success(f"{t_input}: ${precio_cierre:,.2f}")
            else:
                st.error("No se encontraron datos para hoy.")
        except:
            st.error("Error de conexión con el mercado.")

# 2. Calculadora para el Cierre
with st.sidebar.expander("🧮 Calculadora de Montos", expanded=False):
    c_precio = st.number_input("Precio Cierre ($)", min_value=0.0, step=1.0)
    c_cant = st.number_input("Cantidad Acciones", min_value=0, step=1)
    st.info(f"**Monto Total:**\n${c_precio * c_cant:,.0f}")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Navegar Hoja:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Terminal de Gestión Activa")
        
        # Benchmarking IPSA Real
        try:
            ipsa = yf.download("^IPSA", period="2d", progress=False)['Close']
            ret_ipsa = (ipsa.iloc[-1] / ipsa.iloc[-2]) - 1
        except: ret_ipsa = 0.0

        # Datos del Excel (Fila 6 / índice 5 en adelante)
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna()] # Filtro por fecha en Columna C

        # --- OBTENCIÓN DE DATOS DIRECTOS DEL EXCEL (COLUMNA E) ---
        # Columna E es índice 4. Columna F es índice 5.
        ultima_fila = df_clean.iloc[-1]
        valor_cartera_excel = limpiar_num(ultima_fila[4]) # Columna E (Valor de la Cartera)
        caja_excel = limpiar_num(ultima_fila[5])         # Columna F (Sobrante)
        patrimonio_total = valor_cartera_excel + caja_excel

        # --- MÉTRICAS PRINCIPALES ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Valor Cartera (Acciones)", f"${valor_cartera_excel:,.0f}")
        m2.metric("Benchmark IPSA (Hoy)", f"{ret_ipsa:+.2%}")
        m3.metric("Caja Sobrante", f"${caja_excel:,.0f}")
        m4.metric("Fecha Sistema", datetime.now().strftime("%d/%m/%Y"))

        st.divider()

        # --- TABLA DE EVOLUCIÓN (DATOS DE COLUMNA E) ---
        st.subheader("📈 Evolución Diaria del Valor Cartera (Excel)")
        # Seleccionamos Fecha (2), Periodo (1) y Valor Cartera (4)
        df_evol = df_clean[[2, 1, 4]].copy()
        df_evol.columns = ["Fecha", "Periodo", "Valor Cartera ($)"]
        # Limpiamos los datos de la columna para que se vean bien en la tabla
        df_evol["Valor Cartera ($)"] = df_evol["Valor Cartera ($)"].apply(limpiar_num)
        st.dataframe(df_evol, use_container_width=True, hide_index=True)

        st.divider()

        # --- DESPLEGABLES POR TÍTULO ---
        st.subheader("📋 Detalle Individual")
        max_c = df_raw.shape[1]
        for c_idx in range(7, max_c, 3):
            # Seguridad para evitar Error 128
            if c_idx + 2 < max_c:
                nombre = str(df_raw.iloc[3, c_idx]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    h = df_clean[[2, 1, c_idx, c_idx + 1, c_idx + 2]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio", "Cantidad", "Monto ($)"]
                    # Limpiamos formatos para visualización
                    for col in ["Precio", "Cantidad", "Monto ($)"]:
                        h[col] = h[col].apply(limpiar_num)
                    
                    with st.expander(f"🔹 {nombre}"):
                        st.dataframe(h[h["Precio"]>0], use_container_width=True, hide_index=True)

    elif seleccion == "Omega":
        st.title("📉 Hoja Omega: Análisis de Riesgo")
        # Filtro estricto B3 a H87
        df_omega = df_raw.iloc[2:87, 1:8].copy()
        df_omega.columns = df_omega.iloc[0]
        st.dataframe(df_omega.iloc[1:].replace("#VALUE!", "0"), use_container_width=True, hide_index=True)

    else:
        st.title(f"📄 Hoja: {seleccion}")
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error detectado: {e}")
