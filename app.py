import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import os
import requests
import xml.etree.ElementTree as ET

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Skaner Giełdowy PRO", layout="wide", initial_sidebar_state="expanded")

# --- WCZYTYWANIE BAZY ---
@st.cache_data
def wczytaj_baze(nazwa_pliku):
    baza = []
    if os.path.exists(nazwa_pliku):
        with open(nazwa_pliku, "r", encoding="utf-8") as f:
            for line in f:
                if " - " in line:
                    baza.append(line.strip())
    return baza

lista_gpw = wczytaj_baze("spolki.txt")
lista_wig = wczytaj_baze("spolkiwig.txt")
lista_nc = wczytaj_baze("spolkinc.txt")

# ==========================================
# MENU BOCZNE (SIDEBAR)
# ==========================================
st.sidebar.markdown("## ⚙️ Panel Sterowania")
st.sidebar.markdown("---")

narzedzie = st.sidebar.radio(
    "1️⃣ Wybierz moduł:", 
    ["🔍 Skaner (Pojedyncza spółka)", "📡 Radar Okazji (Wzrosty)", "📉 Radar Spadków (Snajper)", "📰 Wiadomości (GPW)"]
)

if narzedzie != "📰 Wiadomości (GPW)":
    st.sidebar.markdown("---")
    wybrany_rynek = st.sidebar.radio("2️⃣ Wybierz rynek:", ["SKANER GPW", "SKANER WIG", "SKANER NEW CONNECT"])
    
    if wybrany_rynek == "SKANER GPW": aktywna_lista = lista_gpw
    elif wybrany_rynek == "SKANER WIG": aktywna_lista = lista_wig
    else: aktywna_lista = lista_nc

    # DYNAMICZNE SUWAKI DLA RADARU SPADKÓW
    if narzedzie == "📉 Radar Spadków (Snajper)":
        st.sidebar.markdown("---")
        st.sidebar.markdown("🎯 **Ustawienia Snajpera:**")
        min_dni = st.sidebar.slider("Minimalna liczba dni spadku:", 1, 10, 3)
        min_krach = st.sidebar.slider("Minimalny krach od szczytu (%):", -50, -5, -10)

st.sidebar.markdown("---")
st.sidebar.info("💡 Użyj ikonki '>' w lewym górnym rogu na telefonie, by sterować menu.")

# ==========================================
# GŁÓWNY EKRAN APLIKACJI
# ==========================================

# ------------------------------------------
# NARZĘDZIE 1: SKANER
# ------------------------------------------
if narzedzie == "🔍 Skaner (Pojedyncza spółka)":
    st.title(f"📈 {wybrany_rynek} - Analiza")
    opcje_wyboru = ["--- Wpisz własny ticker (np. z USA) ---"] + aktywna_lista
    col_wyszukiwarka, col_okres, col_wykres = st.columns([2, 1, 1])
    with col_wyszukiwarka: wybor = st.selectbox("🔍 Wybierz spółkę:", opcje_wyboru)
    with col_okres: okres = st.selectbox("📅 Zakres danych:", ["1mo", "6mo", "1y", "2y", "5y", "max"], index=3)
    with col_wykres: typ_wykresu = st.selectbox("📊 Typ wykresu:", ["Świecowy", "Liniowy"])

    if wybor == "--- Wpisz własny ticker (np. z USA) ---":
        fraza = st.text_input("Wpisz ticker:", "").strip().upper()
        uruchom = st.button("Skanuj Własny Ticker")
        symbol = fraza + ".WA" if "." not in fraza and not fraza.startswith("^") else fraza
        pelna_nazwa = symbol
    else:
        czesc = wybor.split(" - ", 1)
        ticker, pelna_nazwa = czesc[0].strip(), czesc[1].strip()
        symbol, fraza = ticker + ".WA", ticker + ".WA"
        uruchom = st.button(f"Skanuj spółkę: {pelna_nazwa}")

    if uruchom and fraza:
        with st.spinner('Pobieram dane...'):
            stock = yf.Ticker(symbol)
            df = stock.history(period=okres)
            if not df.empty:
                ostatnia_cena = df['Close'].iloc[-1]
                df['SMA_20'] = df['Close'].rolling(window=20).mean()
                df['STD_20'] = df['Close'].rolling(window=20).std()
                df['Upper_BB'] = df['SMA_20'] + (df['STD_20'] * 2)
                df['Lower_BB'] = df['SMA_20'] - (df['STD_20'] * 2)
                df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
                df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
                df['MACD'] = df['EMA_12'] - df['EMA_26']
                df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                df['MACD_Hist'] = df['MACD'] - df['Signal']

                st.markdown(f"### 🏢 {pelna_nazwa} `({symbol})`")
                col1, col2, col3 = st.columns(3)
                col1.metric("Wycena", f"{ostatnia_cena:.2f}")
                col2.metric("Bollinger", "🟢 Wyprzedana" if ostatnia_cena <= df['Lower_BB'].iloc[-1] * 1.02 else "🟡 Neutralna")
                col3.metric("MACD", "🟢 Trend Wzrostowy" if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else "🔴 Trend Spadkowy")

                # PRZYWRÓCONE ETYKIETY I ZNACZNIKI
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3], subplot_titles=("Notowania (Wstęgi Bollingera)", "Wskaźnik MACD"))
                
                if typ_wykresu == "Świecowy": 
                    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Świece'), row=1, col=1)
                else: 
                    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Cena', line=dict(color='#1f77b4', width=2)), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], mode='lines', name='Górna Wstęga', line=dict(color='rgba(255,0,0,0.5)', width=1, dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], mode='lines', name='Dolna Wstęga', line=dict(color='rgba(0,128,0,0.5)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)
                
                kolory_macd = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Siła Trendu', marker_color=kolory_macd), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD', line=dict(color='blue')), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], mode='lines', name='Sygnał', line=dict(color='orange')), row=2, col=1)
                
                # PRZYWRÓCONY HOVERMODE (pionowa linia) I SUWAK
                fig.update_layout(height=750, margin=dict(l=20, r=20, t=40, b=20), hovermode='x unified', showlegend=False)
                fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
                fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.05, row=2, col=1) 
                
                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# ------------------------------------------
