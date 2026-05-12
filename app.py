import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Terminal Financiera Pro", layout="wide", page_icon="📈")

# --- INICIALIZACIÓN DE DATOS ---
if 'cartera' not in st.session_state:
    st.session_state.cartera = pd.DataFrame(columns=["Fecha_Compra", "Ticker", "Bolsa", "Precio_Compra", "Cantidad", "Monto_CLP"])
if 'favoritas' not in st.session_state:
    st.session_state.favoritas = pd.DataFrame(columns=["Fecha_Reg", "Ticker", "Precio_Ref"])

# --- FUNCIONES DE APOYO ---
def normalizar_ticker(t):
    t = t.strip().upper()
    if "." not in t and len(t) <= 6: return f"{t}.SN" # Auto-completa Chile
    return t

def obtener_precio_cierre_robusto(ticker, fecha_objetivo):
    """Busca el precio de cierre real, manejando festivos y errores de API"""
    try:
        t_obj = yf.Ticker(ticker)
        # Pedimos un margen de 7 días para asegurar que pillamos un día hábil
        inicio = fecha_objetivo - timedelta(days=5)
        fin = fecha_objetivo + timedelta(days=2)
        hist = t_obj.history(start=inicio, end=fin)
        
        if not hist.empty:
            # Buscamos el día exacto o el anterior más cercano
            if fecha_objetivo in hist.index.date:
                precio = hist.loc[str(fecha_objetivo), 'Close']
                if isinstance(precio, pd.Series): precio = precio.iloc[-1]
                return float(precio), t_obj.info.get('exchange', 'N/A')
            else:
                # Si es fin de semana, tomamos el último cierre disponible antes de la fecha
                precios_antes = hist[hist.index.date <= fecha_objetivo]
                if not precios_antes.empty:
                    return float(precios_antes['Close'].iloc[-1]), t_obj.info.get('exchange', 'N/A')
        return None, None
    except:
        return None, None

def calcular_indicadores(df, sma_p, ema_p, rsi_p):
    df['SMA'] = df['Close'].rolling(window=sma_p).mean()
    df['EMA'] = df['Close'].ewm(span=ema_p, adjust=False).mean()
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_p).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_p).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# --- INTERFAZ ---
st.title("🏛️ Terminal Financiera de Alta Precisión")
tabs = st.tabs(["🏠 Home", "💼 Mi Cartera", "⭐ Favoritas", "📊 Análisis y Gráficos"])

# ==========================================
# TAB 1: HOME (DASHBOARD DINÁMICO)
# ==========================================
with tabs[0]:
    st.header("Dashboard de Control")
    
    # 1. MÉTRICAS CLAVE
    usd_val = yf.Ticker("CLP=X").history(period="1d")['Close'].iloc[-1]
    total_val = st.session_state.cartera['Monto_CLP'].sum() if not st.session_state.cartera.empty else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Valor Total Cartera", f"${total_val:,.0f} CLP")
    m2.metric("Dólar Observado", f"${usd_val:,.2f} CLP")
    m3.metric("Activos Totales", len(st.session_state.cartera) + len(st.session_state.favoritas))

    st.divider()

    # 2. MONITOR EN VIVO Y COMERCIALIZACIÓN
    tickers_total = list(set(st.session_state.cartera['Ticker'].tolist() + st.session_state.favoritas['Ticker'].tolist()))
    
    if tickers_total:
        st.subheader("⚡ Monitor en Vivo y Nivel de Comercialización")
        cols_vivas = st.columns(min(len(tickers_total), 4))
        
        for idx, t in enumerate(tickers_total):
            try:
                stock_obj = yf.Ticker(t)
                h_viva = stock_obj.history(period="2d")
                if len(h_viva) >= 2:
                    p_hoy = h_viva['Close'].iloc[-1]
                    p_ayer = h_viva['Close'].iloc[-2]
                    vol_hoy = h_viva['Volume'].iloc[-1]
                    # Volumen promedio 10 días para el % de comercialización
                    vol_avg = stock_obj.history(period="10d")['Volume'].mean()
                    comercializacion = (vol_hoy / vol_avg) * 100
                    
                    var = ((p_hoy - p_ayer) / p_ayer) * 100
                    with cols_vivas[idx % 4]:
                        st.metric(t, f"{p_hoy:,.2f}", f"{var:.2f}%")
                        st.caption(f"Comercialización: {comercializacion:.1f}%")
                        if var > 0: st.write("🟢 SEÑAL: SUBIENDO")
                        else: st.write("🔴 SEÑAL: BAJANDO")
            except: continue

        # 3. GRÁFICO DE EVOLUCIÓN DE CARTERA (Simulado)
        st.divider()
        st.subheader("📈 Evolución del Valor de la Cartera (Últimos 30 días)")
        if not st.session_state.cartera.empty:
            with st.spinner("Calculando historial de cartera..."):
                hist_total = None
                for _, fila in st.session_state.cartera.iterrows():
                    h_ticker = yf.download(fila['Ticker'], period="1mo", progress=False)['Close']
                    monto_h = h_ticker * fila['Cantidad']
                    if fila['Bolsa'] != "SGO": monto_h *= usd_val
                    hist_total = monto_h if hist_total is None else hist_total + monto_h
                
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=hist_total.index, y=hist_total, mode='lines+markers', name='Cartera CLP', line=dict(color='#00FF00')))
                fig_line.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Agrega activos para ver el movimiento en vivo.")

