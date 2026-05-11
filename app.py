import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Terminal IPSA - Gestión Activa", layout="wide")

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
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val: return 0.0
        s = "".join(c for c in str(v) if c.isdigit() or c in [',', '.'])
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

# --- BARRA LATERAL: CALCULADORA DE CIERRE ---
st.sidebar.title("⌨️ Ingreso de Datos (23:00 hrs)")
st.sidebar.markdown("Usa esto para calcular los montos antes de pegarlos en el Excel.")

with st.sidebar.expander("🧮 Calculadora de Montos", expanded=True):
    fecha_ingreso = st.date_input("Fecha", datetime.now())
    precio_in = st.number_input("Precio de Cierre ($)", min_value=0.0, step=0.1)
    cantidad_in = st.number_input("Cantidad de Acciones", min_value=0, step=1)
    monto_result = precio_in * cantidad_in
    st.info(f"**Monto a ingresar:**\n${monto_result:,.0f}")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Navegación:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Terminal de Gestión Activa")
        
        # 1. Obtener IPSA Real
        ipsa = yf.download("^IPSA", period="2d", progress=False)['Close']
        ret_ipsa = (ipsa.iloc[-1] / ipsa.iloc[-2]) - 1 if len(ipsa) > 1 else 0.0

        # 2. Procesar Datos Históricos
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna()] # Columna C (Fecha)

        # --- CÁLCULO DEL VALOR TOTAL DE CARTERA ---
        # Creamos una columna temporal con la suma de todos los montos de las acciones
        def calcular_total_dia(fila):
            suma = 0
            # Recorremos las columnas de acciones (desde la H/7 de 3 en 3)
            for c in range(7, df_raw.shape[1], 3):
                p = limpiar_num(fila[c])
                q = limpiar_num(fila[c+1])
                suma += (p * q)
            return suma

        df_clean['Valor_Cartera'] = df_clean.apply(calcular_total_dia, axis=1)
        
        ultima = df_clean.iloc[-1]
        caja = limpiar_num(ultima[5])
        patrimonio_total = ultima['Valor_Cartera'] + caja

        # --- MÉTRICAS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patrimonio Total", f"${patrimonio_total:,.0f}")
        m2.metric("Benchmark IPSA", f"{ret_ipsa:+.2%}")
        m3.metric("Caja (Sobrante)", f"${caja:,.0f}")
        m4.metric("Fecha Hoy", datetime.now().strftime("%d/%m/%Y"))

        st.divider()

        # --- TABLA DE EVOLUCIÓN DE CARTERA ---
        st.subheader("📈 Evolución Diaria del Patrimonio")
        tabla_evolucion = df_clean[[2, 1, 'Valor_Cartera']].copy()
        tabla_evolucion.columns = ["Fecha", "Periodo", "Valor en Acciones ($)"]
        st.dataframe(tabla_evolucion, use_container_width=True, hide_index=True)

        st.divider()

        # --- DESPLEGABLES POR ACCIÓN ---
        st.subheader("📋 Detalle por Título")
        for col_idx in range(7, df_raw.shape[1], 3):
            nombre = str(df_raw.iloc[3, col_idx]).strip().upper()
            if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                h = df_clean[[2, 1, col_idx, col_idx + 1]].copy()
                h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                h["Precio"] = h["Precio"].apply(limpiar_num)
                h["Cantidad"] = h["Cantidad"].apply(limpiar_num)
                h["Monto ($)"] = h["Precio"] * h["Cantidad"]
                
                with st.expander(f"🔹 {nombre}"):
                    st.dataframe(h[h["Precio"]>0], use_container_width=True, hide_index=True)

    elif seleccion == "Omega":
        st.title("📉 Hoja Omega")
        df_omega = df_raw.iloc[2:87, 1:8].copy()
        df_omega.columns = df_omega.iloc[0]
        st.dataframe(df_omega.iloc[1:].replace("#VALUE!", "0"), use_container_width=True, hide_index=True)

    else:
        st.title(f"📄 Hoja: {seleccion}")
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
