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
    """Limpia el formato del Excel (coma=miles, punto=decimal)"""
    try:
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val: return 0.0
        # Quitamos la coma (miles) para que Python lo trate como número
        s = s_val.replace(',', '')
        return float(s)
    except: return 0.0

def formato_excel(valor):
    """Formato solicitado: 1,234,567.89 (Coma miles, Punto decimal)"""
    return "{:,.2f}".format(valor)

# --- BARRA LATERAL: BUSCADOR Y CALCULADORA ---
st.sidebar.title("🛠️ Herramientas de Control")

with st.sidebar.expander("🔍 Buscador de Precios", expanded=True):
    t_input = st.text_input("Nemotécnico (ej: BCI, LTM):", "").upper().strip()
    if t_input:
        t_search = t_input if ".SN" in t_input else f"{t_input}.SN"
        try:
            stock = yf.Ticker(t_search)
            hist = stock.history(period="1d")
            if not hist.empty:
                st.success(f"{t_input}: {formato_excel(hist['Close'].iloc[-1])}")
            else: st.error("Sin datos.")
        except: st.error("Error de conexión.")

with st.sidebar.expander("🧮 Calculadora de Montos", expanded=False):
    st.write("Precio × Cantidad")
    c_precio = st.number_input("Precio ($)", min_value=0.0, step=1.0, format="%.2f")
    c_cant = st.number_input("Cantidad", min_value=0, step=1)
    st.info(f"**Monto:**\n{formato_excel(c_precio * c_cant)}")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Hoja actual:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Terminal de Gestión Activa")
        
        # 1. Variación IPSA Real (Mercado en vivo)
        try:
            ipsa_ticker = yf.Ticker("^IPSA")
            ipsa_hist = ipsa_ticker.history(period="2d")
            ipsa_actual = ipsa_hist['Close'].iloc[-1]
            ipsa_previo = ipsa_hist['Close'].iloc[-2]
            var_ipsa = (ipsa_actual / ipsa_previo) - 1
        except: var_ipsa = 0.0

        # 2. Datos del Excel (Fila 6 en adelante)
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna()] # Filtro por fecha en Columna C

        # 3. Lógica de Cálculo Exacto de Patrimonio por fila
        def calcular_patrimonio(fila):
            suma_acciones = 0
            # Acciones desde Columna H (índice 7) de 3 en 3
            num_cols = len(fila)
            for c in range(7, num_cols, 3):
                if c + 1 < num_cols:
                    suma_acciones += (limpiar_num(fila[c]) * limpiar_num(fila[c+1]))
            # Se suma F (índice 5) y G (índice 6) según tu fórmula
            return suma_acciones + limpiar_num(fila[5]) + limpiar_num(fila[6])

        df_clean['Patrimonio_Calculado'] = df_clean.apply(calcular_patrimonio, axis=1)
        
        # DATOS DINÁMICOS DE LA ÚLTIMA FILA INGRESADA
        ultima = df_clean.iloc[-1]
        val_cartera_actual = ultima['Patrimonio_Calculado']
        caja_sobrante_actual = limpiar_num(ultima[5]) # Columna F
        fecha_actualizada = str(ultima[2]) # Fecha de la última fila

        # --- MÉTRICAS SUPERIORES (Cuadros de Resumen) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Valor de Cartera", f"${formato_excel(val_cartera_actual)}")
        m2.metric("IPSA (Mercado Live)", f"{var_ipsa:+.2%}", delta_color="normal")
        m3.metric("Caja Sobrante (F)", f"${formato_excel(caja_sobrante_actual)}")
        m4.metric("Fecha del Dato", fecha_actualizada)

        st.divider()

        # --- TABLA DE EVOLUCIÓN ---
        st.subheader("📈 Historial del Valor de Cartera")
        df_evol = df_clean[[2, 1, 'Patrimonio_Calculado']].copy()
        df_evol.columns = ["Fecha", "Periodo", "Total Cartera ($)"]
        df_evol["Total Cartera ($)"] = df_evol["Total Cartera ($)"].apply(formato_excel)
        st.dataframe(df_evol, use_container_width=True, hide_index=True)

        st.divider()

        # --- DESPLEGABLES INDIVIDUALES POR ACCIÓN ---
        st.subheader("📋 Detalle de Títulos (Calculado)")
        for c in range(7, df_raw.shape[1], 3):
            if c + 1 < df_raw.shape[1]:
                nombre = str(df_raw.iloc[3, c]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    h = df_clean[[2, 1, c, c+1]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                    
                    # Cálculo del Monto por día (Precio * Cantidad)
                    h["Monto ($)"] = h["Precio"].apply(limpiar_num) * h["Cantidad"].apply(limpiar_num)
                    
                    # Aplicar formato visual de Excel
                    h_vista = h.copy()
                    for col in ["Precio", "Cantidad", "Monto ($)"]:
                        h_vista[col] = h_vista[col].apply(formato_excel)

                    with st.expander(f"🔹 {nombre}"):
                        # Mostramos solo los días que tienen precio registrado
                        st.dataframe(h_vista[h["Precio"].apply(limpiar_num) > 0], use_container_width=True, hide_index=True)

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
