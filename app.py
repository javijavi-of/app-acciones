import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Financiera IPSA", layout="wide", initial_sidebar_state="expanded")

# Link Base y GIDs que me pasaste
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
    """Limpia el formato chileno (1.500,50) a número de Python"""
    try:
        if pd.isna(v) or str(v).strip() == "" or any(c.isalpha() for c in str(v)):
            return 0.0
        # Eliminar puntos de miles y cambiar coma por punto decimal
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
    # Leemos sin encabezado para procesar manualmente
    df_raw = pd.read_csv(url, header=None)

    if seleccion == "Seguimiento Cartera":
        st.title("🏛️ Seguimiento de Cartera vs IPSA")
        
        # 1. LIMPIEZA DE DATOS CARRETEROS
        # Los datos reales empiezan en la fila 6 (índice 5)
        # Filtramos filas que tengan algo parecido a una fecha en la columna C (índice 2)
        df_clean = df_raw.iloc[5:].copy()
        df_clean = df_clean[df_clean[2].notna() & df_clean[2].str.contains(r'\d')]
        
        if not df_clean.empty:
            # Buscamos la última fila que realmente tenga el valor de la cartera (Columna E / Índice 4)
            # Escaneamos de abajo hacia arriba para saltarnos celdas vacías al final del Excel
            ultima_valida = df_clean[df_clean[4].apply(limpiar_num) > 0].iloc[-1]
            
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
            st.info("Despliega cada acción para ver su historial 'carretero' y el cálculo de Monto Total.")
            
            # Columnas de acciones empiezan en H (7) y van de 3 en 3
            for col_idx in range(7, df_raw.shape[1], 3):
                nombre = str(df_raw.iloc[3, col_idx]).strip().upper() # Fila 4 del Excel
                
                if nombre and "NAN" not in nombre and "UNNAMED" not in nombre:
                    # Construir tabla: Fecha, Periodo, Precio, Cantidad
                    h = df_clean[[2, 1, col_idx, col_idx + 1]].copy()
                    h.columns = ["Fecha", "Periodo", "Precio Cierre", "Cantidad"]
                    
                    # Limpiar y Calcular
                    h["Precio Cierre"] = h["Precio Cierre"].apply(limpiar_num)
                    h["Cantidad"] = h["Cantidad"].apply(limpiar_num)
                    h["Total Cartera ($)"] = h["Precio Cierre"] * h["Cantidad"]
                    
                    # Solo mostrar filas donde el precio es mayor a 0 (días que se investigó)
                    h = h[h["Precio Cierre"] > 0]

                    with st.expander(f"🔹 {nombre}"):
                        st.dataframe(h, use_container_width=True, hide_index=True)
        else:
            st.warning("No se detectaron datos en la hoja de Seguimiento. Revisa la columna C del Excel.")

    else:
        # VISUALIZACIÓN PARA LAS OTRAS HOJAS
        st.title(f"📑 Hoja: {seleccion}")
        # Mostramos los datos desde la fila donde suelen empezar los encabezados (fila 3 o 4)
        st.dataframe(df_raw.iloc[2:], use_container_width=True)

except Exception as e:
    st.error(f"Error cargando la hoja '{seleccion}': {e}")