# ==========================================
# TAB 2: MI CARTERA
# ==========================================
with tabs[1]:
    st.header("Gestión de Cartera")
    with st.expander("➕ Agregar Acción a Cartera", expanded=True):
        c1, c2, c3 = st.columns(3)
        t_new = c1.text_input("Ticker:").upper()
        f_new = c2.date_input("Fecha Adquisición:", datetime.now() - timedelta(days=1))
        cant_new = c3.number_input("Cantidad:", min_value=1)
        
        if st.button("Guardar en Cartera"):
            t_norm = normalizar_ticker(t_new)
            p, bolsa = obtener_precio_cierre_robusto(t_norm, f_new)
            if p:
                monto_clp = p * cant_new
                if bolsa != "SGO": monto_clp *= usd_val
                
                nuevo_registro = pd.DataFrame([{
                    "Fecha_Compra": f_new.strftime("%d/%m/%Y"), "Ticker": t_norm,
                    "Bolsa": bolsa, "Precio_Compra": p, "Cantidad": cant_new, "Monto_CLP": monto_clp
                }])
                st.session_state.cartera = pd.concat([st.session_state.cartera, nuevo_registro], ignore_index=True)
                st.success(f"Registrado: {t_norm} a ${p:,.2f}")
            else:
                st.error("No se encontró precio. Verifica el Ticker o la fecha.")

    st.dataframe(st.session_state.cartera, use_container_width=True)

# ==========================================
# TAB 3: FAVORITAS
# ==========================================
with tabs[2]:
    st.header("Watchlist: Acciones Favoritas")
    with st.expander("⭐ Añadir Ticker a Seguimiento"):
        cf1, cf2 = st.columns(2)
        t_fav = cf1.text_input("Ticker Favorito:").upper()
        f_fav = cf2.date_input("Fecha de Referencia:", datetime.now())
        
        if st.button("Añadir a Favoritas"):
            t_norm = normalizar_ticker(t_fav)
            p_f, _ = obtener_precio_cierre_robusto(t_norm, f_fav)
            if p_f:
                nuevo_fav = pd.DataFrame([{
                    "Fecha_Reg": f_fav.strftime("%d/%m/%Y"), "Ticker": t_norm, "Precio_Ref": p_f
                }])
                st.session_state.favoritas = pd.concat([st.session_state.favoritas, nuevo_fav], ignore_index=True)
                st.success(f"Añadida {t_norm} para seguimiento.")

    st.dataframe(st.session_state.favoritas, use_container_width=True)

# ==========================================
# TAB 4: ANÁLISIS TÉCNICO (VELAS Y SEÑALES)
# ==========================================
with tabs[3]:
    st.header("Análisis Técnico Pro")
    t_ana = st.selectbox("Ticker a analizar:", tickers_total if tickers_total else ["CHILE.SN"])
    
    col_f1, col_f2 = st.columns(2)
    f_start = col_f1.date_input("Analizar desde:", datetime.now() - timedelta(days=180))
    f_end = col_f2.date_input("Hasta:", datetime.now())
    
    with st.expander("⚙️ Ajustar Parámetros de Indicadores"):
        s1, s2, s3 = st.columns(3)
        sma_val = s1.slider("SMA", 5, 200, 50)
        ema_val = s2.slider("EMA", 5, 100, 20)
        rsi_val = s3.slider("RSI", 2, 30, 14)

    if st.button("🚀 Generar Gráficos de Velas"):
        data = yf.download(t_ana, start=f_start, end=f_end, progress=False)
        if not data.empty:
            data = calcular_indicadores(data, sma_val, ema_val, rsi_val)
            
            # FIGURA TRIPLE
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
            
            # VELAS
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Velas"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA'], name="SMA", line=dict(color='orange')), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA'], name="EMA", line=dict(color='cyan')), row=1, col=1)
            
            # RSI
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            
            # MACD
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name="MACD", line=dict(color='white')), row=3, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], name="Signal", line=dict(color='yellow')), row=3, col=1)
            
            fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # ANÁLISIS DE EXPERTO
            st.subheader("🕵️ Análisis de Indicadores")
            r_act = data['RSI'].iloc[-1]
            m_act = data['MACD'].iloc[-1]
            s_act = data['Signal'].iloc[-1]
            
            c_a, c_b = st.columns(2)
            with c_a:
                st.write(f"**RSI ({r_act:.1f}):**")
                if r_act > 70: st.error("SOBRECOMPRA: El activo está muy caro. Riesgo de caída.")
                elif r_act < 30: st.success("SOBREVENTA: El activo está barato. Oportunidad de rebote.")
                else: st.info("NEUTRAL: No hay fuerza de tendencia clara.")
            
            with c_b:
                st.write(f"**MACD:**")
                if m_act > s_act: st.success("CRUCE ALCISTA: Momentum positivo. Sugiere COMPRA.")
                else: st.error("CRUCE BAJISTA: Momentum negativo. Sugiere VENTA.")
