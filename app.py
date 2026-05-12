import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Terminal Financiera Pro", layout="wide", page_icon="🏦")

# --- INICIALIZACIÓN DE BASES DE DATOS LOCALES ---
if 'cartera' not in st.session_state:
    st.session_state.cartera = pd.DataFrame(columns=["Fecha_Compra", "Ticker", "Bolsa", "Precio_Ref", "Cantidad", "Monto_Total_CLP"])
if 'favoritas' not in st.session_state:
    st.session_state.favoritas = pd.DataFrame(columns=["Fecha_Ref", "Ticker", "Bolsa", "Precio_Ref"])

# --- FUNCIONES DE APOYO Y CÁLCULO ---
def normalizar_ticker(t):
    """Agrega .SN automáticamente si el usuario lo olvida"""
    t = t.strip().upper()
    if "." not in t: 
        return f"{t}.SN"
    return t

def obtener_datos_exactos(ticker, fecha_busqueda):
    """Busca el CIERRE REAL (no ajustado) manejando fines de semana y festivos"""
    try:
        obj = yf.Ticker(ticker)
        inicio = fecha_busqueda - timedelta(days=5)
        fin = fecha_busqueda + timedelta(days=2)
        
        # auto_adjust=False ES LA CLAVE PARA QUE NO USE EL CIERRE AJUSTADO
        hist = obj.history(start=inicio, end=fin, auto_adjust=False)
        
        if not hist.empty:
            # Si el día exacto está, lo tomamos. Si no, tomamos el cierre anterior más cercano
            if str(fecha_busqueda) in hist.index.astype(str):
                precio_real = hist.loc[str(fecha_busqueda), 'Close']
            else:
                hist_filtrado = hist[hist.index.date <= fecha_busqueda]
                if not hist_filtrado.empty:
                    precio_real = hist_filtrado['Close'].iloc[-1]
                else:
                    return None, None
            
            # Si pandas devuelve una Serie por error, tomamos el último valor
            if isinstance(precio_real, pd.Series): 
                precio_real = precio_real.iloc[-1]
                
            exchange = obj.info.get('exchange', 'Desconocida')
            return float(precio_real), exchange
        return None, None
    except:
        return None, None

def calcular_indicadores(df, sma_p, ema_p, rsi_p):
    if df.empty: return df
    df['SMA'] = df['Close'].rolling(window=sma_p).mean()
    df['EMA'] = df['Close'].ewm(span=ema_p, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_p).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_p).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    return df

# --- INTERFAZ PRINCIPAL ---
st.title("🏛️ Terminal Financiera: Control Activo")
tabs = st.tabs(["🏠 Dashboard en Vivo", "💼 Mi Cartera (Gestión)", "⭐ Acciones Favoritas", "📊 Análisis Técnico"])

# ==========================================
# TAB 1: HOME (DASHBOARD)
# ==========================================
with tabs[0]:
    st.header("Monitor de Mercado y Resumen")
    
    try:
        usd_val = yf.Ticker("CLP=X").history(period="1d")['Close'].iloc[-1]
    except:
        usd_val = 900.0 # Respaldo si falla
        
    total_val = st.session_state.cartera['Monto_Total_CLP'].sum() if not st.session_state.cartera.empty else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Valor Total de la Cartera", f"${total_val:,.0f} CLP")
    m2.metric("Dólar Observado (CLP=X)", f"${usd_val:,.2f} CLP")
    m3.metric("Activos Monitoreados", len(st.session_state.cartera) + len(st.session_state.favoritas))

    st.divider()

    tickers_total = list(set(st.session_state.cartera['Ticker'].tolist() + st.session_state.favoritas['Ticker'].tolist()))
    
    if tickers_total:
        st.subheader("⚡ Monitor en Vivo (Variación y Comercialización)")
        cols_vivas = st.columns(4)
        
        for idx, t in enumerate(tickers_total):
            try:
                stock_obj = yf.Ticker(t)
                h_viva = stock_obj.history(period="15d", auto_adjust=False)
                
                if len(h_viva) >= 2:
                    p_hoy = h_viva['Close'].iloc[-1]
                    p_ayer = h_viva['Close'].iloc[-2]
                    vol_hoy = h_viva['Volume'].iloc[-1]
                    vol_avg = h_viva['Volume'].mean()
                    
                    comercializacion = (vol_hoy / vol_avg) * 100 if vol_avg > 0 else 0
                    var = ((p_hoy - p_ayer) / p_ayer) * 100
                    flecha = "🟢 Sube" if var >= 0 else "🔴 Baja"
                    
                    with cols_vivas[idx % 4]:
                        st.metric(t, f"${p_hoy:,.2f}", f"{var:+.2f}%")
                        st.caption(f"Comercialización: {comercializacion:.0f}% | Señal: {flecha}")
            except:
                pass
    else:
        st.info("Agrega activos a tu Cartera o Favoritas para activar el monitor en vivo.")

