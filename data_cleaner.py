import pandas as pd
import numpy as np

INPUT_FILE = 'dane_med6P_SEL.csv'
OUTPUT_FILE = 'dane_med_CLN.csv'

def clean_data():
    
    df = pd.read_csv(INPUT_FILE, sep='|')
    print(f"Wczytano: {df.shape[0]} wierszy, {df.shape[1]} kolumn.")

    # Dializa
    # Zmiana z: -1-nie, 0-brak danych, 1-tak(stała), 2-przejściowa
    # Na: 0-nie, 1-stała, 2-przejściowa, <NA>-brak
    
    # Krok A: Mapowanie wartości logicznych
    # Zamieniamy 0 (Brak danych) na np.nan
    df['Dializa'] = df['Dializa'].replace(0, np.nan)
    # Zmiana -1 na 0 bo 0-nie to standard
    df['Dializa'] = df['Dializa'].replace(-1, 0)
    
   # Int64 pozwala na Nan
    df['Dializa'] = df['Dializa'].astype('Int64')
    
    print("Nowy rozkład 'Dializa' (0=Nie, 1=Stała, 2=Przejściowa):")
    print(df['Dializa'].value_counts(dropna=False).sort_index())

    # Powikłania
    # Zmiana z: 2-nie, 1-tak, 0/-1-brak danych (0 to brak wpisu)
    # Na: 0-nie, 1-tak, <NA>-brak
    
    powiklania_cols = [c for c in df.columns if 'Powiklania' in c]
    
    # Definiujemy mapowanie "śmieci" na <NA>
    # Wszystko co nie jest 1 (Tak) lub 2 (Nie) traktujemy jako brak danych
    nan_mapping = {-1: np.nan, 0: np.nan}
    
    # Definiujemy mapowanie wartości merytorycznych
    # 2 zamieniamy na 0 (Zdrowy), 1 zostaje 1 (Chory)
    value_mapping = {2: 0} 

    for col in powiklania_cols:
        # 1. Czyszczenie śmieci (-1 i 0 -> NaN)
        df[col] = df[col].replace(nan_mapping)
        
        # 2. Zmiana logiki (2 -> 0)
        df[col] = df[col].replace(value_mapping)
        
        # 3. Wymuszanie typ całkowity (Int64)
        df[col] = df[col].astype('Int64')
    
    if 'Powiklania_Nerki' in df.columns:
        print("Przykładowy rozkład 'Powiklania_Nerki':")
        print(df['Powiklania_Nerki'].value_counts(dropna=False).sort_index())

    # Duplikaty
    df = df.drop_duplicates()
    
    df.to_csv(OUTPUT_FILE, index=False, sep='|')
    
    print(f"\nZapisano plik: {OUTPUT_FILE}")
    
    # Szybki podgląd czy zniknęły kropki (np. 1.0 -> 1)
    print("Podgląd pierwszych 5 wierszy (Dializa i Nerki):")
    cols_preview = ['Dializa'] + [c for c in df.columns if 'Nerki' in c][:1]
    print(df[cols_preview].head())

if __name__ == "__main__":
    clean_data()