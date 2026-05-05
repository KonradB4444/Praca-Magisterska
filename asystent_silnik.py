import os
import xgboost as xgb
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
import streamlit as st


model_zgon = xgb.XGBClassifier()
model_zgon.load_model("xgboost_zgon.json")

model_dializa = xgb.XGBClassifier()
model_dializa.load_model("xgboost_dializa.json")

@tool
def oblicz_ryzyko(
    wiek: int, liczba_zajetych_narzadow: int, plazmaferezy: int,
    zaostrz_wymagajace_oit: int, manifestacja_pokarmowy: int,
    manifestacja_zajecie_csn: int, manifestacja_moczowo_plciowy: int,
    manifestacja_wzrok: int, manifestacja_skora: int,
    manifestacja_neurologiczny: int, manifestacja_sercowo_naczyniowy: int,
    opoznienie_rozpoznia: int, manifestacja_miesno_szkiel: int,
    kreatynina: float, leczenie_plazmaferezy: int, rozpoznanie: int,
    przebieg_scalony: int, manifestacja_nerki: int
) -> str:
    """
    Narzędzie oblicza ryzyko zgonu i trwałej dializoterapii.
    Wymaga podania 18 unikalnych parametrów klinicznych pacjenta.
    """

    df_zgon_dict = {
        'Wiek': wiek, # Technicznie nie było w benchmarku ale raczej dać trzeba
        'Liczba_Zajetych_Narzadow': liczba_zajetych_narzadow,
        'Zaostrz_Wymagajace_OIT': zaostrz_wymagajace_oit,
        'Manifestacja_Pokarmowy': manifestacja_pokarmowy,
        'Manifestacja_Zajecie_CSN': manifestacja_zajecie_csn,
        'Manifestacja_Moczowo-Plciowy': manifestacja_moczowo_plciowy,
        'Plazmaferezy': plazmaferezy,
        'Manifestacja_Wzrok': manifestacja_wzrok,
        'Manifestacja_Skora': manifestacja_skora,
        'Manifestacja_Neurologiczny': manifestacja_neurologiczny,
        'Manifestacja_Sercowo-Naczyniowy': manifestacja_sercowo_naczyniowy,
        'Opoznienie_Rozpoznia': opoznienie_rozpoznia,
        'Manifestacja_Miesno-Szkiel': manifestacja_miesno_szkiel
    }

    df_dial_dict = {
        'Wiek': wiek,
        'Kreatynina': kreatynina,
        'Plazmaferezy': plazmaferezy,
        'Leczenie_Plazmaferezy': leczenie_plazmaferezy,
        'Rozpoznanie': rozpoznanie,
        'Przebieg_scalony': przebieg_scalony,
        'Manifestacja_Nerki': manifestacja_nerki,
        'Liczba_Zajetych_Narzadow': liczba_zajetych_narzadow
    }

    df_zgon = pd.DataFrame([df_zgon_dict])
    df_dial = pd.DataFrame([df_dial_dict])

    if "ostatnie_parametry" not in st.session_state:
        st.session_state.ostatnie_parametry = {}
        
    st.session_state.ostatnie_parametry = {
        "XGBoost_Zgon_Input": df_zgon_dict,
        "XGBoost_Dializa_Input": df_dial_dict
    }

    # Predykcja prawdopodobieństwa (indeks [1] to klasa pozytywna)
    ryzyko_zgon = 100 - (model_zgon.predict_proba(df_zgon)[0][1] * 100)
    ryzyko_dializa = model_dializa.predict_proba(df_dial)[0][1] * 100

    # Potrzebne do ładnego podsumowania na końcu
    wynik_zgon_val = float(ryzyko_zgon)
    wynik_dial_val = float(ryzyko_dializa)

    st.session_state.tymczasowe_wyniki_ui = {
        "zgon": round(wynik_zgon_val, 2),
        "dializa": round(wynik_dial_val, 2)
    }

    return (f"Obliczenia XGBoost zakończone. "
            f"Ryzyko zgonu wynosi {ryzyko_zgon:.1f}%. "
            f"Ryzyko konieczności dializy wynosi {ryzyko_dializa:.1f}%.")

