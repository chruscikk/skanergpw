import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import os

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

# --- PAMIĘĆ SESJI DLA ULUBIONYCH ---
if 'ulubione_zapisane' not in st.session_state:
    st.session_state['ulubione_zapisane'] = []

tab1, tab2, tab3 = st.tabs(["🔍 Analiza Spółki", "📡 Radar Okazji", "⭐ Moje Ulubione"])

# ==========================================
# ZAKŁADKA 1: SKANER JEDNEJ SPÓŁKI
# ==========================================
with tab1:
    col_wyszukiwarka, col_okres = st.columns([3, 1])
    
    with col_wyszukiwarka:
        wybor = st.selectbox("🔍 Wybierz spółkę z listy:", opcje_wyboru)
    with col_okres:
        okres = st.selectbox("📅 Zakres danych:", ["1mo", "6mo", "1y", "2y", "5y", "max"], index=3)

    if wybor == "--- Wpisz własny ticker (np. z USA lub ETF) ---":
        fraza = st.text_input("Wpisz skrót giełdowy (np. AAPL, ETFSP500):", "").strip().upper()
        uruchom = st.button("Skanuj Własny Ticker")
        if uruchom and fraza:
            symbol = fraza + ".WA" if "." not in fraza and not fraza.startswith("^") else fraza
            pelna_nazwa = symbol
    else:
        czesc = wybor.split(" - ", 1)
        ticker = czesc[0].strip()
        pelna_nazwa = czesc[1].strip()
        symbol = ticker + ".WA"
        fraza = symbol
        uruchom = st.button(f"Skanuj spółkę: {pelna_nazwa}")

    if uruchom and fraza:
        with st.spinner(f'Pobieram dane dla {symbol} (Okres: {okres})...'):
            stock = yf.Ticker(symbol)
            df = stock.history(period=okres)

            if df.empty and symbol.endswith(".WA"):
                symbol_us = symbol.replace(".WA", "")
                stock_us = yf.Ticker(symbol_us)
                df_us = stock_us.history(period=okres)
                if not df_us.empty:
                    df = df_us
                    symbol = symbol_us
                    if pelna_nazwa == symbol + ".WA": 
                        pelna_nazwa = symbol

            if df.empty:
                st.error(f"❌ Brak danych dla '{fraza}'. Upewnij się, że skrót jest poprawny.")
            else:
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

                ost_upper, ost_lower = df['Upper_BB'].iloc[-1], df['Lower_BB'].iloc[-1]
                ost_macd, ost_signal, ost_hist = df['MACD'].iloc[-1], df['Signal'].iloc[-1], df['MACD_Hist'].iloc[-1]

                bb_status = "🟢 WYPRZEDANA" if ostatnia_cena <= ost_lower * 1.02 else "🔴 PRZEGRZANA" if ostatnia_cena >= ost_upper * 0.98 else "🟡 NEUTRALNA"
                macd_status = "🟢 TREND WZROSTOWY" if ost_macd > ost_signal and ost_hist > 0 else "🔴 TREND SPADKOWY" if ost_macd < ost_signal and ost_hist < 0 else "🟡 ZMIANA TRENDU"

                st.markdown(f"### 🏢 {pelna_nazwa} `({symbol})`")
                col1, col2, col3 = st.columns(3)
                col1.metric("Wycena", f"{ostatnia_cena:.2f}")
                col2.metric("Wstęgi Bollingera", bb_status)
                col3.metric("Wskaźnik MACD", macd_status)

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.05, row_heights=[0.7, 0.3],
                                    subplot_titles=(f"Notowania (Bollinger Bands)", "MACD"))

                fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', 
                                         name='Cena', line=dict(color='#1f77b4', width=2)), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], mode='lines', 
                                         name='Górna Wstęga', line=dict(color='rgba(255, 0, 0, 0.5)', width=1, dash='dot')), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], mode='lines', 
                                         name='Dolna Wstęga', line=dict(color='rgba(0, 128, 0, 0.5)', width=1, dash='dot'), 
                                         fill='tonexty', fillcolor='rgba(128, 128, 128, 0.1)'), row=1, col=1)

                kolory_macd = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Siła Trendu', marker_color=kolory_macd), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD', line=dict(color='blue', width=1.5)), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], mode='lines', name='Sygnał', line=dict(color='orange', width=1.5)), row=2, col=1)

                fig.update_layout(height=700, margin=dict(l=20, r=20, t=40, b=20), 
                                  hovermode='x unified', showlegend=False)
                fig.update_xaxes(rangeslider_visible=False)
                
                st.plotly_chart(fig, use_container_width=True)

