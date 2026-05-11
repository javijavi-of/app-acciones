import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Financiera IPSA", layout="wide", initial_sidebar_state="expanded")

# Link Base y GIDs oficiales de tu documento
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
    """Limpia el formato chileno (1.500,50) a número real"""
    try:
        if pd.isna(v) or str(v).strip() == "" or any(c.isalpha() for c in str(v) if c not in [',', '.']):
            return 0.0
        s = str(v).replace('.', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

# --- NAVEGACIÓN ---
st.sidebar.title("📊 Terminal Financiera")
st.sidebar.markdown("---")
seleccion = st.sidebar.radio("Ir a la hoja:", list(HOJAS.keys()))

try:
    url = BASE_URL + HOJAS[seleccion]
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Seguimiento de Cartera vs IPSA")
        
        # 1. LIMPIEZA DE DATOS (Fila 6 en adelante)
        df_clean = df_raw.iloc[5:].copy()
        
        # Filtro de seguridad: Solo filas que tengan algo en la columna C (Fecha)
        if df_raw.shape[1] > 2:
            df_clean = df_clean[df_clean[2].notna()]
        
        # VALIDACIÓN: ¿Hay datos reales?
        if not df_clean.empty:
            # Buscamos la última fila que tenga un valor numérico en la Columna E (índice 4)
            df_con_valor = df_clean[df_clean[4].apply(limpiar_num) > 0]
            
            if not df_con_valor.empty:
                ultima_valida = df_con_valor.iloc[-1]
                
                # --- MÉTRICAS SUPERIORES ---
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Valor Total Cartera", f"${limpiar_num(ultima_valida[4]):,.0f}")
                with m2:
                    st.metric("Caja (Sobrante)", f"${limpiar_num(ultima_valida[5]):,.0f}")
                with m3:
                    st.metric("Fecha Último Registro", str(ultima_valida[2]))

                st.divider()

                # --- HISTORIAL POR ACCIÓN ---
                st.subheader("📈 Evolución por Título")
                
                # Columnas de acciones desde índice 7 de 3 en 3
                for col_idx in range(7, df_raw.shape[1], 3):
                    nombre = str(df_raw.iloc[3, col_idx]).strip().upper()
                    
                    if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                        # Extraer historial
                        h = df_clean[[2, 1, col_idx, col_idx + 1]].copy()
                        h.columns = ["Fecha", "Periodo", "Precio Cierre", "Cantidad"]
                        
                        h["Precio Cierre"] = h["Precio Cierre"].apply(limpiar_num)
                        h["Cantidad"] = h["Cantidad"].apply(limpiar_num)
                        h["Monto Total ($)"] = h["Precio Cierre"] * h["Cantidad"]
                        
                        # Solo mostrar filas con actividad
                        h = h[h["Precio Cierre"] > 0]

                        if not h.empty:
                            with st.expander(f"🔹 {nombre}"):
                                st.dataframe(h, use_container_width=True, hide_index=True)
            else:
                st.warning("No se encontraron montos registrados en la columna E de tu Excel.")
        else:
            st.warning("La hoja de Seguimiento parece no tener datos debajo de los encabezados.")

    else:
        # VISUALIZACIÓN PARA LAS OTRAS HOJAS
        st.title(f"📑 Hoja: {seleccion}")
        # Muestra la tabla saltando los títulos decorativos de las primeras 2 filas
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error cargando la hoja '{seleccion}': {e}")
