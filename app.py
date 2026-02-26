import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Skaner GPW PRO", layout="wide")
st.title("📈 Profesjonalny Skaner Giełdowy GPW")

# --- BAZA SPÓŁEK (Z pełnymi nazwami, żeby już ich nie brakowało) ---
baza_spolek = {
    # WIG20
    "ORLEN": ("PKN.WA", "Orlen S.A."), "PKN": ("PKN.WA", "Orlen S.A."),
    "PKO": ("PKO.WA", "PKO Bank Polski"), "PKO BP": ("PKO.WA", "PKO Bank Polski"),
    "PEKAO": ("PEO.WA", "Bank Pekao S.A."),
    "CD PROJEKT": ("CDR.WA", "CD Projekt S.A."), "CDR": ("CDR.WA", "CD Projekt S.A."),
    "DINO": ("DNP.WA", "Dino Polska S.A."), "ALLEGRO": ("ALE.WA", "Allegro.eu"),
    "PZU": ("PZU.WA", "PZU S.A."), "LPP": ("LPP.WA", "LPP S.A."),
    "KGHM": ("KGH.WA", "KGHM Polska Miedź"), "MBANK": ("MBK.WA", "mBank S.A."),
    "JSW": ("JSW.WA", "Jastrzębska Spółka Węglowa"), "KRUK": ("KRU.WA", "Kruk S.A."),
    "ALIOR": ("ALR.WA", "Alior Bank"), "CYFROWY POLSAT": ("CPS.WA", "Cyfrowy Polsat"),
    "PGE": ("PGE.WA", "Polska Grupa Energetyczna"), "TAURON": ("TPE.WA", "Tauron PE"),
    
    # Popularne mWIG40 i sWIG80
    "XTB": ("XTB.WA", "XTB S.A."), "CCC": ("CCC.WA", "CCC S.A."),
    "DIGITAL NETWORK": ("DIG.WA", "Digital Network S.A."), "DIG": ("DIG.WA", "Digital Network S.A."),
    "BUDIMEX": ("BDX.WA", "Budimex S.A."), "DOM DEVELOPMENT": ("DOM.WA", "Dom Development"),
    "11 BIT": ("11B.WA", "11 bit studios"), "TEN SQUARE GAMES": ("TEN.WA", "Ten Square Games"),
    "ŻABKA": ("ZAB.WA", "Żabka Group"), "PEPCO": ("PCO.WA", "Pepco Group"),
    "AUTO PARTNER": ("APR.WA", "Auto Partner"), "INTER CARS": ("CAR.WA", "Inter Cars"),
    "ASSECO": ("ACP.WA", "Asseco Poland"), "WP": ("WPL.WA", "Wirtualna Polska"),
    
    # ETFy
    "ETF WIG20": ("ETFW20L.WA", "Beta ETF WIG20lev"),
    "ETF SP500": ("ETFSP500.WA", "Beta ETF S&P 500 PLN"),
    "ETF NASDAQ": ("ETFNDXPL.WA", "Beta ETF Nasdaq 100"),
    
    # USA
    "APPLE": ("AAPL", "Apple Inc."), "MICROSOFT": ("MSFT", "Microsoft Corp."),
    "TESLA": ("TSLA", "Tesla Inc."), "NVIDIA": ("NVDA", "Nvidia Corp.")
}

# --- TWORZENIE ZAKŁADEK (TABS) ---
tab1, tab2 = st.tabs(["🔍 Analiza Spółki (Skaner PRO)", "📡 Radar Okazji (Cały Rynek)"])

