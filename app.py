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
    """Limpia datos del Excel considerando coma como miles y punto como decimal"""
    try:
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val: return 0.0
        # Quitamos las comas (separador de miles) para que Python pueda operar
        s = s_val.replace(',', '')
        return float(s)
    except: return 0.0

def formato_excel(valor):
    """Formato: 1,234,567.89 (Coma miles, Punto decimal)"""
    return "{:,.2f}".format(valor)

# --- BARRA LATERAL: HERRAMIENTAS ---
st.sidebar.title("🛠️ Control de Gestión")

# 1. Buscador (Yahoo Finance)
with st.sidebar.expander("🔍 Buscador de Precios", expanded=True):
    t_input = st.text_input("Nemotécnico (ej: BCI, LTM):", "").upper().strip()
    if t_input:
        t_search = t_input if ".SN" in t_input else f"{t_input}.SN"
        try:
            stock = yf.Ticker(t_search)
            hist = stock.history(period="1d")
            if not hist.empty:
                st.success(f"{t_input}: {formato_excel(hist['Close'].iloc[-1])}")
            else: st.error("No se encontraron datos.")
        except: st.error("Error de conexión.")

# 2. Calculadora rápida
with st.sidebar.expander("🧮 Calculadora de Montos", expanded=False):
    c_precio = st.number_input("Precio ($)", min_value=0.0, step=1.0, format="%.2f")
    c_cant = st.number_input("Cantidad", min_value=0, step=1)
    st.info(f"**Monto Total:**\n{formato_excel(c_precio * c_cant)}")

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
        df_clean = df_clean[df_clean[2].notna()] # Filtro por fecha

        # --- MOTOR DE CÁLCULO (LA LÓGICA QUE ME PEDISTE) ---
        def auditor_cartera(fila):
            # Sumamos (Precio * Cantidad) de cada acción (Empiezan en col H=7 de 3 en 3)
            sumatoria_acciones = 0
            num_cols = len(fila)
            for c in range(7, num_cols, 3):
                if c + 1 < num_cols:
                    p = limpiar_num(fila[c])
                    q = limpiar_num(fila[c+1])
                    sumatoria_acciones += (p * q)
            
            # Agregamos las celdas F (índice 5) y G (índice 6) de tu fórmula de Excel
            f_val = limpiar_num(fila[5])
            g_val = limpiar_num(fila[6])
            
            return sumatoria_acciones + f_val + g_val

        # Python realiza el cálculo fila por fila
        df_clean['Patrimonio_Calculado'] = df_clean.apply(auditor_cartera, axis=1)
        
        # Último dato registrado
        ultima = df_clean.iloc[-1]
        total_hoy = ultima['Patrimonio_Calculado']
        caja_f = limpiar_num(ultima[5])

        # --- MÉTRICAS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Valor Cartera (Acciones + F + G)", formato_excel(total_hoy))
        m2.metric("IPSA Hoy", "{:+.2%}".format(ret_ipsa))
        m3.metric("Caja Sobrante (F)", formato_excel(caja_f))
        m4.metric("Fecha Sistema", datetime.now().strftime("%d/%m/%Y"))

        st.divider()

        # --- TABLA DE EVOLUCIÓN CALCULADA ---
        st.subheader("📈 Evolución Diaria (Sumatoria de Inversiones)")
        df_evol = df_clean[[2, 1, 'Patrimonio_Calculado']].copy()
        df_evol.columns = ["Fecha", "Periodo", "Patrimonio Total ($)"]
        # Formatear números para la tabla
        df_evol["Patrimonio Total ($)"] = df_evol["Patrimonio Total ($)"].apply(formato_excel)
        st.dataframe(df_evol, use_container_width=True, hide_index=True)

        st.divider()

        # --- DETALLE INDIVIDUAL ---
        st.subheader("📋 Detalle de Inversión por Acción")
        max_c = df_raw.shape[1]
        for c in range(7, max_c, 3):
            if c + 1 < max_c:
                nombre = str(df_raw.iloc[3, c]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    h = df_clean[[2, 1, c, c+1]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                    
                    # Cálculos individuales por día
                    h["Precio"] = h["Precio"].apply(limpiar_num)
                    h["Cantidad"] = h["Cantidad"].apply(limpiar_num)
                    h["Total Invertido ($)"] = h["Precio"] * h["Cantidad"]
                    
                    # Formatear para visualización
                    h_vista = h.copy()
                    for col in ["Precio", "Cantidad", "Total Invertido ($)"]:
                        h_vista[col] = h_vista[col].apply(formato_excel)

                    with st.expander(f"🔹 {nombre}"):
                        st.dataframe(h_vista[h["Precio"] > 0], use_container_width=True, hide_index=True)

    elif seleccion == "Omega":
        st.title("📉 Hoja Omega")
        df_omega = df_raw.iloc[2:87, 1:8].copy()
        df_omega.columns = df_omega.iloc[0]
        st.dataframe(df_omega.iloc[1:].replace("#VALUE!", "0"), use_container_width=True, hide_index=True)

    else:
        st.title(f"📄 Hoja: {seleccion}")
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error detectado: {e}")
