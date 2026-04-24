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

# --- UNIWERSALNA FUNKCJA WCZYTUJĄCA PLIKI ---
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
    [
        "🔍 Skaner (Pojedyncza spółka)", 
        "📡 Radar Okazji (Wzrosty)", 
        "📉 Radar Spadków (Łapanie dołków)",
        "💰 Dywidendy (Kto płaci?)",
        "📰 Wiadomości (GPW)"
    ]
)

if narzedzie != "📰 Wiadomości (GPW)":
    st.sidebar.markdown("---")
    wybrany_rynek = st.sidebar.radio("2️⃣ Wybierz rynek:", ["SKANER GPW", "SKANER WIG", "SKANER NEW CONNECT"])
    
    if wybrany_rynek == "SKANER GPW":
        aktywna_lista, nazwa_pliku_info = lista_gpw, "spolki.txt"
    elif wybrany_rynek == "SKANER WIG":
        aktywna_lista, nazwa_pliku_info = lista_wig, "spolkiwig.txt"
    else:
        aktywna_lista, nazwa_pliku_info = lista_nc, "spolkinc.txt"

st.sidebar.markdown("---")
st.sidebar.info("💡 **Wskazówka:** Na telefonie zwiń to menu strzałką w lewym górnym rogu.")


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

            if df.empty and symbol.endswith(".WA"):
                symbol_us = symbol.replace(".WA", "")
                stock_us = yf.Ticker(symbol_us)
                df_us = stock_us.history(period=okres)
                if not df_us.empty: df, symbol, pelna_nazwa = df_us, symbol_us, symbol_us if pelna_nazwa == symbol + ".WA" else pelna_nazwa

            if df.empty:
                st.error(f"❌ Brak danych dla '{fraza}'.")
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

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3], subplot_titles=(f"Notowania", "MACD"))
                if typ_wykresu == "Świecowy": fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Świece'), row=1, col=1)
                else: fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Cena', line=dict(color='#1f77b4', width=2)), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], mode='lines', name='Górna', line=dict(color='red', width=1, dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], mode='lines', name='Dolna', line=dict(color='green', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

                kolory_macd = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=kolory_macd), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', line=dict(color='blue')), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], mode='lines', line=dict(color='orange')), row=2, col=1)

                fig.update_layout(height=750, margin=dict(l=20, r=20, t=40, b=20), hovermode='x unified', showlegend=False)
                fig.update_xaxes(rangeslider_visible=False, row=1, col=1) 
                fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.05, row=2, col=1) 
                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# ------------------------------------------
# NARZĘDZIE 2: RADAR OKAZJI WZROSTÓW
# ------------------------------------------
elif narzedzie == "📡 Radar Okazji (Wzrosty)":
    st.title(f"📡 {wybrany_rynek} - Szukanie Wzrostów")
    if len(aktywna_lista) == 0: st.error("Lista spółek jest pusta!")
    else:
        spolki_radar = [linia.split(" - ")[0].strip() + ".WA" for linia in aktywna_lista]
        if st.button("Skanuj rynek"):
            with st.spinner('Pobieram dane...'):
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
                        hist_macd = macd - sig
                        
                        syg_bb = cena <= (ost_lower * 1.03) 
                        syg_macd = macd.iloc[-1] > sig.iloc[-1] and hist_macd.iloc[-1] > 0
                        if syg_bb or syg_macd:
                            sila = "⭐⭐⭐ POTĘŻNY" if (syg_bb and syg_macd) else "⭐⭐ DOBRY" if syg_macd else "⭐ SŁABY"
                            nazwa = next((l.split(" - ")[1].strip() for l in aktywna_lista if l.startswith(ticker.replace(".WA", ""))), ticker)
                            okazje.append({"Spółka": nazwa, "Symbol": ticker.replace(".WA", ""), "Cena PLN": round(cena,2), "Siła": sila})
                    except: continue
                if okazje:
                    df_wyniki = pd.DataFrame(okazje).sort_values(by="Siła", ascending=False).reset_index(drop=True)
                    st.dataframe(df_wyniki, use_container_width=True)
                else: st.warning("Brak sygnałów kupna.")

