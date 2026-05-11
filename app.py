import streamlit as st
import pandas as pd
import yfinance as yf

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="IPSA Terminal Pro", layout="wide")

# Link de tu Google Sheet
URL_GOOGLE = "https://docs.google.com/spreadsheets/d/1IJmrcL8f6l3qIDW7gw4CjLRBRiFkCFN4KCQeKaQbPic/edit?usp=sharing"
CSV_URL = URL_GOOGLE.replace("/edit?usp=sharing", "/export?format=csv")

st.title("🏛️ Panel de Control de Cartera - IPSA")
st.markdown("---")

try:
    # 1. CARGA DE DATOS
    # Leemos el CSV ignorando las primeras filas para llegar a los Tickers
    raw_df = pd.read_csv(CSV_URL, header=None)
    
    # Extraemos los Tickers (están en la fila 3 de tu Excel, que es índice 2 o 3 en Python)
    # Buscamos los nombres de las acciones que están cada 3 columnas
    tickers = []
    for col in range(7, raw_df.shape[1], 3): # Empieza en la columna H (7)
        t = raw_df.iloc[2, col] # Fila 3 del Excel
        if pd.notna(t):
            tickers.append((t, col))

    # Obtenemos la última fila con datos (el valor más reciente)
    last_row = raw_df.iloc[-1] 
    fecha_actual = last_row[2] # Columna C

    st.sidebar.success(f"📅 Última Actualización: {fecha_actual}")

    # 2. RESUMEN GENERAL (Métricas principales)
    monto_total_cartera = last_row[4] # Columna E (Valor Total)
    caja_sobrante = last_row[5] # Columna F (Sobrante)

    c1, c2, c3 = st.columns(3)
    c1.metric("Patrimonio Total", f"${float(monto_total_cartera):,.0f}")
    c2.metric("Caja Disponible", f"${float(caja_sobrante):,.0f}")
    c3.metric("Activos en Cartera", f"{len(tickers)} Acciones")

    st.markdown("### 🔍 Detalle por Título (Acción)")
    st.info("Haz clic en cada nombre para ver el desglose de Precio, Cantidad y Valor de la Posición.")

    # 3. PESTAÑAS DESPLEGABLES POR ACCIÓN
    # Aquí creamos el orden visual que pediste
    for t_name, col_index in tickers:
        with st.expander(f"📊 {t_name}"):
            # Extraemos los datos que marcaste en rojo y azul
            precio = last_row[col_index]      # Precio (Cuadro rojo/azul)
            cantidad = last_row[col_index + 1] # Cantidad
            valor_pos = last_row[col_index + 2] # Valor Posición
            
            col_a, col_b, col_c = st.columns(3)
            col_a.write(f"**Precio Actual:**\n ${float(precio):,.2f}")
            col_b.write(f"**Cantidad:**\n {int(float(cantidad)):,}")
            col_c.write(f"**Monto Invertido:**\n ${float(valor_pos):,.0f}")
            
            # Botón opcional para ver gráfico rápido en Yahoo Finance
            if st.button(f"Ver gráfico {t_name}", key=t_name):
                st.line_chart(yf.download(f"{t_name}.SN", period="1mo")['Close'])

except Exception as e:
    st.error(f"Error visual: {e}")
    st.info("Revisa que la estructura de columnas no haya cambiado en el Google Sheet.")
