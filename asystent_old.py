import os
import pandas as pd
import xgboost as xgb
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

#os.environ["OPENAI_API_KEY"] = ""

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

    df_zgon = pd.DataFrame([{
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
    }])

    df_dial = pd.DataFrame([{
        'Wiek': wiek,
        'Kreatynina': kreatynina,
        'Plazmaferezy': plazmaferezy,
        'Leczenie_Plazmaferezy': leczenie_plazmaferezy,
        'Rozpoznanie': rozpoznanie,
        'Przebieg_scalony': przebieg_scalony,
        'Manifestacja_Nerki': manifestacja_nerki,
        'Liczba_Zajetych_Narzadow': liczba_zajetych_narzadow
    }])

    print("\nDEBUG: ")
    print(df_zgon.iloc[0])

    # Predykcja prawdopodobieństwa (indeks [1] to klasa pozytywna)
    ryzyko_zgon = 100 - (model_zgon.predict_proba(df_zgon)[0][1] * 100)
    ryzyko_dializa = model_dializa.predict_proba(df_dial)[0][1] * 100

    return (f"Obliczenia XGBoost zakończone. "
            f"Ryzyko zgonu wynosi {ryzyko_zgon:.1f}%. "
            f"Ryzyko konieczności dializy wynosi {ryzyko_dializa:.1f}%.")

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_z_narzedziami = llm.bind_tools([oblicz_ryzyko])

system_prompt = """Jesteś inteligentnym Asystentem Medycznym.
Twoim celem jest zebranie 18 parametrów od lekarza w celu obliczenia ryzyka klinicznego.
Zadawaj pytania naturalnie, po 2 lub 3 naraz, aby nie przytłoczyć użytkownika.
Jeśli użytkownik poda informacje ogólnikowo, samodzielnie zmapuj je na format liczbowy/binarny.

Pamiętaj, by wyciągnąć informacje o wieku, kreatyninie, liczbie zajętych narządów, pobycie na OIT, plazmaferezie, opóźnieniu rozpoznania,
rozpoznaniu, przebiegu scalonym oraz manifestacjach (pokarmowej, CSN, moczowo-płciowej, wzrokowej, 
skórnej, neurologicznej, sercowo-naczyniowej, mięśniowo-szkieletowej, nerkowej) i leczeniu plazmaferezą.

Gdy uznasz, że zebrałeś wszystkie niezbędne parametry z listy narzędzia, WYWOŁAJ FUNKCJĘ oblicz_ryzyko.
Po otrzymaniu wyniku z funkcji, przedstaw go lekarzowi w profesjonalny sposób."""

messages = [SystemMessage(content=system_prompt)]

print("\nSTART ASYSTENTA (Wpisz 'wyjście' aby zakończyć)")
print("Asystent: Dzień dobry, proszę opisać przypadek pacjenta.")

while True:
    user_input = input("\nLekarz: ")
    if user_input.lower() == 'wyjście':
        break

    messages.append(HumanMessage(content=user_input))
    
    # Wywołanie LLM
    response = llm_z_narzedziami.invoke(messages)
    messages.append(response)

    def wydobadz_tekst(odpowiedz):
        if isinstance(odpowiedz.content, str):
            return odpowiedz.content
        elif isinstance(odpowiedz.content, list):
            for element in odpowiedz.content:
                if isinstance(element, dict) and element.get('type') == 'text':
                    return element.get('text')
        return "Błąd parsowania odpowiedzi modelu."

    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "oblicz_ryzyko":
                # Uruchomienie XGBoosta
                wynik_ml = oblicz_ryzyko.invoke(tool_call["args"])
                
                # Przekazanie wyniku z powrotem do LLMa
                messages.append(ToolMessage(
                    tool_call_id=tool_call["id"],
                    name=tool_call["name"],
                    content=str(wynik_ml)
                ))
                
                final_response = llm_z_narzedziami.invoke(messages)
                messages.append(final_response)
                
                print(f"\nAsystent: {wydobadz_tekst(final_response)}")
    else:
        # LLM wciąż zbiera dane, zadaje kolejne pytanie
        print(f"\nAsystent: {wydobadz_tekst(response)}")


# dziwne zjawisko, z jakiegoś powodu modele openAI (gpt-4o, gtp-4o-mini itp.) mają fluksuację inteligencji, tzn. przy jednych testach tymi samymi promptami łatwo
# jest go zbić z system prompta, a za drugim trzyma się go dobrze. Z tego powodu postanowiłem zrezygnować z modelów openAI