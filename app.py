import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Skaner GPW PRO", layout="centered")
st.title("📈 Skaner Giełdowy PRO")

# Rozbudowany słownik z przypisanymi pełnymi nazwami
baza_spolek = {
    "ORLEN": ("PKN.WA", "Orlen S.A."), 
    "PKO": ("PKO.WA", "PKO Bank Polski"), 
    "PEKAO": ("PEO.WA", "Bank Pekao S.A."),
    "CD PROJEKT": ("CDR.WA", "CD Projekt S.A."), 
    "DINO": ("DNP.WA", "Dino Polska S.A."), 
    "ALLEGRO": ("ALE.WA", "Allegro.eu"),
    "PZU": ("PZU.WA", "PZU S.A."), 
    "LPP": ("LPP.WA", "LPP S.A."), 
    "KGHM": ("KGH.WA", "KGHM Polska Miedź"),
    "MBANK": ("MBK.WA", "mBank S.A."), 
    "XTB": ("XTB.WA", "XTB S.A."), 
    "JSW": ("JSW.WA", "Jastrzębska Spółka Węglowa"),
    "DIGITAL NETWORK": ("DIG.WA", "Digital Network S.A."), 
    "DIG": ("DIG.WA", "Digital Network S.A."),
    "ETF WIG20": ("ETFW20L.WA", "Beta ETF WIG20lev"), 
    "ETF SP500": ("ETFSP500.WA", "Beta ETF S&P 500"),
    "APPLE": ("AAPL", "Apple Inc."), 
    "MICROSOFT": ("MSFT", "Microsoft Corp."), 
    "TESLA": ("TSLA", "Tesla Inc.")
}

fraza = st.text_input("🔍 Wpisz nazwę firmy lub skrót giełdowy:", "DIGITAL NETWORK").strip().upper()

if st.button("Skanuj"):
    # Inteligentne przypisywanie symbolu i pełnej nazwy
    if fraza in baza_spolek:
        symbol = baza_spolek[fraza][0]
        pelna_nazwa = baza_spolek[fraza][1]
    else:
        symbol = fraza + ".WA" if "." not in fraza and not fraza.startswith("^") else fraza
        pelna_nazwa = symbol # Domyślnie używamy symbolu, dopóki nie pobierzemy nazwy

    with st.spinner(f'Pobieram dane dla {symbol}...'):
        stock = yf.Ticker(symbol)
        df = stock.history(period="1y")

        # Awaryjne szukanie w USA
        if df.empty and symbol.endswith(".WA"):
            symbol_us = symbol.replace(".WA", "")
            stock_us = yf.Ticker(symbol_us)
            df_us = stock_us.history(period="1y")
            if not df_us.empty:
                df = df_us
                symbol = symbol_us
                pelna_nazwa = symbol
                stock = stock_us

        if df.empty:
            st.error(f"❌ Brak danych dla '{fraza}'. Spróbuj innej nazwy.")
        else:
            # Ostrożna próba pobrania pełnej nazwy (jeśli wpisano z palca coś spoza słownika)
            if pelna_nazwa == symbol:
                try:
                    pelna_nazwa = stock.info.get('longName', symbol)
                except:
                    pass # Jeśli Yahoo blokuje połączenie, program się nie psuje, tylko wyświetla symbol

            ostatnia_cena = df['Close'].iloc[-1]

            # Obliczenia Bollinger i MACD
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

            # Logika Sygnałów
            bb_status = "🟢 WYPRZEDANA" if ostatnia_cena <= ost_lower * 1.02 else "🔴 PRZEGRZANA" if ostatnia_cena >= ost_upper * 0.98 else "🟡 NEUTRALNA"
            macd_status = "🟢 TREND WZROSTOWY" if ost_macd > ost_signal and ost_hist > 0 else "🔴 TREND SPADKOWY" if ost_macd < ost_signal and ost_hist < 0 else "🟡 ZMIANA TRENDU"

            # Wyświetlanie górnego panelu informacyjnego
            st.success(f"🏢 Spółka: **{pelna_nazwa}** ({symbol})")
            col1, col2, col3 = st.columns(3)
            col1.metric("Wycena", f"{ostatnia_cena:.2f} PLN")
            col2.metric("Bollinger", bb_status)
            col3.metric("MACD", macd_status)

            # Rysowanie wykresu
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1.5]})
            ax1.plot(df.index, df['Close'], label='Cena', color='#1f77b4', linewidth=2)
            ax1.plot(df.index, df['Upper_BB'], label='Górna Wstęga', color='red', linestyle=':', alpha=0.7)
            ax1.plot(df.index, df['Lower_BB'], label='Dolna Wstęga', color='green', linestyle=':', alpha=0.7)
            ax1.fill_between(df.index, df['Lower_BB'], df['Upper_BB'], color='gray', alpha=0.1)
            ax1.set_title(f"Notowania: {pelna_nazwa}", fontsize=14)
            ax1.legend(loc='upper left')
            ax1.grid(True, linestyle=':', alpha=0.6)

            colors = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
            ax2.bar(df.index, df['MACD_Hist'], color=colors, alpha=0.5, label='Siła Trendu')
            ax2.plot(df.index, df['MACD'], label='MACD', color='blue')
            ax2.plot(df.index, df['Signal'], label='Sygnał', color='orange')
            ax2.legend(loc='upper left')
            ax2.grid(True, linestyle=':', alpha=0.6)
            
            plt.tight_layout()
            st.pyplot(fig)

            # --- ROZWIJANA ŚCIĄGA DLA INWESTORA ---
            with st.expander("📖 JAK ODCZYTYWAĆ WSKAŹNIKI PRO? (Kliknij, aby rozwinąć)"):
                st.markdown("""
                ### 1. WSTĘGI BOLLINGERA (Górny wykres - Kanał)
                * **Szara strefa** to 'normalny' ruch ceny.
                * 🟢 **DOTKNIĘCIE ZIELONEJ LINII (Dolna wstęga):** Akcje są wyprzedane. Często oznacza to, że panika się kończy i zaraz nastąpi odbicie w górę.
                * 🔴 **DOTKNIĘCIE CZERWONEJ LINII (Górna wstęga):** Akcje są za drogie. Zbliża się korekta (spadek).

                ### 2. MACD (Dolny wykres - Wykrywacz trendu)
                * 🟢 **SYGNAŁ KUPNA (Złoty krzyż MACD):** Niebieska linia przecina pomarańczową od dołu. Słupki zmieniają kolor z czerwonego na zielony.
                * 🔴 **SYGNAŁ SPRZEDAŻY:** Niebieska linia spada poniżej pomarańczowej. Zielone słupki przechodzą w czerwone.

                ---
                💡 **ZŁOTA ZASADA: Szukaj podwójnego potwierdzenia!**
                Najlepsze momenty na zakup są wtedy, gdy cena dotyka zielonej dolnej wstęgi (Bollinger), a MACD zaczyna zawijać w górę i generować zielone słupki.
                """)import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Skaner GPW PRO", layout="centered")
