import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

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
        if pd.isna(v): return 0.0
        s_val = str(v).strip().replace(',', '')
        if s_val == "" or "#VALUE" in s_val.upper(): return 0.0
        return float(s_val)
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
seleccion = st.sidebar.radio("Hoja actual:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Terminal de Gestión Activa")
        
        # 1. Variación IPSA Live (Mercado en tiempo real)
        var_ipsa = 0.0
        try:
            ipsa_hist = yf.download("^IPSA", period="2d", progress=False)['Close']
            if len(ipsa_hist) > 1:
                var_ipsa = (ipsa_hist.iloc[-1] / ipsa_hist.iloc[-2]) - 1
        except: pass

        # 2. Procesar Datos del Excel
        df_clean = df_raw.iloc[5:].copy()
        df_clean[2] = pd.to_datetime(df_clean[2], dayfirst=True, errors='coerce')
        df_clean = df_clean.dropna(subset=[2])
        
        # --- MOTOR DE CÁLCULO ---
        def auditor_cartera(fila):
            suma_acciones = 0
            for c in range(7, len(fila), 3):
                if c + 1 < len(fila):
                    suma_acciones += (limpiar_num(fila[c]) * limpiar_num(fila[c+1]))
            # Suma F (5) y G (6)
            return suma_acciones + limpiar_num(fila[5]) + limpiar_num(fila[6])

        df_clean['Patrimonio_Calculado'] = df_clean.apply(auditor_cartera, axis=1)

        # 3. LÓGICA DE DESFASE: BUSCAR EL CIERRE DE AYER
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Filtramos: Solo registros ANTERIORES a hoy (ayer hacia atrás)
        df_cerrado = df_clean[df_clean[2] < hoy].sort_values(by=2)

        if not df_cerrado.empty:
            # El dato más reciente antes de hoy (ej. el 10 de mayo si hoy es 11)
            dato_ayer = df_cerrado.iloc[-1]
            val_cartera = dato_ayer['Patrimonio_Calculado']
            caja_f = limpiar_num(dato_ayer[5])
            fecha_cierre = dato_ayer[2].strftime('%d/%m/%Y')
            
            # --- MÉTRICAS SUPERIORES ---
            m1, m2, m3, m4 = st.columns(4)
            # Valor de Cartera (Cierre de ayer)
            m1.metric(f"Valor Cartera ({fecha_cierre})", f"${formato_excel(val_cartera)}")
            # IPSA en Vivo (Hoy)
            m2.metric("Variación IPSA (Live)", f"{var_ipsa:+.2%}")
            # Caja de ayer
            m3.metric("Caja Sobrante (F)", f"${formato_excel(caja_f)}")
            # Fecha de HOY
            m4.metric("Fecha de Hoy", hoy.strftime("%d/%m/%Y"))

            st.divider()

            # --- TABLA DE EVOLUCIÓN COMPLETA ---
            st.subheader("📈 Historial del Patrimonio")
            df_evol = df_clean.sort_values(by=2, ascending=False).copy()
            df_evol_display = df_evol[[2, 1, 'Patrimonio_Calculado']].copy()
            df_evol_display.columns = ["Fecha", "Periodo", "Total Cartera ($)"]
            df_evol_display["Fecha"] = df_evol_display["Fecha"].dt.strftime('%d/%m/%Y')
            df_evol_display["Total Cartera ($)"] = df_evol_display["Total Cartera ($)"].apply(formato_excel)
            st.dataframe(df_evol_display, use_container_width=True, hide_index=True)

            # --- DETALLE POR ACCIÓN ---
            st.subheader("📋 Detalle de Títulos (Precios y Cantidades)")
            for c in range(7, df_raw.shape[1], 3):
                if c + 1 < df_raw.shape[1]:
                    nombre = str(df_raw.iloc[3, c]).strip().upper()
                    if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                        h = df_clean[[2, 1, c, c+1]].copy()
                        h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                        # Cálculo de monto
                        h["Monto ($)"] = h["Precio"].apply(limpiar_num) * h["Cantidad"].apply(limpiar_num)
                        
                        # Formato visual
                        h_vista = h.sort_values(by="Fecha", ascending=False).copy()
                        h_vista["Fecha"] = h_vista["Fecha"].dt.strftime('%d/%m/%Y')
                        for col in ["Precio", "Cantidad", "Monto ($)"]:
                            h_vista[col] = h_vista[col].apply(formato_excel)

                        with st.expander(f"🔹 {nombre}"):
                            st.dataframe(h_vista[h["Precio"].apply(limpiar_num) > 0], use_container_width=True, hide_index=True)
        else:
            st.warning("No se encontraron registros de días anteriores a hoy en el Excel.")

    else:
        st.title(f"📄 Hoja: {seleccion}")
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error detectado: {e}")
