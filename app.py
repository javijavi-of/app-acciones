import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Financiera IPSA", layout="wide", initial_sidebar_state="expanded")

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
    """Limpia cualquier texto, signo o punto para dejar solo el número"""
    try:
        if pd.isna(v) or str(v).strip() == "": return 0.0
        # Quitamos todo lo que no sea número, coma o punto
        s = "".join(c for c in str(v) if c.isdigit() or c in [',', '.'])
        if not s: return 0.0
        # Manejo de formato chileno: quitar puntos de mil, cambiar coma a punto decimal
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except:
        return 0.0

# --- NAVEGACIÓN ---
st.sidebar.title("📊 Terminal Financiera")
seleccion = st.sidebar.radio("Ir a la hoja:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Seguimiento de Cartera vs IPSA")
        
        # Filtramos filas que tengan una fecha (Columna C / Índice 2)
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna() & df_clean[2].astype(str).str.contains(r'\d')]

        if not df_clean.empty:
            # --- PROCESAMIENTO DE ACCIONES Y CÁLCULO DE TOTAL ---
            st.subheader("📈 Evolución por Título")
            
            valor_total_cartera = 0
            caja_sobrante = limpiar_num(df_clean.iloc[-1][5]) # Columna F
            fecha_reporte = str(df_clean.iloc[-1][2])

            # Contenedor para los expanders
            principales = ["ANDINAB", "BCI", "BSANTANDER", "CENCOMALLS", "MALLPLAZA", 
                           "PARAUCO", "SALFACORP", "SQMB", "ECL", "ENELCHILE", 
                           "ILC", "OROBLANCO", "ENELGXCH", "NORTEGRAN", "SQMA"]
            
            tablas_acciones = []

            # Recorremos columnas de acciones (H en adelante, de 3 en 3)
            for col_idx in range(7, df_raw.shape[1], 3):
                nombre = str(df_raw.iloc[3, col_idx]).strip().upper()
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    # Crear historial
                    h = df_clean[[2, 1, col_idx, col_idx + 1]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio", "Cantidad"]
                    h["Precio"] = h["Precio"].apply(limpiar_num)
                    h["Cantidad"] = h["Cantidad"].apply(limpiar_num)
                    h["Total ($)"] = h["Precio"] * h["Cantidad"]
                    
                    # Sumamos al valor total de la cartera (solo el último dato registrado)
                    valor_total_cartera += h["Total ($)"].iloc[-1]
                    
                    h = h[h["Precio"] > 0] # Solo mostrar días con datos
                    tablas_acciones.append((nombre, h))

            # --- MÉTRICAS SUPERIORES ---
            # Ahora las calculamos nosotros para que no fallen
            m1, m2, m3 = st.columns(3)
            m1.metric("Patrimonio en Acciones", f"${valor_total_cartera:,.0f}")
            m2.metric("Caja (Sobrante)", f"${caja_sobrante:,.0f}")
            m3.metric("Última Fecha", fecha_reporte)

            st.divider()

            # Mostrar Expanders
            for nombre, tabla in tablas_acciones:
                with st.expander(f"🔹 {nombre}"):
                    st.dataframe(tabla, use_container_width=True, hide_index=True)
        else:
            st.warning("No se encontraron registros diarios. Asegúrate de poner la fecha en la Columna C.")

    else:
        st.title(f"📑 Hoja: {seleccion}")
        # Para las otras hojas, mostramos los datos desde donde empiezan los números
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error en la hoja '{seleccion}': {e}")