# ==========================================
# TAB 2: MI CARTERA (SISTEMA DE 2 PASOS)
# ==========================================
with tabs[1]:
    st.header("Gestor de Portafolio")
    
    with st.expander("➕ Añadir Acción a la Cartera (Paso a Paso)", expanded=True):
        st.markdown("### Paso 1: Validar Precio de Referencia")
        c1, c2 = st.columns(2)
        t_input = c1.text_input("Ticker (ej: ANDINA-B, CHILE):").upper()
        f_input = c2.date_input("Fecha de Adquisición o Referencia:", datetime.now())
        
        if st.button("🔍 1. Obtener Precio Real de Mercado"):
            t_norm = normalizar_ticker(t_input)
            precio_api, bolsa_api = obtener_datos_exactos(t_norm, f_input)
            
            if precio_api is not None:
                st.session_state['temp_ticker'] = t_norm
                st.session_state['temp_precio'] = precio_api
                st.session_state['temp_bolsa'] = bolsa_api
                st.session_state['temp_fecha'] = f_input
                st.success(f"✅ Precio de Cierre Real localizado para {t_norm}: ${precio_api:,.2f}")
            else:
                st.error("❌ No se encontraron datos para esa fecha. Intenta con un día hábil.")

        # Si el Paso 1 fue exitoso, mostramos el Paso 2
        if 'temp_precio' in st.session_state:
            st.divider()
            st.markdown("### Paso 2: Configurar y Calcular")
            c3, c4 = st.columns(2)
            # Permite al usuario editar el precio si lo desea
            p_final = c3.number_input("Precio por Acción ($):", value=float(st.session_state['temp_precio']), step=0.1)
            cantidad = c4.number_input("Cantidad de Acciones:", min_value=1, step=1)
            
            monto_calculado = p_final * cantidad
            st.info(f"**Monto Total Final:** ${monto_calculado:,.2f}")
            
            if st.button("💾 2. Confirmar y Añadir a Mi Cartera"):
                nuevo_reg = pd.DataFrame([{
                    "Fecha_Compra": st.session_state['temp_fecha'].strftime("%d/%m/%Y"),
                    "Ticker": st.session_state['temp_ticker'],
                    "Bolsa": st.session_state['temp_bolsa'],
                    "Precio_Ref": p_final,
                    "Cantidad": cantidad,
                    "Monto_Total_CLP": monto_calculado
                }])
                st.session_state.cartera = pd.concat([st.session_state.cartera, nuevo_reg], ignore_index=True)
                st.success("¡Acción guardada en tu cartera con éxito!")
                del st.session_state['temp_precio'] # Limpiamos la memoria temporal
                st.rerun()

    st.subheader("📋 Mi Cartera Actual")
    if not st.session_state.cartera.empty:
        df_mostrar = st.session_state.cartera.copy()
        df_mostrar['Precio_Ref'] = df_mostrar['Precio_Ref'].apply(lambda x: f"${x:,.2f}")
        df_mostrar['Monto_Total_CLP'] = df_mostrar['Monto_Total_CLP'].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
    else:
        st.write("Tu cartera está vacía.")