st.title("📈 Skaner Giełdowy PRO")

slownik_nazw = {
    "ORLEN": "PKN.WA", "PKO": "PKO.WA", "PEKAO": "PEO.WA",
    "CD PROJEKT": "CDR.WA", "DINO": "DNP.WA", "ALLEGRO": "ALE.WA",
    "PZU": "PZU.WA", "LPP": "LPP.WA", "KGHM": "KGH.WA",
    "MBANK": "MBK.WA", "XTB": "XTB.WA", "JSW": "JSW.WA",
    "DIGITAL NETWORK": "DIG.WA", "DIG": "DIG.WA",
    "ETF WIG20": "ETFW20L.WA", "ETF SP500": "ETFSP500.WA",
    "APPLE": "AAPL", "MICROSOFT": "MSFT", "TESLA": "TSLA"
}

fraza = st.text_input("🔍 Wpisz nazwę firmy lub skrót giełdowy:", "DIGITAL NETWORK").strip().upper()

if st.button("Skanuj"):
    # Ustalanie symbolu i nazwy bez odpytywania zablokowanego API Yahoo o "info"
    if fraza in slownik_nazw:
        symbol = slownik_nazw[fraza]
        pelna_nazwa = fraza 
    else:
        symbol = fraza + ".WA" if "." not in fraza and not fraza.startswith("^") else fraza
        pelna_nazwa = symbol 

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
                pelna_nazwa = symbol

        if df.empty:
            st.error(f"❌ Brak danych dla '{fraza}'. Spróbuj innej nazwy.")
        else:
            ostatnia_cena = df['Close'].iloc[-1]

            # Obliczenia Bollinger i MACD
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

            # Logika Sygnałów
            bb_status = "🟢 WYPRZEDANA" if ostatnia_cena <= ost_lower * 1.02 else "🔴 PRZEGRZANA" if ostatnia_cena >= ost_upper * 0.98 else "🟡 NEUTRALNA"
            macd_status = "🟢 TREND WZROSTOWY" if ost_macd > ost_signal and ost_hist > 0 else "🔴 TREND SPADKOWY" if ost_macd < ost_signal and ost_hist < 0 else "🟡 ZMIANA TRENDU"

            st.success(f"🏢 Spółka: {pelna_nazwa} ({symbol})")
            col1, col2, col3 = st.columns(3)
            col1.metric("Wycena", f"{ostatnia_cena:.2f} PLN")
            col2.metric("Bollinger", bb_status)
            col3.metric("MACD", macd_status)

            # Rysowanie wykresu
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1.5]})
            ax1.plot(df.index, df['Close'], label='Cena', color='#1f77b4', linewidth=2)
            ax1.plot(df.index, df['Upper_BB'], label='Górna Wstęga', color='red', linestyle=':', alpha=0.7)
            ax1.plot(df.index, df['Lower_BB'], label='Dolna Wstęga', color='green', linestyle=':', alpha=0.7)
            ax1.fill_between(df.index, df['Lower_BB'], df['Upper_BB'], color='gray', alpha=0.1)
            ax1.set_title(f"Notowania: {pelna_nazwa}", fontsize=14)
            ax1.legend(loc='upper left')
            ax1.grid(True, linestyle=':', alpha=0.6)

            colors = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
            ax2.bar(df.index, df['MACD_Hist'], color=colors, alpha=0.5, label='Siła Trendu')
            ax2.plot(df.index, df['MACD'], label='MACD', color='blue')
            ax2.plot(df.index, df['Signal'], label='Sygnał', color='orange')
            ax2.legend(loc='upper left')
            ax2.grid(True, linestyle=':', alpha=0.6)
            
            plt.tight_layout()
            st.pyplot(fig)