# ==========================================
# ZAKŁADKA 2: RADAR OKAZJI
# ==========================================
with tab2:
    st.markdown("### 📡 Zeskanuj swoją listę spółek")
    spolki_radar = [linia.split(" - ")[0].strip() + ".WA" for linia in lista_spolek]

    st.write(f"Ten radar przeanalizuje w tle **{len(spolki_radar)}** spółek dodanych do Twojego pliku `spolki.txt`.")

    if st.button("Uruchom Radar Okazji"):
        if len(spolki_radar) == 0:
            st.error("Twoja lista spółek jest pusta! Dodaj firmy do pliku spolki.txt.")
        else:
            with st.spinner('Pobieram pakiety danych z giełdy...'):
                dane_rynku = yf.download(spolki_radar, period="6mo", progress=False)
                if len(spolki_radar) == 1:
                    ceny_zamkniecia = pd.DataFrame({spolki_radar[0]: dane_rynku['Close']})
                else:
                    ceny_zamkniecia = dane_rynku['Close']
                
                znalezione_okazje = []

                for ticker in spolki_radar:
                    try:
                        historia_cen = ceny_zamkniecia[ticker].dropna()
                        if len(historia_cen) < 50: continue
                        cena = historia_cen.iloc[-1]

                        sma20 = historia_cen.rolling(window=20).mean().iloc[-1]
                        std20 = historia_cen.rolling(window=20).std().iloc[-1]
                        ost_lower = sma20 - (std20 * 2)

                        ema12 = historia_cen.ewm(span=12, adjust=False).mean()
                        ema26 = historia_cen.ewm(span=26, adjust=False).mean()
                        macd = ema12 - ema26
                        signal = macd.ewm(span=9, adjust=False).mean()
                        hist = macd - signal

                        ost_macd, ost_signal, ost_hist = macd.iloc[-1], signal.iloc[-1], hist.iloc[-1]

                        sygnal_bb = cena <= (ost_lower * 1.02) 
                        sygnal_macd = ost_macd > ost_signal and ost_hist > 0

                        if sygnal_bb or sygnal_macd:
                            sila = "⭐⭐⭐ POTĘŻNY" if (sygnal_bb and sygnal_macd) else "⭐⭐ DOBRY" if sygnal_macd else "⭐ SŁABY"
                            nazwa_dla_radaru = ticker.replace(".WA", "")
                            for linia in lista_spolek:
                                if linia.startswith(nazwa_dla_radaru + " -"):
                                    nazwa_dla_radaru = linia.split(" - ")[1].strip()
                                    break

                            znalezione_okazje.append({
                                "Nazwa Spółki": nazwa_dla_radaru,
                                "Symbol": ticker.replace(".WA", ""),
                                "Cena (PLN)": round(cena, 2),
                                "Bollinger (Okazja)": "✅ TAK" if sygnal_bb else "➖",
                                "MACD (Trend)": "✅ TAK" if sygnal_macd else "➖",
                                "Siła Sygnału": sila
                            })
                    except Exception:
                        continue

                if len(znalezione_okazje) > 0:
                    df_wyniki = pd.DataFrame(znalezione_okazje)
                    df_wyniki = df_wyniki.sort_values(by="Siła Sygnału", ascending=False).reset_index(drop=True)
                    st.success("🎯 Znalazłem następujące okazje na rynku:")
                    st.dataframe(df_wyniki, use_container_width=True)
                else:
                    st.warning("🤷‍♂️ Żadna z obserwowanych przez Ciebie spółek nie generuje silnego sygnału kupna.")

