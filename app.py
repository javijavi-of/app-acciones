import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Terminal Financiera Pro", layout="wide", page_icon="🏦")

# --- INICIALIZACIÓN DE ESTADOS ---
if 'cartera' not in st.session_state:
    st.session_state.cartera = pd.DataFrame(columns=["Fecha_Compra", "Ticker", "Bolsa", "Precio_Compra", "Cantidad", "Monto_CLP"])
if 'favoritas' not in st.session_state:
    st.session_state.favoritas = pd.DataFrame(columns=["Fecha_Reg", "Ticker", "Bolsa", "Precio_Ref"])

# --- FUNCIONES DE AYUDA ---
def formato_clp(valor):
    return f"${valor:,.0f}".replace(",", ".")

def obtener_precio_cierre(ticker, fecha):
    try:
        stock = yf.Ticker(ticker)
        # Buscamos un rango pequeño alrededor de la fecha por si es festivo
        start = fecha
        end = fecha + timedelta(days=4)
        hist = stock.history(start=start, end=end)
        if not hist.empty:
            return hist['Close'].iloc[0], stock.info.get('exchange', 'N/A')
        return None, None
    except:
        return None, None

def calcular_indicadores(df, sma_p, ema_p, rsi_p, m_f, m_s, m_sig):
    df['SMA'] = df['Close'].rolling(window=sma_p).mean()
    df['EMA'] = df['Close'].ewm(span=ema_p, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_p).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_p).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    exp1 = df['Close'].ewm(span=m_f, adjust=False).mean()
    exp2 = df['Close'].ewm(span=m_s, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=m_sig, adjust=False).mean()
    return df

# --- INTERFAZ ---
st.title("🏛️ Terminal Financiera: Control Total")
tabs = st.tabs(["🏠 Home / Dashboard", "💼 Mi Cartera", "⭐ Acciones Favoritas", "📊 Análisis Técnico"])

# ==========================================
# TAB 1: HOME (DASHBOARD EN VIVO)
# ==========================================
with tabs[0]:
    st.header("Monitor de Mercado en Vivo")
    
    # Dólar y métricas
    usd_val = yf.Ticker("CLP=X").history(period="1d")['Close'].iloc[-1]
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Dólar Observado", f"${usd_val:,.2f} CLP")
    
    total_cartera = st.session_state.cartera['Monto_CLP'].sum() if not st.session_state.cartera.empty else 0
    col_m2.metric("Valor Total Cartera", formato_clp(total_cartera))

    st.divider()
    
    # Monitor de Acciones (Cartera + Favoritas)
    tickers_interes = list(set(st.session_state.cartera['Ticker'].tolist() + st.session_state.favoritas['Ticker'].tolist()))
    
    if tickers_interes:
        st.subheader("⚡ Seguimiento de Precios en Tiempo Real")
        # Descargamos precios actuales
        data_live = yf.download(tickers_interes, period="2d", progress=False)['Close']
        
        cols_live = st.columns(len(tickers_interes) if len(tickers_interes) < 5 else 4)
        for i, t in enumerate(tickers_interes):
            try:
                # Corregimos el acceso a los datos de yfinance
                if len(tickers_interes) == 1:
                    ultimo_p = data_live.iloc[-1]
                    prev_p = data_live.iloc[-2]
                else:
                    ultimo_p = data_live[t].iloc[-1]
                    prev_p = data_live[t].iloc[-2]
                
                var_pct = ((ultimo_p - prev_p) / prev_p) * 100
                flecha = "🔼" if var_pct > 0 else "🔽"
                
                with cols_live[i % 4]:
                    st.metric(f"{t}", f"{ultimo_p:,.2f}", f"{var_pct:.2f}% {flecha}")
            except:
                continue
    else:
        st.info("Agrega acciones en 'Mi Cartera' o 'Favoritas' para ver el monitor en vivo.")