# NARZĘDZIE 2: RADAR WZROSTÓW
# ------------------------------------------
elif narzedzie == "📡 Radar Okazji (Wzrosty)":
    st.title(f"📡 {wybrany_rynek} - Szukanie Wzrostów")
    spolki_radar = [linia.split(" - ")[0].strip() + ".WA" for linia in aktywna_lista]
    if st.button("Uruchom Radar"):
        with st.spinner('Skanuję rynek...'):
            dane = yf.download(spolki_radar, period="6mo", progress=False)['Close']
            if isinstance(dane, pd.Series): dane = dane.to_frame(name=spolki_radar[0])
            okazje = []
            for ticker in spolki_radar:
                try:
                    hist = dane[ticker].dropna()
                    if len(hist) < 50: continue
                    cena = hist.iloc[-1]
                    ost_lower = hist.rolling(20).mean().iloc[-1] - (hist.rolling(20).std().iloc[-1] * 2)
                    macd = hist.ewm(span=12).mean() - hist.ewm(span=26).mean()
                    sig = macd.ewm(span=9).mean()
                    if cena <= ost_lower * 1.03 or (macd.iloc[-1] > sig.iloc[-1] and (macd.iloc[-1] - sig.iloc[-1]) > 0):
                        nazwa = next((l.split(" - ")[1].strip() for l in aktywna_lista if l.startswith(ticker.replace(".WA", ""))), ticker)
                        okazje.append({"Spółka": nazwa, "Symbol": ticker.replace(".WA", ""), "Cena": round(cena, 2)})
                except: continue
            if okazje: st.dataframe(pd.DataFrame(okazje), use_container_width=True)
            else: st.warning("Brak sygnałów.")