# ==========================================
# ZAKŁADKA 1: SKANER JEDNEJ SPÓŁKI
# ==========================================
with tab1:
    fraza = st.text_input("🔍 Wpisz nazwę firmy, ETF lub skrót giełdowy:", "DIGITAL NETWORK").strip().upper()

    if st.button("Skanuj Spółkę"):
        # Ustalenie symbolu i nazwy
        if fraza in baza_spolek:
            symbol = baza_spolek[fraza][0]
            pelna_nazwa = baza_spolek[fraza][1]
        else:
            symbol = fraza + ".WA" if "." not in fraza and not fraza.startswith("^") else fraza
            pelna_nazwa = symbol # Używa symbolu, jeśli nazwy nie ma w bazie

        with st.spinner(f'Pobieram dane dla {symbol}...'):
            stock = yf.Ticker(symbol)
            df = stock.history(period="1y")

            # Szukanie w USA
            if df.empty and symbol.endswith(".WA"):
                symbol_us = symbol.replace(".WA", "")
                stock_us = yf.Ticker(symbol_us)
                df_us = stock_us.history(period="1y")
                if not df_us.empty:
                    df = df_us
                    symbol = symbol_us
                    pelna_nazwa = symbol

            if df.empty:
                st.error(f"❌ Brak danych dla '{fraza}'. Spróbuj innej nazwy lub użyj skrótu z giełdy.")
            else:
                ostatnia_cena = df['Close'].iloc[-1]

                # --- OBLICZENIA WSKAŹNIKÓW ---
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

                # --- SYGNAŁY ---
                bb_status = "🟢 WYPRZEDANA" if ostatnia_cena <= ost_lower * 1.02 else "🔴 PRZEGRZANA" if ostatnia_cena >= ost_upper * 0.98 else "🟡 NEUTRALNA"
                macd_status = "🟢 TREND WZROSTOWY" if ost_macd > ost_signal and ost_hist > 0 else "🔴 TREND SPADKOWY" if ost_macd < ost_signal and ost_hist < 0 else "🟡 ZMIANA TRENDU"

                # Wyświetlanie górnego panelu z PEŁNĄ NAZWĄ
                st.markdown(f"### 🏢 {pelna_nazwa} `({symbol})`")
                col1, col2, col3 = st.columns(3)
                col1.metric("Wycena", f"{ostatnia_cena:.2f}")
                col2.metric("Wstęgi Bollingera", bb_status)
                col3.metric("Wskaźnik MACD", macd_status)

                # --- WYKRES ---
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

                # --- ŚCIĄGA ---
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
    st.markdown("### 📡 Zeskanuj rynek w poszukiwaniu okazji")
    st.write("Ten radar pobierze w tle dane dla 40 najpopularniejszych polskich spółek i wyświetli tylko te, na których wskaźniki sugerują potencjalny moment do kupna.")
    
    spolki_radar = [
        "PKN.WA", "PKO.WA", "PEO.WA", "PZU.WA", "DNP.WA", "ALE.WA", "CDR.WA",
        "LPP.WA", "KGH.WA", "MBK.WA", "SPL.WA", "ALR.WA", "KRU.WA", "KTY.WA",
        "XTB.WA", "JSW.WA", "CCC.WA", "TPE.WA", "PGE.WA", "CPS.WA", "BDX.WA",
        "DOM.WA", "CAR.WA", "11B.WA", "TEN.WA", "APR.WA", "DIG.WA", "ZAB.WA",
        "PCO.WA", "BHW.WA", "MIL.WA", "DVL.WA", "EAT.WA", "GPW.WA", "ING.WA",
        "ASB.WA", "SLV.WA", "CMR.WA", "CIE.WA", "NEU.WA"
    ]

    if st.button("Uruchom Szybki Radar Okazji"):
        with st.spinner('Pobieram pakiety danych dla 40 spółek (To zajmie ok. 3-5 sekund)...'):
            # Optymalizacja - pobieramy wszystko jednym szybkim zapytaniem
            dane_rynku = yf.download(spolki_radar, period="6mo", progress=False)
            ceny_zamkniecia = dane_rynku['Close']
            
            znalezione_okazje = []

            for ticker in spolki_radar:
                try:
                    historia_cen = ceny_zamkniecia[ticker].dropna()
                    if len(historia_cen) < 50:
                        continue
                        
                    cena = historia_cen.iloc[-1]

                    # Bollinger
                    sma20 = historia_cen.rolling(window=20).mean().iloc[-1]
                    std20 = historia_cen.rolling(window=20).std().iloc[-1]
                    ost_lower = sma20 - (std20 * 2)

                    # MACD
                    ema12 = historia_cen.ewm(span=12, adjust=False).mean()
                    ema26 = historia_cen.ewm(span=26, adjust=False).mean()
                    macd = ema12 - ema26
                    signal = macd.ewm(span=9, adjust=False).mean()
                    hist = macd - signal

                    ost_macd = macd.iloc[-1]
                    ost_signal = signal.iloc[-1]
                    ost_hist = hist.iloc[-1]

                    # Warunki sygnału kupna
                    sygnal_bb = cena <= (ost_lower * 1.03) # 3% tolerancji przy dolnej bandzie
                    sygnal_macd = ost_macd > ost_signal and ost_hist > 0

                    if sygnal_bb or sygnal_macd:
                        if sygnal_bb and sygnal_macd:
                            sila = "⭐⭐⭐ POTĘŻNY"
                        elif sygnal_macd:
                            sila = "⭐⭐ DOBRY (Trend)"
                        else:
                            sila = "⭐ SŁABY (Niska cena)"

                        znalezione_okazje.append({
                            "Symbol": ticker.replace(".WA", ""),
                            "Ostatnia Cena": round(cena, 2),
                            "Bollinger (Wyprzedana)": "✅ TAK" if sygnal_bb else "➖",
                            "MACD (Trend rosnący)": "✅ TAK" if sygnal_macd else "➖",
                            "Siła Sygnału": sila
                        })
                except Exception:
                    continue

            if len(znalezione_okazje) > 0:
                df_wyniki = pd.DataFrame(znalezione_okazje)
                df_wyniki = df_wyniki.sort_values(by="Siła Sygnału", ascending=False).reset_index(drop=True)
                st.success("🎯 Znalazłem następujące okazje na rynku:")
                st.dataframe(df_wyniki, use_container_width=True)
                st.info("💡 **Co dalej?** Skopiuj symbol najbardziej obiecującej spółki z tabeli i wpisz go w pierwszej zakładce 'Analiza Spółki', aby obejrzeć jej wykres i sprawdzić detale.")
            else:
                st.warning("🤷‍♂️ W tym momencie żadna ze śledzonych spółek nie generuje silnego sygnału kupna na wskaźnikach. Rynek czeka na rozstrzygnięcie.")
