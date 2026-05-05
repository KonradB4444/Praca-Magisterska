import pandas as pd
import xgboost as xgb

df = pd.read_csv('dane_med_CLN.csv', sep='|')

cechy_zgon_lista = [
    'Wiek',
    'Liczba_Zajetych_Narzadow', 
    'Zaostrz_Wymagajace_OIT', 
    'Manifestacja_Pokarmowy', 
    'Manifestacja_Zajecie_CSN', 
    'Manifestacja_Moczowo-Plciowy', 
    'Plazmaferezy', 
    'Manifestacja_Wzrok', 
    'Manifestacja_Skora', 
    'Manifestacja_Neurologiczny', 
    'Manifestacja_Sercowo-Naczyniowy', 
    'Opoznienie_Rozpoznia', 
    'Manifestacja_Miesno-Szkiel'
]

cechy_dializa_lista = [
    'Wiek',
    'Kreatynina', 
    'Plazmaferezy', 
    'Leczenie_Plazmaferezy', 
    'Rozpoznanie', 
    'Przebieg_scalony', 
    'Manifestacja_Nerki', 
    'Liczba_Zajetych_Narzadow'
]

brakujace_zgon = [c for c in cechy_zgon_lista if c not in df.columns]
brakujace_dializa = [c for c in cechy_dializa_lista if c not in df.columns]

if brakujace_zgon or brakujace_dializa:
    print(f"Brakuje kolumn w CSV")
    if brakujace_zgon: print(f"Brakuje dla Zgonu: {brakujace_zgon}")
    if brakujace_dializa: print(f"Brakuje dla Dializy: {brakujace_dializa}")
    exit()

df_zgon = df.dropna(subset=['Zgon']).copy()
X_zgon = df_zgon[cechy_zgon_lista]
y_zgon = df_zgon['Zgon']

model_zgon = xgb.XGBClassifier(
    use_label_encoder=False, 
    eval_metric='logloss', 
    random_state=42
)
model_zgon.fit(X_zgon, y_zgon)
model_zgon.save_model("xgboost_zgon.json")

df_dial = df.dropna(subset=['Dializa']).copy()
y_dial = df_dial['Dializa'].apply(lambda x: 1 if x > 0 else 0)
X_dial = df_dial[cechy_dializa_lista]

model_dializa = xgb.XGBClassifier(
    use_label_encoder=False, 
    eval_metric='logloss', 
    random_state=42
)
model_dializa.fit(X_dial, y_dial)
model_dializa.save_model("xgboost_dializa.json")