class Asystent:
    def __init__(self, klucz_api):
        os.environ["GOOGLE_API_KEY"] = klucz_api
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature = 0)
        self.agent = self.llm.bind_tools([oblicz_ryzyko])
        system_prompt = """Jesteś inteligentnym Asystentem Medycznym.
        Twoim celem jest zebranie 18 parametrów od lekarza w celu obliczenia ryzyka klinicznego.
        Zadawaj pytania naturalnie, po 2 lub 3 naraz, aby nie przytłoczyć użytkownika.
        Jeśli użytkownik poda informacje ogólnikowo, samodzielnie zmapuj je na format liczbowy/binarny.

        Pamiętaj, by wyciągnąć informacje o wieku, kreatyninie, liczbie zajętych narządów, pobycie na OIT, plazmaferezie, opóźnieniu rozpoznania,
        rozpoznaniu, przebiegu scalonym oraz manifestacjach (pokarmowej, CSN, moczowo-płciowej, wzrokowej, 
        skórnej, neurologicznej, sercowo-naczyniowej, mięśniowo-szkieletowej, nerkowej) i leczeniu plazmaferezą.

        Gdy uznasz, że zebrałeś wszystkie niezbędne parametry z listy narzędzia, WYWOŁAJ FUNKCJĘ oblicz_ryzyko.
        Po otrzymaniu wyniku z funkcji, przedstaw go lekarzowi w profesjonalny sposób.

        NIGDY nie pytaj użytkownika o skale numeryczne, typy zmiennych ani jednostki, w których działa narzędzie. 
        Zamiast tego SAMODZIELNIE w locie przeliczaj i mapuj podane przez lekarza informacje zgodnie z poniższymi instrukcjami:

        JEDNOSTKI I FORMATY (KRYTYCZNE)
        1. 'opoznienie_rozpoznania': ZAWSZE przeliczaj na DNI. (np. jeśli lekarz mówi "4 tygodnie", przekaż 28; jeśli "2 miesiące", przekaż 60). Podaj samą liczbę.
        2. 'kreatynina': Narzędzie oczekuje wartości w umol/l. Jeśli lekarz poda małą wartość sugerującą mg/dl (np. 0.8 do 15.0), samodzielnie pomnóż ją przez 88.4 przed przekazaniem do narzędzia.
        3. Parametry binarne (OIT, plazmafereza, wszystkie manifestacje): Jeśli pacjent miał objaw/leczenie, przekaż cyfrę 1. Jeśli nie miał, przekaż 0.

        LEGENDA DO MAPOWANIA (Tłumacz słowa na poniższe liczby)
        Parametr 'przebieg_scalony' (skala 0-9 określająca ciężkość):
        Jeśli lekarz opisze przebieg jako łagodny / brak zaostrzeń -> przekaż 2
        Jeśli lekarz opisze przebieg jako umiarkowany / wymagał hospitalizacji -> przekaż 5
        Jeśli lekarz opisze przebieg jako ciężki / krytyczny / pobyt na OIT -> przekaż 8

        Parametr 'rozpoznanie':
        Jeśli lekarz opisze chorobę zapalną / pierwotne zapalenie naczyń -> przekaż 1
        Jeśli lekarz opisze stan na tle infekcyjnym -> przekaż 2
        Jeśli lekarz opisze stan na tle nowotworowym -> przekaż 3
        
        ABSOLUTNY ZAKAZ HALUCYNACJI LICZB. Gdy użyjesz narzędzia 'oblicz_ryzyko', otrzymasz dokładne wyniki procentowe.
        W swojej odpowiedzi tekstowej MUSISZ przepisać te liczby dokładnie tak, jak zwróciło je narzędzie, z dokładnością do jednego miejsca po przecinku. 
        Nie wolno Ci wymyślać własnych statystyk."""
        self.messages = [SystemMessage(content=system_prompt)]

    def wydobadz_tekst(self, odpowiedz):
        if isinstance(odpowiedz.content, str):
            return odpowiedz.content
        elif isinstance(odpowiedz.content, list):
            for element in odpowiedz.content:
                if isinstance(element, dict) and element.get('type') == 'text':
                    return element.get('text')
        return "Błąd parsowania odpowiedzi modelu."

    def przetworz_wiadomosc(self, wiadomosc_lekarza: str) -> str:
        self.messages.append(HumanMessage(content=wiadomosc_lekarza))
        response = self.agent.invoke(self.messages)
        self.messages.append(response)
        
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call["name"] == "oblicz_ryzyko":
                    wynik = oblicz_ryzyko.invoke(tool_call["args"])
                    self.messages.append(ToolMessage(
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"],
                        content=str(wynik)
                    ))
            
            final_response = self.agent.invoke(self.messages)
            self.messages.append(final_response)
            
            return self.wydobadz_tekst(final_response)
        
        return self.wydobadz_tekst(response)
    def odtworz_historie_z_ui(self, historia_z_ui):
        system_msg = self.messages[0]
        self.messages = [system_msg]
        
        for msg in historia_z_ui:
            czysty_tekst = str(msg["content"]).strip() 
            
            if msg["role"] == "user":
                self.messages.append(HumanMessage(content=czysty_tekst))
            elif msg["role"] == "assistant":
                self.messages.append(AIMessage(content=czysty_tekst))