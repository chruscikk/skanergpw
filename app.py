import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import warnings
import os

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Skaner GPW PRO", layout="wide")
st.title("📈 Profesjonalny Skaner Giełdowy GPW")

# --- WCZYTYWANIE BAZY Z PLIKU TXT ---
@st.cache_data # Zapamiętuje dane, żeby nie czytać pliku przy każdym kliknięciu
def wczytaj_spolki():
    baza = []
    if os.path.exists("spolki.txt"):
        with open("spolki.txt", "r", encoding="utf-8") as f:
            for line in f:
                if " - " in line:
                    baza.append(line.strip())
    return baza

lista_spolek = wczytaj_spolki()
# Dodajemy opcję awaryjną na samej górze listy dla ETF-ów i giełd z USA
opcje_wyboru = ["--- Wpisz własny ticker (np. z USA lub ETF) ---"] + lista_spolek

tab1, tab2 = st.tabs(["🔍 Analiza Spółki (Skaner PRO)", "📡 Radar Okazji (Cały Rynek)"])

# ==========================================
# ZAKŁADKA 1: SKANER JEDNEJ SPÓŁKI
# ==========================================
with tab1:
    # Używamy inteligentnego pola wyboru z wbudowanym autouzupełnianiem
    wybor = st.selectbox("🔍 Wybierz spółkę z listy (zacznij wpisywać, by wyszukać):", opcje_wyboru)

    # Logika sprawdzania, co wybrał użytkownik
    if wybor == "--- Wpisz własny ticker (np. z USA lub ETF) ---":
        fraza = st.text_input("Wpisz skrót giełdowy (np. AAPL, ETFSP500):", "").strip().upper()
        uruchom = st.button("Skanuj Własny Ticker")
        if uruchom and fraza:
            symbol = fraza + ".WA" if "." not in fraza and not fraza.startswith("^") else fraza
            pelna_nazwa = symbol
    else:
        # Rozbijamy "ALE - Allegro" na "ALE" i "Allegro"
        czesc = wybor.split(" - ", 1)
        ticker = czesc[0].strip()
        pelna_nazwa = czesc[1].strip()
        symbol = ticker + ".WA"
        fraza = symbol
        uruchom = st.button(f"Skanuj spółkę: {pelna_nazwa}")

    if uruchom and fraza:
        with st.spinner(f'Pobieram dane dla {symbol}...'):
            stock = yf.Ticker(symbol)
            df = stock.history(period="1y")

            if df.empty and symbol.endswith(".WA"):
                symbol_us = symbol.replace(".WA", "")
                stock_us = yf.Ticker(symbol_us)
                df_us = stock_us.history(period="1y")
                if not df_us.empty:
                    df = df_us
                    symbol = symbol_us
                    if pelna_nazwa == symbol + ".WA": # Jeśli wpisano z palca
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

                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), gridspec_kw={'height_ratios': [3, 1.5]})
                
                ax1.plot(df.index, df['Close'], label='Cena', color='#1f77b4', linewidth=2)
                ax1.plot(df.index, df['Upper_BB'], label='Górna Wstęga (Opór)', color='red', linestyle=':', alpha=0.7)
                ax1.plot(df.index, df['Lower_BB'], label='Dolna Wstęga (Wsparcie)', color='green', linestyle=':', alpha=0.7)
                ax1.fill_between(df.index, df['Lower_BB'], df['Upper_BB'], color='gray', alpha=0.1)
                ax1.set_title(f"Notowania giełdowe: {pelna_nazwa}", fontsize=12)
                ax1.legend(loc='upper left')
                ax1.grid(True, linestyle=':', alpha=0.6)

                colors = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
                ax2.bar(df.index, df['MACD_Hist'], color=colors, alpha=0.5, label='Siła Trendu')
                ax2.plot(df.index, df['MACD'], label='MACD (Szybka)', color='blue')
                ax2.plot(df.index, df['Signal'], label='Sygnał (Wolna)', color='orange')
                ax2.legend(loc='upper left')
                ax2.grid(True, linestyle=':', alpha=0.6)
                
                plt.tight_layout()
                st.pyplot(fig)

                with st.expander("📖 JAK ODCZYTYWAĆ WSKAŹNIKI? (Legenda)"):
                    st.markdown("""
                    **1. WSTĘGI BOLLINGERA (Górny wykres)**
                    * 🟢 **Dolna wstęga (zielona kropkowana):** Jeśli cena do niej spada, akcje są "wyprzedane". Zwiększa się szansa na odbicie ceny w górę.
                    * 🔴 **Górna wstęga (czerwona kropkowana):** Jeśli cena do niej dociera, akcje są "za drogie". Ryzyko spadku.

                    **2. MACD (Dolny wykres)**
                    * 🟢 **Sygnał KUPNA:** Niebieska linia przecina pomarańczową od dołu. Słupki stają się zielone.
                    * 🔴 **Sygnał SPRZEDAŻY:** Niebieska linia spada poniżej pomarańczowej. Słupki stają się czerwone.
                    """)

