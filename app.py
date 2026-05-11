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
    """Limpia datos: coma para miles y punto para decimal"""
    try:
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val: return 0.0
        # Quitamos la coma (miles) para que Python pueda calcular
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
            else: st.error("Sin datos.")
        except: st.error("Error de conexión.")

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
        
        # 1. Variación IPSA Real
        var_ipsa = 0.0
        try:
            ipsa_data = yf.download("^IPSA", period="2d", progress=False)['Close']
            if len(ipsa_data) > 1:
                var_ipsa = (ipsa_data.iloc[-1] / ipsa_data.iloc[-2]) - 1
        except: pass

        # 2. Datos del Excel (Fila 6 en adelante)
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna()] # Solo filas con fecha

        # --- MOTOR DE CÁLCULO ---
        def auditor_cartera(fila):
            suma_acciones = 0
            # Recorremos columnas de acciones (H=7 de 3 en 3)
            # Python multiplica Precio * Cantidad de cada título
            for c in range(7, len(fila), 3):
                if c + 1 < len(fila):
                    p = limpiar_num(fila[c])
                    q = limpiar_num(fila[c+1])
                    suma_acciones += (p * q)
            # Sumamos las celdas F (5) y G (6) adicionales de tu fórmula
            return suma_acciones + limpiar_num(fila[5]) + limpiar_num(fila[6])

        df_clean['Patrimonio_Calculado'] = df_clean.apply(auditor_cartera, axis=1)

        # 3. LÓGICA DE MÉTRICAS (DESFASE DE 1 DÍA)
        if len(df_clean) >= 1:
            # Buscamos la fila de "ayer" (penúltima). Si solo hay una, tomamos la última.
            fila_ayer = df_clean.iloc[-2] if len(df_clean) > 1 else df_clean.iloc[-1]
            
            val_cartera_ayer = fila_ayer['Patrimonio_Calculado']
            caja_ayer = limpiar_num(fila_ayer[5]) # Columna F
            
            # --- MÉTRICAS SUPERIORES ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Valor Cartera (Cierre Ayer)", f"${formato_excel(val_cartera_ayer)}")
            m2.metric("IPSA Hoy (Live)", f"{var_ipsa:+.2%}")
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

            # --- DETALLE POR ACCIÓN (Aquí corregimos el error de sangría) ---
            st.subheader("📋 Detalle de Títulos")
            max_cols = df_raw.shape[1]
            for c_idx in range(7, max_cols, 3):
                if c_idx + 1 < max_cols:
                    nombre = str(df_raw.iloc[3, c_idx]).strip().upper()
                    if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                        h = df_clean[[2, 1, c_idx, c_idx + 1]].copy()
                        h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                        
                        # Cálculo matemático Precio x Cantidad
                        h["Monto ($)"] = h["Precio"].apply(limpiar_num) * h["Cantidad"].apply(limpiar_num)
                        
                        # Formato visual
                        h_vista = h.copy()
                        for col in ["Precio", "Cantidad", "Monto ($)"]:
                            h_vista[col] = h_vista[col].apply(formato_excel)

                        with st.expander(f"🔹 {nombre}"):
                            # Solo mostrar si hay datos
                            st.dataframe(h_vista[h["Precio"].apply(limpiar_num) > 0], use_container_width=True, hide_index=True)
        else:
            st.info("Ingresa al menos una fila con datos en tu Excel.")

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
