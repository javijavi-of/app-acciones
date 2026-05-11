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
        s_val = str(v).strip().upper()
        if pd.isna(v) or s_val == "" or "#VALUE" in s_val or "FECHA" in s_val:
            return 0.0
        s = "".join(c for c in str(v) if c.isdigit() or c in [',', '.'])
        if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
        elif ',' in s: s = s.replace(',', '.')
        return float(s)
    except: return 0.0

# --- BARRA LATERAL: BUSCADOR MEJORADO ---
st.sidebar.title("🔍 Consultas y Navegación")
st.sidebar.subheader("Buscador de Precios")
t_input = st.sidebar.text_input("Nemotécnico (ej: BCI, SQMB, COPEC):", "").upper().strip()

if t_input:
    # Parche para tickers chilenos comunes
    t_ready = t_input.replace("-B", "B") # Yahoo a veces prefiere SQMB sobre SQM-B
    if not t_ready.endswith(".SN"): t_ready += ".SN"
    
    try:
        # Usamos history en lugar de fast_info por estabilidad
        ticker_obj = yf.Ticker(t_ready)
        data_hist = ticker_obj.history(period="1d")
        if not data_hist.empty:
            precio_cierre = data_hist['Close'].iloc[-1]
            st.sidebar.success(f"{t_input}: ${precio_cierre:,.2f}")
            st.sidebar.caption(f"Precio de cierre (Bolsa de Stgo)")
        else:
            st.sidebar.warning(f"No hay datos para {t_input} hoy.")
    except:
        st.sidebar.error("Error de conexión con Yahoo Finance.")

st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Ir a la hoja:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Performance de Cartera vs IPSA")
        
        # IPSA Real para Benchmarking
        try:
            ipsa_val = yf.download("^IPSA", period="2d", progress=False)['Close']
            ret_ipsa = (ipsa_val.iloc[-1] / ipsa_val.iloc[-2]) - 1
        except: ret_ipsa = 0.0

        # Limpiar datos del Excel (Fila 6 en adelante)
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna() & df_clean[2].astype(str).str.contains(r'\d')]

        if not df_clean.empty:
            ultima = df_clean.iloc[-1]
            
            # Cálculo de patrimonio dinámico (evita error 128)
            valor_activos_total = 0
            max_cols = df_raw.shape[1]
            
            # Procesamos solo donde haya nombres de acciones
            for c in range(7, max_cols, 3):
                if c + 1 >= max_cols: break # Seguridad para no salirse de la tabla
                
                nombre = str(df_raw.iloc[3, c]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    p = limpiar_num(ultima[c])
                    q = limpiar_num(ultima[c+1])
                    valor_activos_total += (p * q)

            caja = limpiar_num(ultima[5])
            patrimonio = valor_activos_total + caja
            
            # --- MÉTRICAS ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Patrimonio Total", f"${patrimonio:,.0f}")
            m2.metric("IPSA Hoy", f"{ret_ipsa:+.2%}")
            m3.metric("Caja (Sobrante)", f"${caja:,.0f}")
            m4.metric("Fecha Actual", datetime.now().strftime("%d/%m/%Y"))

            st.divider()
            
            # --- HISTORIALES ---
            for c in range(7, max_cols, 3):
                if c + 1 >= max_cols: break
                nombre = str(df_raw.iloc[3, c]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    h = df_clean[[2, 1, c, c+1]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                    h["Precio"] = h["Precio"].apply(limpiar_num)
                    h["Cantidad"] = h["Cantidad"].apply(limpiar_num)
                    h["Monto ($)"] = h["Precio"] * h["Cantidad"]
                    h = h[h["Precio"] > 0]

                    with st.expander(f"📊 {nombre}"):
                        st.dataframe(h, use_container_width=True, hide_index=True)

    elif seleccion == "Omega":
        st.title("📉 Hoja Omega: Análisis de Riesgo")
        # Filtro estricto B3 a H87
        df_omega = df_raw.iloc[2:87, 1:8].copy()
        df_omega.columns = df_omega.iloc[0]
        df_omega = df_omega.iloc[1:].replace("#VALUE!", "0").replace("#VALUE", "0")
        st.dataframe(df_omega, use_container_width=True, hide_index=True)

    else:
        st.title(f"📄 Hoja: {seleccion}")
        st.dataframe(df_raw.iloc[2:].replace("#VALUE!", "0"), use_container_width=True)

except Exception as e:
    st.error(f"Error en la terminal: {e}")