# ==========================================
# TAB 2: MI CARTERA
# ==========================================
with tabs[1]:
    st.header("Gestión de Activos")
    with st.expander("➕ Registrar Compra (Histórica o Actual)"):
        c1, c2, c3 = st.columns(3)
        t_compra = c1.text_input("Ticker (ej: CHILE.SN, TSLA):").upper()
        f_compra = c2.date_input("Fecha de Compra:", datetime.now())
        cant = c3.number_input("Cantidad:", min_value=1)
        
        if st.button("Validar y Agregar a Cartera"):
            p_cierre, bolsa = obtener_precio_cierre(t_compra, f_compra)
            if p_cierre:
                monto = p_cierre * cant
                # Simulación conversión si es dólar
                if bolsa != "SGO": monto *= usd_val 
                
                nueva = pd.DataFrame([{
                    "Fecha_Compra": f_compra.strftime("%d/%m/%Y"),
                    "Ticker": t_compra, "Bolsa": bolsa,
                    "Precio_Compra": p_cierre, "Cantidad": cant, "Monto_CLP": monto
                }])
                st.session_state.cartera = pd.concat([st.session_state.cartera, nueva], ignore_index=True)
                st.success(f"Agregado: {t_compra} a {p_cierre:,.2f}")
            else:
                st.error("No se encontró precio para esa fecha.")

    st.dataframe(st.session_state.cartera, use_container_width=True)

# ==========================================
# TAB 3: ACCIONES FAVORITAS
# ==========================================
with tabs[2]:
    st.header("Lista de Seguimiento (Watchlist)")
    with st.form("fav_form"):
        f1, f2 = st.columns(2)
        t_fav = f1.text_input("Ticker Favorito:").upper()
        fecha_fav = f2.date_input("Fecha de Referencia:", datetime.now())
        if st.form_submit_button("Añadir a Favoritos"):
            p_fav, bolsa_f = obtener_precio_cierre(t_fav, fecha_fav)
            if p_fav:
                nueva_f = pd.DataFrame([{
                    "Fecha_Reg": fecha_fav.strftime("%d/%m/%Y"),
                    "Ticker": t_fav, "Bolsa": bolsa_f, "Precio_Ref": p_fav
                }])
                st.session_state.favoritas = pd.concat([st.session_state.favoritas, nueva_f], ignore_index=True)
            else:
                st.error("Error al obtener datos.")
    
    st.dataframe(st.session_state.favoritas, use_container_width=True)

# ==========================================
# TAB 4: ANÁLISIS TÉCNICO
# ==========================================
with tabs[3]:
    st.header("Centro de Análisis Avanzado")
    
    # Selector de acción desde nuestras listas o manual
    lista_opciones = list(set(["CHILE.SN"] + tickers_interes))
    t_analisis = st.selectbox("Selecciona acción para analizar:", lista_opciones)
    
    col_a1, col_a2 = st.columns(2)
    f_inicio = col_a1.date_input("Desde:", datetime.now() - timedelta(days=365))
    f_fin = col_a2.date_input("Hasta:", datetime.now())
    
    with st.expander("⚙️ Parámetros Técnicos"):
        pa1, pa2, pa3 = st.columns(3)
        s_p = pa1.slider("SMA Period", 5, 200, 50)
        e_p = pa2.slider("EMA Period", 5, 100, 20)
        r_p = pa3.slider("RSI Period", 2, 30, 14)

    if st.button("🚀 Ejecutar Análisis"):
        data = yf.download(t_analisis, start=f_inicio, end=f_fin, progress=False)
        
        if not data.empty:
            data = calcular_indicadores(data, s_p, e_p, r_p, 12, 26, 9)
            
            # FIGURA
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
            
            # 1. VELAS
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Velas"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA'], name="SMA", line=dict(color='blue')), row=1, col=1)
            
            # 2. RSI
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            
            # 3. MACD
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name="MACD"), row=3, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], name="Signal"), row=3, col=1)

            fig.update_layout(height=900, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # ANALISIS AUTOMÁTICO
            rsi_act = data['RSI'].iloc[-1]
            st.subheader("💡 Sugerencia del Sistema")
            if rsi_act > 70:
                st.warning(f"RSI en {rsi_act:.2f}: SOBRECOMPRA. El precio está muy alto, sugiere esperar o vender.")
            elif rsi_act < 30:
                st.success(f"RSI en {rsi_act:.2f}: SOBREVENTA. Oportunidad de compra detectada.")
            else:
                st.info(f"RSI en {rsi_act:.2f}: Tendencia neutral.")
        else:
            st.error("No se pudieron cargar datos para este periodo.")