# ------------------------------------------
# NARZĘDZIE 3: RADAR SPADKÓW (NOWOŚĆ)
# ------------------------------------------
elif narzedzie == "📉 Radar Spadków (Łapanie dołków)":
    st.title(f"📉 {wybrany_rynek} - Radar Spadków")
    st.write("Skaner wykrywa spółki, które mocno tanieją. **Warunek:** Spadek trwający minimum 3 dni z rzędu LUB jednodniowy krach powyżej 10%.")
    
    if len(aktywna_lista) == 0: st.error("Lista spółek jest pusta!")
    else:
        spolki_radar = [linia.split(" - ")[0].strip() + ".WA" for linia in aktywna_lista]
        if st.button("Uruchom detektor spadków"):
            with st.spinner('Analizuję dynamikę cen...'):
                # Pobieramy szerszy zakres danych dla szczytów
                dane = yf.download(spolki_radar, period="2mo", progress=False)['Close']
                if isinstance(dane, pd.Series): dane = dane.to_frame(name=spolki_radar[0])
                
                znalezione_spadki = []

                for ticker in spolki_radar:
                    try:
                        hist = dane[ticker].dropna()
                        if len(hist) < 15: continue
                        
                        c0 = hist.iloc[-1] # Dziś
                        c1 = hist.iloc[-2] # Wczoraj
                        c2 = hist.iloc[-3] # Przedwczoraj
                        c3 = hist.iloc[-4] # 3 dni temu
                        
                        # Warunek 1: Jednodniowy krach > 10%
                        spadek_1d_proc = ((c0 - c1) / c1) * 100
                        krach_10 = spadek_1d_proc <= -10.0
                        
                        # Warunek 2: Spadek 3 dni z rzędu
                        spadek_3_dni = (c0 < c1) and (c1 < c2) and (c2 < c3)
                        
                        if krach_10 or spadek_3_dni:
                            # Szukamy "szczytu" przed rozpoczęciem spadku (najwyższa cena z ostatnich 14 dni)
                            szczyt = hist.tail(14).max()
                            laczny_spadek = ((c0 - szczyt) / szczyt) * 100
                            
                            powod = "🔴 Krach >10%" if krach_10 else "🔻 Spadek od 3 dni"
                            nazwa = next((l.split(" - ")[1].strip() for l in aktywna_lista if l.startswith(ticker.replace(".WA", ""))), ticker)
                            
                            znalezione_spadki.append({
                                "Nazwa Spółki": nazwa,
                                "Symbol": ticker.replace(".WA", ""),
                                "Cena przed spadkiem (Szczyt)": f"{szczyt:.2f} PLN",
                                "Aktualna Cena": f"{c0:.2f} PLN",
                                "Głębokość Spadku": f"{laczny_spadek:.2f}%",
                                "Typ Spadku": powod
                            })
                    except Exception:
                        continue

                if znalezione_spadki:
                    df_wyniki = pd.DataFrame(znalezione_spadki).sort_values(by="Głębokość Spadku", ascending=True).reset_index(drop=True)
                    st.error("🚨 Wykryto mocne przeceny na poniższych spółkach:")
                    st.dataframe(df_wyniki, use_container_width=True)
                else:
                    st.success("🟢 Na rynku jest spokojnie. Żadna spółka nie spełnia rygorystycznych kryteriów gwałtownego spadku.")