# ==========================================
# ZAKŁADKA 2: RADAR OKAZJI
# ==========================================
with tab2:
    st.markdown("### 📡 Zeskanuj swoją listę spółek w poszukiwaniu okazji")
    
    # Radar korzysta teraz z tickerów wyciągniętych prosto z pliku spolki.txt!
    spolki_radar = [linia.split(" - ")[0].strip() + ".WA" for linia in lista_spolek]

    st.write(f"Ten radar przeanalizuje w tle **{len(spolki_radar)}** spółek dodanych do Twojego pliku `spolki.txt`.")

    if st.button("Uruchom Radar Okazji"):
        if len(spolki_radar) == 0:
            st.error("Twoja lista spółek jest pusta! Dodaj firmy do pliku spolki.txt.")
        else:
            with st.spinner('Pobieram pakiety danych z giełdy...'):
                dane_rynku = yf.download(spolki_radar, period="6mo", progress=False)
                # Obsługa struktury danych z yfinance dla jednej vs wielu spółek
                if len(spolki_radar) == 1:
                    ceny_zamkniecia = pd.DataFrame({spolki_radar[0]: dane_rynku['Close']})
                else:
                    ceny_zamkniecia = dane_rynku['Close']
                
                znalezione_okazje = []

                for ticker in spolki_radar:
                    try:
                        historia_cen = ceny_zamkniecia[ticker].dropna()
                        if len(historia_cen) < 50:
                            continue
                            
                        cena = historia_cen.iloc[-1]

                        sma20 = historia_cen.rolling(window=20).mean().iloc[-1]
                        std20 = historia_cen.rolling(window=20).std().iloc[-1]
                        ost_lower = sma20 - (std20 * 2)

                        ema12 = historia_cen.ewm(span=12, adjust=False).mean()
                        ema26 = historia_cen.ewm(span=26, adjust=False).mean()
                        macd = ema12 - ema26
                        signal = macd.ewm(span=9, adjust=False).mean()
                        hist = macd - signal

                        ost_macd = macd.iloc[-1]
                        ost_signal = signal.iloc[-1]
                        ost_hist = hist.iloc[-1]

                        sygnal_bb = cena <= (ost_lower * 1.03) 
                        sygnal_macd = ost_macd > ost_signal and ost_hist > 0

                        if sygnal_bb or sygnal_macd:
                            sila = "⭐⭐⭐ POTĘŻNY" if (sygnal_bb and sygnal_macd) else "⭐⭐ DOBRY" if sygnal_macd else "⭐ SŁABY"
                            
                            # Wyciągamy ładną nazwę spółki na podstawie tickera
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
                    st.warning("🤷‍♂️ W tym momencie żadna z obserwowanych przez Ciebie spółek nie generuje silnego sygnału kupna.")