# ==========================================
# TAB 3: ACCIONES FAVORITAS (WATCHLIST)
# ==========================================
with tabs[2]:
    st.header("Lista de Observación (Favoritas)")
    
    with st.expander("⭐ Añadir Ticker a Seguimiento"):
        cf1, cf2 = st.columns(2)
        t_fav = cf1.text_input("Ticker Favorito (ej: SQM-B):").upper()
        f_fav = cf2.date_input("Fecha de Referencia (Favoritos):", datetime.now())
        
        if st.button("Añadir a Favoritas"):
            t_norm = normalizar_ticker(t_fav)
            p_f, bolsa_f = obtener_datos_exactos(t_norm, f_fav)
            if p_f is not None:
                nuevo_fav = pd.DataFrame([{
                    "Fecha_Ref": f_fav.strftime("%d/%m/%Y"),
                    "Ticker": t_norm,
                    "Bolsa": bolsa_f,
                    "Precio_Ref": p_f
                }])
                st.session_state.favoritas = pd.concat([st.session_state.favoritas, nuevo_fav], ignore_index=True)
                st.success(f"{t_norm} añadida a vigilancia a ${p_f:,.2f}")
            else:
                st.error("❌ Error al obtener datos para ese día.")

    if not st.session_state.favoritas.empty:
        df_fav = st.session_state.favoritas.copy()
        df_fav['Precio_Ref'] = df_fav['Precio_Ref'].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df_fav, use_container_width=True, hide_index=True)

# ==========================================
# TAB 4: ANÁLISIS TÉCNICO Y GRÁFICOS
# ==========================================
with tabs[3]:
    st.header("Análisis Técnico y Velas Japonesas")
    
    opciones_grafico = list(set(["CHILE.SN"] + tickers_total))
    t_ana = st.selectbox("Selecciona acción para graficar:", opciones_grafico)
    
    col_a1, col_a2 = st.columns(2)
    f_start = col_a1.date_input("Desde:", datetime.now() - timedelta(days=180))
    f_end = col_a2.date_input("Hasta:", datetime.now())
    
    with st.expander("⚙️ Parámetros de Análisis (SMA, EMA, RSI)"):
        pa1, pa2, pa3 = st.columns(3)
        sma_val = pa1.slider("Período SMA", 5, 200, 50)
        ema_val = pa2.slider("Período EMA", 5, 100, 20)
        rsi_val = pa3.slider("Período RSI", 2, 30, 14)

    if st.button("🚀 Ejecutar Análisis Gráfico"):
        # Usamos auto_adjust=False para ver los precios reales en el gráfico
        data = yf.download(t_ana, start=f_start, end=f_end, auto_adjust=False, progress=False)
        
        if not data.empty:
            data = calcular_indicadores(data, sma_val, ema_val, rsi_val)
            
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
            
            # 1. Velas, SMA y EMA
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Precio"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['SMA'], name=f"SMA {sma_val}", line=dict(color='orange', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['EMA'], name=f"EMA {ema_val}", line=dict(color='cyan', width=1.5)), row=1, col=1)
            
            # 2. RSI
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            
            # 3. MACD
            fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name="MACD", line=dict(color='white')), row=3, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['Signal'], name="Signal", line=dict(color='yellow')), row=3, col=1)
            fig.add_trace(go.Bar(x=data.index, y=data['Hist'], name="Histograma", marker_color='gray'), row=3, col=1)

            fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Análisis Automatizado
            st.subheader("💡 Lectura del Sistema")
            r_act = float(data['RSI'].iloc[-1])
            m_act = float(data['MACD'].iloc[-1])
            s_act = float(data['Signal'].iloc[-1])
            
            c_a, c_b = st.columns(2)
            with c_a:
                st.write(f"**Análisis RSI ({r_act:.1f}):**")
                if r_act > 70: st.error("SOBRECOMPRA: Posible corrección bajista inminente.")
                elif r_act < 30: st.success("SOBREVENTA: Posible rebote o momento de entrada.")
                else: st.info("NEUTRAL: El activo está en zona de equilibrio.")
            
            with c_b:
                st.write(f"**Análisis MACD:**")
                if m_act > s_act: st.success(f"TENDENCIA ALCISTA (MACD {m_act:.2f} > Señal {s_act:.2f})")
                else: st.error(f"TENDENCIA BAJISTA (MACD {m_act:.2f} < Señal {s_act:.2f})")
        else:
            st.error("No hay datos históricos para construir el gráfico en este periodo.")