# ------------------------------------------
# NARZĘDZIE 3: RADAR SPADKÓW (SNAJPER)
# ------------------------------------------
elif narzedzie == "📉 Radar Spadków (Snajper)":
    st.title(f"📉 {wybrany_rynek} - Detektor Punktów Zwrotnych")
    
    with st.expander("📖 OPIS ANALIZ I WSKAŹNIKÓW (Jak czytać wyniki?)"):
        st.markdown("""
        ### **Na czym polega ta analiza?**
        Ten radar szuka spółek skrajnie wyprzedanych, które mogą lada moment odbić. Sprawdzamy:
        1.  **Dni spadku / wzrostu:** Pokazuje trend. Jeśli widzisz dni wzrostu > 0, oznacza to, że "nóż przestał spadać".
        2.  **Głębokość spadku:** Procentowa strata od lokalnego szczytu z 14 dni.
        3.  **RSI (Relative Strength Index):** Wskaźnik od 0 do 100. **Poniżej 30** to strefa paniki (często okazja).
        4.  **Skok Wolumenu:** Jeśli wolumen dziś jest wyższy od średniej, oznacza to, że do gry weszli "Grubsi Gracze".
        5.  **SMA200 (Średnia 200-sesyjna):** Najważniejsza linia trendu. Jeśli cena jest blisko niej, prawdopodobieństwo odbicia rośnie.
        """)

    spolki_radar = [linia.split(" - ")[0].strip() + ".WA" for linia in aktywna_lista]
    if st.button("Uruchom Snajpera"):
        with st.spinner('Analizuję historyczne dane (może to zająć chwilę)...'):
            dane_raw = yf.download(spolki_radar, period="1y", progress=False)
            ceny = dane_raw['Close']
            wolumeny = dane_raw['Volume']
            if isinstance(ceny, pd.Series): ceny = ceny.to_frame(name=spolki_radar[0])
            if isinstance(wolumeny, pd.Series): wolumeny = wolumeny.to_frame(name=spolki_radar[0])
            
            wyniki = []
            for ticker in spolki_radar:
                try:
                    hist = ceny[ticker].dropna()
                    vol_hist = wolumeny[ticker].dropna()
                    if len(hist) < 200: continue 
                    
                    dni_spadku, dni_odbicia = 0, 0
                    for i in range(1, 6):
                        if hist.iloc[-i] > hist.iloc[-(i+1)]: dni_odbicia += 1
                        else: break
                    start_sp = dni_odbicia + 1
                    for i in range(start_sp, len(hist)):
                        if hist.iloc[-i] < hist.iloc[-(i+1)]: dni_spadku += 1
                        else: break

                    delta = hist.diff()
                    up = delta.where(delta > 0, 0).rolling(14).mean()
                    down = -delta.where(delta < 0, 0).rolling(14).mean()
                    rsi = 100 - (100 / (1 + (up / down))).iloc[-1]
                    
                    vol_today = vol_hist.iloc[-1]
                    vol_avg = vol_hist.rolling(20).mean().iloc[-1]
                    skok_vol = "✅" if vol_today > vol_avg * 1.5 else "➖"
                    
                    sma200 = hist.rolling(200).mean().iloc[-1]
                    odl_sma200 = ((hist.iloc[-1] - sma200) / sma200) * 100
                    blisko_sma = "🎯 TAK" if abs(odl_sma200) < 3 else "➖"
                    
                    szczyt = hist.tail(14).max()
                    krach = ((hist.iloc[-1] - szczyt) / szczyt) * 100
                    
                    if dni_spadku >= min_dni or krach <= min_krach:
                        nazwa = next((l.split(" - ")[1].strip() for l in aktywna_lista if l.startswith(ticker.replace(".WA", ""))), ticker)
                        wyniki.append({
                            "Spółka": nazwa,
                            "Symbol": ticker.replace(".WA", ""),
                            "Dni ↓": dni_spadku,
                            "Dni ↑": f"🔥 {dni_odbicia}" if dni_odbicia > 0 else "0",
                            "Krach": f"{krach:.2f}%",
                            "RSI": round(rsi, 1),
                            "Skok Vol": skok_vol,
                            "Przy SMA200": blisko_sma,
                            "_sort": krach
                        })
                except: continue

            if wyniki:
                df = pd.DataFrame(wyniki).sort_values(by="_sort", ascending=True).drop(columns=['_sort']).reset_index(drop=True)
                st.error("🚨 Wykryto następujące okazje po przecenach:")
                st.dataframe(df, use_container_width=True)
            else: st.info("Żadna spółka nie spełnia rygorystycznych kryteriów.")

# ------------------------------------------
# NARZĘDZIE 4: WIADOMOŚCI
# ------------------------------------------
elif narzedzie == "📰 Wiadomości (GPW)":
    st.title("📰 Najświeższe komunikaty rynkowe")
    @st.cache_data(ttl=600) 
    def get_news():
        url = "https://news.google.com/rss/search?q=GPW+OR+Gielda+when:7d&hl=pl&gl=PL&ceid=PL:pl"
        try:
            r = requests.get(url, timeout=5)
            root = ET.fromstring(r.content)
            items = [{"title": i.find('title').text, "link": i.find('link').text, "date": i.find('pubDate').text} for i in root.findall('./channel/item')[:30]]
            return sorted(items, key=lambda x: pd.to_datetime(x['date']), reverse=True)
        except: return []
    for n in get_news():
        st.markdown(f"**[{n['title'].split(' - ')[0]}]({n['link']})**")
        st.caption(f"📅 {pd.to_datetime(n['date']).strftime('%Y-%m-%d %H:%M')}")
        st.divider()
