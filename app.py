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
    """Convierte datos de Excel a números reales de Python"""
    try:
        if pd.isna(v): return 0.0
        s_val = str(v).strip().replace(',', '') # Quitamos comas de miles
        if s_val == "" or "#VALUE" in s_val.upper(): return 0.0
        return float(s_val)
    except:
        return 0.0

def formato_excel(valor):
    """Formato: 1,234,567.89 (Solo si es número)"""
    try:
        # Si por error llega un texto, intentamos convertirlo
        num = float(valor)
        return "{:,.2f}".format(num)
    except:
        return "0.00"

# --- BARRA LATERAL: HERRAMIENTAS ---
st.sidebar.title("🛠️ Control de Gestión")

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
seleccion = st.sidebar.radio("Hoja actual:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Terminal de Gestión Activa")
        
        # 1. Benchmark IPSA en Vivo
        var_ipsa = 0.0
        try:
            ipsa_ticker = yf.Ticker("^IPSA")
            ipsa_hist = ipsa_ticker.history(period="2d")
            if len(ipsa_hist) > 1:
                var_ipsa = (ipsa_hist['Close'].iloc[-1] / ipsa_hist['Close'].iloc[-2]) - 1
        except: pass

        # 2. Limpieza y filtrado de filas reales
        df_clean = df_raw.iloc[5:].copy()
        # Filtramos para quedarnos SOLO con filas que tengan una fecha real (evita filas vacías al final)
        df_clean = df_clean[df_clean[2].astype(str).str.contains(r'\d', na=False)]

        if not df_clean.empty:
            # --- MOTOR DE CÁLCULO ---
            def auditor_cartera(fila):
                # Sumamos (Precio * Cantidad) de cada acción (Empiezan en col H=7 de 3 en 3)
                sumatoria_acciones = 0
                num_cols = len(fila)
                for c in range(7, num_cols, 3):
                    if c + 1 < num_cols:
                        sumatoria_acciones += (limpiar_num(fila[c]) * limpiar_num(fila[c+1]))
                # Sumamos F (índice 5) y G (índice 6)
                return sumatoria_acciones + limpiar_num(fila[5]) + limpiar_num(fila[6])

            df_clean['Patrimonio_Calculado'] = df_clean.apply(auditor_cartera, axis=1)
            
            # Obtener ÚLTIMA fila con datos reales
            ultima = df_clean.iloc[-1]
            total_hoy = ultima['Patrimonio_Calculado']
            caja_f = limpiar_num(ultima[5])
            fecha_str = str(ultima[2])

            # --- MÉTRICAS SUPERIORES (LOS CUADROS ROJOS) ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Valor de Cartera", f"${formato_excel(total_hoy)}")
            m2.metric("IPSA (Live)", f"{var_ipsa:+.2%}")
            m3.metric("Caja Sobrante (F)", f"${formato_excel(caja_f)}")
            m4.metric("Fecha del Dato", fecha_str)

            st.divider()

            # --- TABLA DE EVOLUCIÓN ---
            st.subheader("📈 Evolución Diaria del Patrimonio")
            df_evol = df_clean[[2, 1, 'Patrimonio_Calculado']].copy()
            df_evol.columns = ["Fecha", "Periodo", "Total Cartera ($)"]
            df_evol["Total Cartera ($)"] = df_evol["Total Cartera ($)"].apply(formato_excel)
            st.dataframe(df_evol, use_container_width=True, hide_index=True)

            st.divider()

            # --- DETALLE POR ACCIÓN ---
            st.subheader("📋 Detalle de Títulos (Calculado)")
            max_c = df_raw.shape[1]
            for c in range(7, max_c, 3):
                if c + 1 < max_c:
                    nombre = str(df_raw.iloc[3, c]).strip().upper()
                    if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                        # Extraer y calcular
                        h = df_clean[[2, 1, c, c+1]].copy()
                        h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                        h["Monto ($)"] = h["Precio"].apply(limpiar_num) * h["Cantidad"].apply(limpiar_num)
                        
                        # Formatear la visualización
                        h_vista = h.copy()
                        for col in ["Precio", "Cantidad", "Monto ($)"]:
                            h_vista[col] = h_vista[col].apply(formato_excel)

                        with st.expander(f"🔹 {nombre}"):
                            st.dataframe(h_vista, use_container_width=True, hide_index=True)
        else:
            st.warning("No se detectaron datos en el rango de fechas del Seguimiento.")

    elif seleccion == "Omega":
        st.title("📉 Hoja Omega")
        df_omega = df_raw.iloc[2:87, 1:8].copy()
        df_omega.columns = df_omega.iloc[0]
        st.dataframe(df_omega.iloc[1:].replace("#VALUE!", "0"), use_container_width=True, hide_index=True)

    else:
        st.title(f"📄 Hoja: {seleccion}")
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error detectado en la aplicación: {e}")