# ==========================================
# ZAKŁADKA 3: MOJE ULUBIONE (Pulpit nawigacyjny)
# ==========================================
with tab3:
    st.markdown("### ⭐ Panel Obserwowanych Spółek")
    st.write("Wybierz poniżej spółki, które chcesz mieć stale na oku. Aplikacja zapamięta ten wybór na czas trwania Twojej sesji w przeglądarce.")
    
    # Multiselect do zarządzania ulubionymi
    wybrane_ulubione = st.multiselect(
        "Wybierz spółki do panelu:", 
        lista_spolek, 
        default=st.session_state['ulubione_zapisane']
    )
    
    # Zapisujemy zmiany do pamięci sesji
    st.session_state['ulubione_zapisane'] = wybrane_ulubione

    if len(wybrane_ulubione) > 0:
        if st.button("🔄 Pobierz aktualne dane dla ulubionych"):
            with st.spinner("Pobieram najświeższe dane..."):
                tickers_ulubione = [x.split(" - ")[0].strip() + ".WA" for x in wybrane_ulubione]
                
                # Szybkie pobieranie paczką tak jak w radarze
                dane_ulubione = yf.download(tickers_ulubione, period="6mo", progress=False)
                if len(tickers_ulubione) == 1:
                    ceny_ulubione = pd.DataFrame({tickers_ulubione[0]: dane_ulubione['Close']})
                else:
                    ceny_ulubione = dane_ulubione['Close']
                
                wyniki_ulubione = []
                
                for ticker, oryginalna_nazwa in zip(tickers_ulubione, wybrane_ulubione):
                    try:
                        historia = ceny_ulubione[ticker].dropna()
                        if len(historia) < 50: continue
                        cena = historia.iloc[-1]

                        # Obliczenia Bollinger
                        sma20 = historia.rolling(window=20).mean().iloc[-1]
                        std20 = historia.rolling(window=20).std().iloc[-1]
                        ost_lower, ost_upper = sma20 - (std20 * 2), sma20 + (std20 * 2)

                        # Obliczenia MACD
                        ema12 = historia.ewm(span=12, adjust=False).mean()
                        ema26 = historia.ewm(span=26, adjust=False).mean()
                        macd = ema12 - ema26
                        signal = macd.ewm(span=9, adjust=False).mean()
                        hist = macd - signal

                        ost_macd, ost_signal, ost_hist = macd.iloc[-1], signal.iloc[-1], hist.iloc[-1]

                        # Logika statusów (Zmieniona na krótkie, opisowe komunikaty do tabeli)
                        if cena <= ost_lower * 1.02: bb_stat = "🟢 Wyprzedana"
                        elif cena >= ost_upper * 0.98: bb_stat = "🔴 Przegrzana"
                        else: bb_stat = "🟡 Neutralna"

                        if ost_macd > ost_signal and ost_hist > 0: macd_stat = "🟢 Wzrostowy"
                        elif ost_macd < ost_signal and ost_hist < 0: macd_stat = "🔴 Spadkowy"
                        else: macd_stat = "🟡 Zmiana trendu"

                        wyniki_ulubione.append({
                            "Spółka": oryginalna_nazwa.split(" - ")[1].strip(),
                            "Symbol": ticker.replace(".WA", ""),
                            "Ostatnia Cena": f"{cena:.2f} PLN",
                            "Bollinger": bb_stat,
                            "MACD": macd_stat
                        })
                    except Exception:
                        continue

                if len(wyniki_ulubione) > 0:
                    st.markdown("#### 📊 Aktualny stan Twoich ulubionych:")
                    # Wyświetlamy jako ładną, pozbawioną indeksu tabelę
                    st.dataframe(pd.DataFrame(wyniki_ulubione), use_container_width=True, hide_index=True)
    else:
        st.info("👆 Dodaj wyżej pierwsze spółki do obserwowanych, aby zobaczyć podsumowanie.")
