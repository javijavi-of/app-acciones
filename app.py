import streamlit as st
import pandas as pd
import yfinance as yf

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="IPSA Terminal Pro", layout="wide")

URL_GOOGLE = "https://docs.google.com/spreadsheets/d/1IJmrcL8f6l3qIDW7gw4CjLRBRiFkCFN4KCQeKaQbPic/edit?usp=sharing"
CSV_URL = URL_GOOGLE.replace("/edit?usp=sharing", "/export?format=csv")

st.title("🏛️ Panel de Control: app-acciones")
st.markdown("---")

try:
    # 1. CARGA DE DATOS (Sin encabezado para manejarlo nosotros)
    raw_df = pd.read_csv(CSV_URL, header=None)
    
    # AJUSTE DE ÍNDICES SEGÚN TU CAPTURA:
    # Los tickers están en la fila index 3 (Fila 4 del Excel)
    fila_tickers = 3 
    
    tickers = []
    # Las acciones empiezan en la columna H (Índice 7) y van de 3 en 3
    for col in range(7, raw_df.shape[1], 3):
        t = raw_df.iloc[fila_tickers, col]
        if pd.notna(t) and str(t).strip() != "":
            tickers.append((str(t).strip(), col))

    # Buscamos la última fila que tenga una fecha (Columna C / Índice 2)
    # Filtramos filas vacías para encontrar el último dato real
    df_datos = raw_df[raw_df[2].notna()]
    last_row = df_datos.iloc[-1]
    fecha_actual = last_row[2]

    st.sidebar.success(f"📅 Datos al: {fecha_actual}")

    # 2. MÉTRICAS PRINCIPALES (Cuadros de arriba)
    # Columna E = Índice 4 (Valor Total), Columna F = Índice 5 (Sobrante)
    try:
        monto_total = float(str(last_row[4]).replace('.','').replace(',','.'))
        caja = float(str(last_row[5]).replace('.','').replace(',','.'))
    except:
        monto_total = 0
        caja = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Patrimonio Total", f"${monto_total:,.0f}")
    c2.metric("Caja Disponible (Sobrante)", f"${caja:,.0f}")
    c3.metric("Activos en Cartera", f"{len(tickers)} Acciones")

    st.markdown("### 🔍 Detalle Individual por Acción")
    st.info("Abre cada pestaña para ver el Precio y el Monto Invertido (Cuadros Rojo y Azul).")

    # 3. CREACIÓN DE PESTAÑAS (Expanders)
    for t_name, col_idx in tickers:
        # Usamos expanders para el orden visual que pediste
        with st.expander(f"📈 {t_name}"):
            # Extraemos los datos de las 3 columnas de esa acción
            try:
                # Precio (Cuadro Rojo)
                val_precio = float(str(last_row[col_idx]).replace('.','').replace(',','.'))
                # Cantidad (Siguiente columna)
                val_cant = float(str(last_row[col_idx + 1]).replace('.','').replace(',','.'))
                # Monto/Valor Posición (Cuadro Azul)
                val_monto = float(str(last_row[col_idx + 2]).replace('.','').replace(',','.'))
                
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Precio Actual", f"${val_precio:,.2f}")
                col_b.metric("Cantidad", f"{int(val_cant):,}")
                col_c.metric("Monto Invertido", f"${val_monto:,.0f}")
            except:
                st.warning(f"Datos no disponibles para {t_name} en la última fila.")

except Exception as e:
    st.error(f"Error de formato: {e}")
    st.info("Consejo: Verifica que no haya filas vacías al final de tu Google Sheet.")
