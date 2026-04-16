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

st.set_page_config(page_title="Skaner GPW PRO", layout="wide")
st.title("📈 Profesjonalny Skaner Giełdowy GPW")

# --- WCZYTYWANIE BAZY Z PLIKU TXT ---
@st.cache_data
def wczytaj_spolki():
    baza = []
    if os.path.exists("spolki.txt"):
        with open("spolki.txt", "r", encoding="utf-8") as f:
            for line in f:
                if " - " in line:
                    baza.append(line.strip())
    return baza

lista_spolek = wczytaj_spolki()
opcje_wyboru = ["--- Wpisz własny ticker (np. z USA lub ETF) ---"] + lista_spolek

# Zakładki
tab1, tab2, tab3 = st.tabs(["🔍 Analiza Spółki (Skaner PRO)", "📡 Radar Okazji (Cały Rynek)", "📰 Wiadomości (GPW)"])

# ==========================================
# ZAKŁADKA 1 i 2 (Bez zmian w logice wykresów)
# ==========================================
# ... (tutaj znajduje się kod z Twojej poprzedniej wersji dla Tab 1 i Tab 2) ...
# Poniżej znajduje się tylko zaktualizowana Sekcja Wiadomości, podmień ją w swoim pliku.

with tab1:
    col_wyszukiwarka, col_okres, col_wykres = st.columns([2, 1, 1])
    with col_wyszukiwarka: wybor = st.selectbox("🔍 Wybierz spółkę z listy:", opcje_wyboru)
    with col_okres: okres = st.selectbox("📅 Zakres danych:", ["1mo", "6mo", "1y", "2y", "5y", "max"], index=3)
    with col_wykres: typ_wykresu = st.selectbox("📊 Typ wykresu:", ["Świecowy", "Liniowy"])

    if wybor == "--- Wpisz własny ticker (np. z USA lub ETF) ---":
        fraza = st.text_input("Wpisz skrót giełdowy:", "").strip().upper()
        uruchom = st.button("Skanuj Własny Ticker")
        if uruchom and fraza:
            symbol = fraza + ".WA" if "." not in fraza and not fraza.startswith("^") else fraza
            pelna_nazwa = symbol
    else:
        czesc = wybor.split(" - ", 1)
        ticker, pelna_nazwa = czesc[0].strip(), czesc[1].strip()
        symbol, fraza = ticker + ".WA", ticker + ".WA"
        uruchom = st.button(f"Skanuj spółkę: {pelna_nazwa}")

    if uruchom and fraza:
        with st.spinner(f'Pobieram dane dla {symbol}...'):
            stock = yf.Ticker(symbol)
            df = stock.history(period=okres)
            if not df.empty:
                # ... (Logika obliczeń SMA, BB, MACD oraz wykresu Plotly - jak w poprzedniej wersji) ...
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
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                if typ_wykresu == "Świecowy":
                    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Świece'), row=1, col=1)
                else:
                    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Cena'), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], mode='lines', name='Górna', line=dict(width=1, dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], mode='lines', name='Dolna', line=dict(width=1, dash='dot'), fill='tonexty'), row=1, col=1)
                
                kolory_macd = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=kolory_macd), row=2, col=1)
                fig.update_layout(height=750, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

with tab2:
    # ... (Kod Radaru Okazji pozostaje bez zmian) ...
    st.markdown("### 📡 Radar Okazji (Jak w poprzedniej wersji)")
    if st.button("Uruchom Radar"):
        st.write("Skanowanie...")

# ==========================================
# ZAKŁADKA 3: WIADOMOŚCI Z RYNKU (POPRAWIONA)
# ==========================================
with tab3:
    st.markdown("### 📰 Najświeższe komunikaty rynkowe (Ostatnie 7 dni)")
    st.write("Wiadomości pobierane z Google News z użyciem filtra czasu `when:7d`.")

    @st.cache_data(ttl=600) 
    def pobierz_wiadomosci_tydzien():
        wiadomosci = []
        # Dodajemy operator 'when:7d' do zapytania q
        url_google_news = "https://news.google.com/rss/search?q=GPW+OR+Gielda+OR+Akcje+when:7d&hl=pl&gl=PL&ceid=PL:pl"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        
        try:
            response = requests.get(url_google_news, headers=headers, timeout=5)
            root = ET.fromstring(response.content)
            # Zwiększamy limit z 20 do 50, aby objąć cały tydzień
            for item in root.findall('./channel/item')[:50]: 
                tytul = item.find('title').text
                link = item.find('link').text
                data_publikacji = item.find('pubDate').text
                if " - " in tytul:
                    tytul = tytul.rsplit(" - ", 1)[0]
                wiadomosci.append({"tytul": tytul, "link": link, "data": data_publikacji})
        except Exception as e:
            st.error("❌ Problem z połączeniem z Google News.")
            
        return wiadomosci

    if st.button("🔄 Odśwież wiadomości z tygodnia"):
        st.cache_data.clear() 

    artykuly = pobierz_wiadomosci_tydzien()
    
    if artykuly:
        for art in artykuly:
            with st.container():
                st.markdown(f"**[{art['tytul']}]({art['link']})**")
                st.caption(f"📅 {art['data']}")
                st.divider()
