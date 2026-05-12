import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Terminal Financiera Pro", layout="wide", page_icon="📈")

# --- INICIALIZAR BASE DE DATOS LOCAL (SESSION STATE) ---
if 'cartera' not in st.session_state:
    # Creamos un DataFrame vacío con las columnas solicitadas
    st.session_state.cartera = pd.DataFrame(columns=[
        "Fecha_Compra", "Ticker", "Bolsa", "Moneda", "Precio_Compra", "Cantidad", "Monto_Invertido_CLP"
    ])

def formato_peso(valor):
    return f"${valor:,.0f}".replace(",", "v").replace(".", ",").replace("v", ".")

def formato_usd(valor):
    return f"US${valor:,.2f}"

# Función para calcular RSI y MACD puros en Pandas
def calcular_indicadores(df, sma_w, ema_w, rsi_w, macd_fast, macd_slow, macd_sig):
    # SMA y EMA
    df[f'SMA_{sma_w}'] = df['Close'].rolling(window=sma_w).mean()
    df[f'EMA_{ema_w}'] = df['Close'].ewm(span=ema_w, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/rsi_w, adjust=False).mean()
    loss = -delta.where(delta < 0, 0).ewm(alpha=1/rsi_w, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_f = df['Close'].ewm(span=macd_fast, adjust=False).mean()
    ema_s = df['Close'].ewm(span=macd_slow, adjust=False).mean()
    df['MACD'] = ema_f - ema_s
    df['Signal'] = df['MACD'].ewm(span=macd_sig, adjust=False).mean()
    df['Histograma'] = df['MACD'] - df['Signal']
    
    return df

# Extraer Dólar Observado (USD/CLP)
@st.cache_data(ttl=3600)
def obtener_usd_clp():
    try:
        usd = yf.Ticker("CLP=X").history(period="1d")
        return usd['Close'].iloc[-1]
    except:
        return 900.0 # Valor por defecto en caso de error

usd_clp_actual = obtener_usd_clp()

# --- INTERFAZ PRINCIPAL CON PESTAÑAS ---
st.title("🏛️ Terminal de Gestión Activa Independiente")
tab1, tab2, tab3 = st.tabs(["🏠 Home (Dashboard)", "💼 Mi Cartera", "📈 Análisis Técnico y Señales"])

# ==========================================
# PESTAÑA 1: HOME (DASHBOARD)
# ==========================================
with tab1:
    st.header("Resumen General del Portafolio")
    
    df_port = st.session_state.cartera
    total_invertido = df_port['Monto_Invertido_CLP'].sum() if not df_port.empty else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Valor Total Invertido (CLP)", formato_peso(total_invertido))
    col2.metric("Dólar Observado (USD/CLP)", formato_peso(usd_clp_actual))
    col3.metric("Activos en Cartera", len(df_port) if not df_port.empty else 0)
    
    st.divider()
    if not df_port.empty:
        st.subheader("Distribución de tu Cartera")
        # Gráfico de torta simple
        dist = df_port.groupby("Ticker")["Monto_Invertido_CLP"].sum().reset_index()
        fig_pie = go.Figure(data=[go.Pie(labels=dist['Ticker'], values=dist['Monto_Invertido_CLP'], hole=.4)])
        fig_pie.update_layout(height=400, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Tu cartera está vacía. Ve a la pestaña 'Mi Cartera' para agregar activos.")

# ==========================================
# PESTAÑA 2: MI CARTERA (Gestión)
# ==========================================
with tab2:
    st.header("Gestión de Mi Cartera")
    
    with st.expander("➕ Agregar Nueva Acción (Buscador y Calendario)", expanded=True):
        col_busq, col_fecha, col_calc = st.columns(3)
        
        with col_busq:
            ticker_input = st.text_input("1. Nemotécnico (ej: ANDINAB.SN, AAPL):").upper().strip()
            
        with col_fecha:
            fecha_adq = st.date_input("2. Fecha de Adquisición:", datetime.now())
            
        with col_calc:
            st.write("3. Consultar Mercado")
            btn_buscar = st.button("🔍 Buscar Precio Histórico")

        # Memoria temporal para el precio buscado
        if btn_buscar and ticker_input:
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                bolsa = info.get("exchange", "Desconocida")
                moneda = info.get("currency", "CLP")
                
                # Buscar datos históricos
                start_date = fecha_adq - timedelta(days=3) # Margen por si es fin de semana
                end_date = fecha_adq + timedelta(days=1)
                hist = stock.history(start=start_date, end=end_date)
                
                if not hist.empty:
                    # Tomar el precio más cercano a la fecha solicitada
                    precio_historico = hist['Close'].iloc[-1]
                    st.session_state['temp_ticker'] = ticker_input
                    st.session_state['temp_precio'] = precio_historico
                    st.session_state['temp_bolsa'] = bolsa
                    st.session_state['temp_moneda'] = moneda
                    st.success(f"¡Precio encontrado! Bolsa: {bolsa} | Moneda: {moneda}")
                else:
                    st.error("No hay datos para esa fecha. Quizás el mercado estaba cerrado.")
            except Exception as e:
                st.error("Error al buscar el Ticker. Asegúrate de usar .SN para Chile.")
                
        # Si ya buscamos el precio, mostramos la calculadora
        if 'temp_precio' in st.session_state and st.session_state['temp_ticker'] == ticker_input:
            st.divider()
            st.write(f"### Precio de {ticker_input} al {fecha_adq.strftime('%d/%m/%Y')}: **{st.session_state['temp_precio']:,.2f} {st.session_state['temp_moneda']}**")
            
            c_cant = st.number_input("4. Ingresa la Cantidad de Acciones compradas:", min_value=1, step=1)
            
            # Cálculo de monto en su moneda
            monto_original = st.session_state['temp_precio'] * c_cant
            
            # Conversión a CLP si es necesario
            monto_clp = monto_original
            if st.session_state['temp_moneda'] == "USD":
                monto_clp = monto_original * usd_clp_actual
                st.info(f"Monto Original: US${monto_original:,.2f} ➡️ **Total CLP: {formato_peso(monto_clp)}**")
            else:
                st.info(f"**Monto Total CLP: {formato_peso(monto_clp)}**")
                
            if st.button("💾 Guardar en Mi Cartera"):
                nueva_fila = {
                    "Fecha_Compra": fecha_adq.strftime('%d/%m/%Y'),
                    "Ticker": ticker_input,
                    "Bolsa": st.session_state['temp_bolsa'],
                    "Moneda": st.session_state['temp_moneda'],
                    "Precio_Compra": st.session_state['temp_precio'],
                    "Cantidad": c_cant,
                    "Monto_Invertido_CLP": monto_clp
                }
                st.session_state.cartera = pd.concat([st.session_state.cartera, pd.DataFrame([nueva_fila])], ignore_index=True)
                st.success("¡Acción agregada a tu cartera exitosamente!")
                # Limpiar memoria temporal
                del st.session_state['temp_precio']

    st.divider()
    st.subheader("📋 Tu Base de Datos: Valor Diario de Cartera")
    if not st.session_state.cartera.empty:
        df_mostrar = st.session_state.cartera.copy()
        df_mostrar['Precio_Compra'] = df_mostrar['Precio_Compra'].apply(lambda x: f"{x:,.2f}")
        df_mostrar['Monto_Invertido_CLP'] = df_mostrar['Monto_Invertido_CLP'].apply(formato_peso)
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Borrar toda la Cartera"):
            st.session_state.cartera = pd.DataFrame(columns=["Fecha_Compra", "Ticker", "Bolsa", "Moneda", "Precio_Compra", "Cantidad", "Monto_Invertido_CLP"])
            st.rerun()

# ==========================================
# PESTAÑA 3: ANÁLISIS TÉCNICO AVANZADO
# ==========================================
with tab3:
    st.header("Análisis Técnico y Señales (Gráficos Profesionales)")
    
    analisis_ticker = st.text_input("Ingresa el Ticker a analizar (ej: SQM-B.SN, MSFT):", "CHILE.SN").upper()
    
    with st.expander("⚙️ Configurar Parámetros de Indicadores", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        sma_p = c1.number_input("SMA (Simple)", 20, 200, 50)
        ema_p = c2.number_input("EMA (Exponencial)", 9, 100, 20)
        rsi_p = c3.number_input("Período RSI", 7, 30, 14)
        c4.write("MACD")
        macd_f = c4.number_input("Fast", 5, 20, 12)
        macd_s = c4.number_input("Slow", 20, 40, 26)
        macd_sig = c4.number_input("Signal", 5, 15, 9)

    if st.button("📊 Generar Análisis"):
        with st.spinner("Descargando historial y calculando indicadores..."):
            try:
                data = yf.download(analisis_ticker, period="1y", progress=False)
                if not data.empty:
                    # Calculamos todo
                    data = calcular_indicadores(data, sma_p, ema_p, rsi_p, macd_f, macd_s, macd_sig)
                    
                    # --- CREAR GRÁFICO PROFESIONAL CON PLOTLY ---
                    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                        vertical_spacing=0.05, row_heights=[0.5, 0.25, 0.25],
                                        subplot_titles=("Precio y Medias Móviles", "RSI (Fuerza Relativa)", "MACD"))
                    
                    # 1. Velas, SMA y EMA
                    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], 
                                                 low=data['Low'], close=data['Close'], name='Precio'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=data.index, y=data[f'SMA_{sma_p}'], line=dict(color='orange', width=1.5), name=f'SMA {sma_p}'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=data.index, y=data[f'EMA_{ema_p}'], line=dict(color='blue', width=1.5), name=f'EMA {ema_p}'), row=1, col=1)
                    
                    # 2. RSI
                    fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], line=dict(color='purple', width=1.5), name='RSI'), row=2, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                    
                    # 3. MACD
                    fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], line=dict(color='blue', width=1.5), name='MACD'), row=3, col=1)
                    fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], line=dict(color='orange', width=1.5), name='Signal'), row=3, col=1)
                    fig.add_trace(go.Bar(x=data.index, y=data['Histograma'], name='Hist', marker_color='gray'), row=3, col=1)
                    
                    fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)

                    # --- ANÁLISIS AUTOMATIZADO (TEXTO) ---
                    st.subheader(f"🧠 Análisis Automatizado para {analisis_ticker}")
                    
                    ultimo_precio = data['Close'].iloc[-1]
                    ultimo_rsi = data['RSI'].iloc[-1]
                    ultimo_macd = data['MACD'].iloc[-1]
                    ultima_signal = data['Signal'].iloc[-1]
                    sma_actual = data[f'SMA_{sma_p}'].iloc[-1]
                    
                    colA, colB = st.columns(2)
                    
                    with colA:
                        st.markdown("#### 📉 Resumen RSI")
                        if ultimo_rsi > 70:
                            st.error(f"El RSI está en **{ultimo_rsi:.2f}** (Sobrecompra). Históricamente, esto sugiere que el activo está caro y podría haber una corrección o caída de precio pronto. **Sugerencia:** Precaución al comprar, considerar tomar ganancias.")
                        elif ultimo_rsi < 30:
                            st.success(f"El RSI está en **{ultimo_rsi:.2f}** (Sobreventa). El activo ha sido muy castigado y podría estar barato. **Sugerencia:** Posible oportunidad de compra (rebote).")
                        else:
                            st.info(f"El RSI está en **{ultimo_rsi:.2f}** (Zona Neutral). No hay señales claras de agotamiento por parte de compradores ni vendedores.")
                            
                    with colB:
                        st.markdown("#### 📊 Resumen MACD y Tendencia")
                        tendencia = "Alcista 🐂" if ultimo_precio > sma_actual else "Bajista 🐻"
                        st.write(f"**Tendencia General (SMA):** {tendencia}")
                        
                        if ultimo_macd > ultima_signal:
                            st.success(f"El MACD ({ultimo_macd:.2f}) cruzó por ENCIMA de la señal ({ultima_signal:.2f}). Esto es una **Señal de Compra** o momentum positivo a corto plazo.")
                        else:
                            st.error(f"El MACD ({ultimo_macd:.2f}) está por DEBAJO de la señal ({ultima_signal:.2f}). Esto indica momentum negativo. **Señal de Venta** o espera.")

            except Exception as e:
                st.error(f"Error al procesar los gráficos: {e}")