# ------------------------------------------
# NARZĘDZIE 4: DYWIDENDY (NOWOŚĆ)
# ------------------------------------------
elif narzedzie == "💰 Dywidendy (Kto płaci?)":
    st.title(f"💰 {wybrany_rynek} - Skaner Dywidendowy")
    st.info("ℹ️ Amerykańskie API Yahoo Finance nie podaje przyszłych dat wypłat dla GPW. Skaner bazuje na historii wypłat z ostatnich 12 miesięcy, obliczając dla Ciebie realną roczną Stopę Dywidendy (Yield).")
    
    if len(aktywna_lista) == 0: st.error("Lista spółek jest pusta!")
    else:
        spolki_radar = [linia.split(" - ")[0].strip() + ".WA" for linia in aktywna_lista]
        
        if st.button("Szukaj spółek płacących dywidendę"):
            with st.spinner('Analizuję raporty z ostatnich 12 miesięcy... to może chwilę potrwać.'):
                znalezione_dywidendy = []
                
                # Zamiast pobierać masowo, sprawdzamy po kolei, aby dostać tabelę dywidend
                for ticker in spolki_radar:
                    try:
                        akcja = yf.Ticker(ticker)
                        # Pobieramy dane z ostatniego roku
                        df = akcja.history(period="1y")
                        if df.empty or 'Dividends' not in df.columns:
                            continue
                            
                        # Szukamy dni, w których wypłacono dywidendę
                        dywidendy = df[df['Dividends'] > 0]
                        
                        if not dywidendy.empty:
                            suma_wyplat = dywidendy['Dividends'].sum()
                            ostatnia_cena = df['Close'].iloc[-1]
                            
                            # Obliczenie stopy dywidendy (Yield)
                            stopa = (suma_wyplat / ostatnia_cena) * 100
                            
                            nazwa = next((l.split(" - ")[1].strip() for l in aktywna_lista if l.startswith(ticker.replace(".WA", ""))), ticker)
                            
                            znalezione_dywidendy.append({
                                "Spółka": nazwa,
                                "Symbol": ticker.replace(".WA", ""),
                                "Wypłacono w 12 msc": f"{suma_wyplat:.2f} PLN",
                                "Cena Akcji": f"{ostatnia_cena:.2f} PLN",
                                "Stopa Dywidendy (Yield)": f"{stopa:.2f}%"
                            })
                    except Exception:
                        continue

                if znalezione_dywidendy:
                    # Sortujemy od największej stopy dywidendy
                    df_wyniki = pd.DataFrame(znalezione_dywidendy)
                    # Konwersja formatu do liczby, żeby poprawnie posortować
                    df_wyniki['sort_val'] = df_wyniki['Stopa Dywidendy (Yield)'].str.replace('%','').astype(float)
                    df_wyniki = df_wyniki.sort_values(by="sort_val", ascending=False).drop(columns=['sort_val']).reset_index(drop=True)
                    
                    st.success(f"💸 Znaleziono {len(df_wyniki)} spółek wypłacających dywidendy:")
                    st.dataframe(df_wyniki, use_container_width=True)
                    st.markdown("*Chcesz poznać przyszłe daty Ex-Dividend? Najlepszym miejscem do ich sprawdzania dla polskiego rynku jest kalendarz portalu [Bankier.pl](https://www.bankier.pl/gielda/wiadomosci/dywidendy).*")
                else:
                    st.warning("Przez ostatnie 12 miesięcy żadna spółka z tej listy nie wypłaciła dywidendy.")

# ------------------------------------------
# NARZĘDZIE 5: WIADOMOŚCI
# ------------------------------------------
elif narzedzie == "📰 Wiadomości (GPW)":
    st.title("📰 Najświeższe komunikaty rynkowe (Ostatnie 7 dni)")

    @st.cache_data(ttl=600) 
    def pobierz_wiadomosci_tydzien():
        wiadomosci = []
        url_google_news = "https://news.google.com/rss/search?q=GPW+OR+Giełda+Papierów+Wartościowych+OR+Akcje+when:7d&hl=pl&gl=PL&ceid=PL:pl"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(url_google_news, headers=headers, timeout=5)
            root = ET.fromstring(response.content)
            for item in root.findall('./channel/item')[:50]: 
                tytul = item.find('title').text
                link = item.find('link').text
                data_publikacji = item.find('pubDate').text
                if " - " in tytul: tytul = tytul.rsplit(" - ", 1)[0]
                wiadomosci.append({"tytul": tytul, "link": link, "data": data_publikacji})
            if wiadomosci: wiadomosci.sort(key=lambda x: pd.to_datetime(x['data'], utc=True), reverse=True)
        except Exception: st.error("❌ Problem z połączeniem z Google News.")
        return wiadomosci

    if st.button("🔄 Odśwież wiadomości"): st.cache_data.clear() 

    artykuly = pobierz_wiadomosci_tydzien()
    if artykuly:
        for art in artykuly:
            with st.container():
                st.markdown(f"**[{art['tytul']}]({art['link']})**")
                st.caption(f"📅 {pd.to_datetime(art['data']).strftime('%Y-%m-%d %H:%M')}")
                st.divider()
