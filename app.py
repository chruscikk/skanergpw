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
                col3.metric("MACD", "🟢 Kupuj" if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else "🔴 Sprzedaj")

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                                    row_heights=[0.7, 0.3], 
                                    subplot_titles=("Notowania i Wstęgi Bollingera", "Wskaźnik MACD"))
                
                if typ_wykresu == "Świecowy": 
                    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Cena (Świece)'), row=1, col=1)
                else: 
                    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Cena (Zamknięcie)', line=dict(color='#1f77b4', width=2)), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], mode='lines', name='Górna Wstęga', line=dict(color='rgba(255,0,0,0.4)', width=1, dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], mode='lines', name='Dolna Wstęga', line=dict(color='rgba(0,128,0,0.4)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)
                
                kolory_macd = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color=kolory_macd), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='Linia MACD', line=dict(color='blue')), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], mode='lines', name='Linia Sygnałowa', line=dict(color='orange')), row=2, col=1)
                
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
            try:
                dane = yf.download(spolki_radar, period="6mo", progress=False)['Close']
                if isinstance(dane, pd.Series): dane = dane.to_frame(name=spolki_radar[0])
                okazje = []
                for ticker in spolki_radar:
                    try: # <-- Otwarcie sprawdzania danej spółki
                        hist = dane[ticker].dropna()
                        if len(hist) < 50: continue
                        cena = hist.iloc[-1]
                        sma20 = hist.rolling(20).mean()
                        std20 = hist.rolling(20).std()
                        low_bb = (sma20 - (std20 * 2)).iloc[-1]
                        macd = hist.ewm(span=12).mean() - hist.ewm(span=26).mean()
                        sig = macd.ewm(span=9).mean()
                        if cena <= low_bb * 1.03 or (macd.iloc[-1] > sig.iloc[-1] and (macd.iloc[-1] - sig.iloc[-1]) > 0):
                            nazwa = next((l.split(" - ")[1].strip() for l in aktywna_lista if l.startswith(ticker.replace(".WA", ""))), ticker)
                            okazje.append({"Spółka": nazwa, "Symbol": ticker.replace(".WA", ""), "Cena": round(cena, 2)})
                    except: 
                        continue # <--- BRAKOWAŁO TEGO ZAMKNIĘCIA!

                if okazje: st.dataframe(pd.DataFrame(okazje), use_container_width=True)
                else: st.warning("Brak sygnałów.")
            except: st.error("Błąd podczas pobierania danych radarowych.")

# ------------------------------------------
# NARZĘDZIE 3: RADAR SPADKÓW (SNAJPER)
# ------------------------------------------
elif narzedzie == "📉 Radar Spadków (Snajper)":
    st.title(f"📉 {wybrany_rynek} - Detektor Punktów Zwrotnych")
    with st.expander("📖 OPIS ANALIZ (Jak czytać wyniki?)"):
        st.markdown("""
        1. **Dni ↓ / ↑**: Licznik dni nieprzerwanych spadków oraz trwającego odbicia.
        2. **Krach**: Procentowa strata od lokalnego szczytu (ostatnie 14 dni).
        3. **RSI**: Poniżej 30 oznacza skrajne wyprzedanie (panika).
        4. **Skok Vol**: ✅ oznacza, że wolumen jest o 50% wyższy niż średnia (duzi gracze kupują).
        5. **Przy SMA200**: 🎯 oznacza, że cena jest blisko głównej średniej 200-sesyjnej.
        """)

    spolki_radar = [linia.split(" - ")[0].strip() + ".WA" for linia in aktywna_lista]
    if st.button("Uruchom Snajpera"):
        with st.spinner('Analizuję historię rynkową...'):
            try:
                dane_raw = yf.download(spolki_radar, period="1y", progress=False)
                ceny = dane_raw['Close']
                vols = dane_raw['Volume']
                if isinstance(ceny, pd.Series): ceny = ceny.to_frame(name=spolki_radar[0])
                if isinstance(vols, pd.Series): vols = vols.to_frame(name=spolki_radar[0])
                
                wyniki = []
                for ticker in spolki_radar:
                    try:
                        hist = ceny[ticker].dropna()
                        vh = vols[ticker].dropna()
                        if len(hist) < 200: continue 
                        
                        # Licznik trendu
                        up, down = 0, 0
                        for i in range(1, 6):
                            if hist.iloc[-i] > hist.iloc[-(i+1)]: up += 1
                            else: break
                        st_sp = up + 1
                        for i in range(st_sp, len(hist)):
                            if hist.iloc[-i] < hist.iloc[-(i+1)]: down += 1
                            else: break

                        # RSI
                        delta = hist.diff()
                        gain = delta.where(delta > 0, 0).rolling(14).mean()
                        loss = -delta.where(delta < 0, 0).rolling(14).mean()
                        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
                        
                        # Wolumen i SMA
                        vol_ok = "✅" if vh.iloc[-1] > vh.rolling(20).mean().iloc[-1] * 1.5 else "➖"
                        sma200 = hist.rolling(200).mean().iloc[-1]
                        sma_ok = "🎯 TAK" if abs(((hist.iloc[-1] - sma200)/sma200)*100) < 3 else "➖"
                        
                        max14 = hist.tail(14).max()
                        krach = ((hist.iloc[-1] - max14) / max14) * 100
                        
                        if down >= min_dni or krach <= min_krach:
                            nazwa = next((l.split(" - ")[1].strip() for l in aktywna_lista if l.startswith(ticker.replace(".WA", ""))), ticker)
                            wyniki.append({"Spółka": nazwa, "Symbol": ticker.replace(".WA", ""), "Dni ↓": down, "Dni ↑": f"🔥 {up}" if up > 0 else "0", "Krach": f"{krach:.2f}%", "RSI": round(rsi, 1), "Skok Vol": vol_ok, "Przy SMA200": sma_ok, "_s": krach})
                    except: continue

                if wyniki:
                    df = pd.DataFrame(wyniki).sort_values("_s").drop(columns=["_s"]).reset_index(drop=True)
                    st.error("🚨 Wykryte okazje:")
                    st.dataframe(df, use_container_width=True)
                else: st.info("Brak spółek spełniających kryteria.")
            except: st.error("Błąd pobierania danych.")

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
