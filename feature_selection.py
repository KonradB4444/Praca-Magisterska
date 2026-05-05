import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_selection import mutual_info_classif
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler

file_path = 'dane_med_CLN.csv'
df = pd.read_csv(file_path, sep='|')

def run_consensus_selection(X, y, top_n=15):
    X_num = X.select_dtypes(include=[np.number])

    imputer = SimpleImputer(strategy='median')
    X_clean = pd.DataFrame(imputer.fit_transform(X_num), columns=X_num.columns)

    gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
    gb.fit(X_clean, y)
    imp_gb = gb.feature_importances_

    imp_mi = mutual_info_classif(X_clean, y, discrete_features='auto', random_state=42)

    imp_corr = X_clean.corrwith(y).abs().values

    results = pd.DataFrame({
        'Feature': X_num.columns,
        'GB_Imp': imp_gb,
        'Mutual_Info': imp_mi,
        'Correlation': imp_corr
    })
    
    scaler = MinMaxScaler()
    results[['GB_Imp', 'Mutual_Info', 'Correlation']] = scaler.fit_transform(results[['GB_Imp', 'Mutual_Info', 'Correlation']])

    results['Score'] = results[['GB_Imp', 'Mutual_Info', 'Correlation']].mean(axis=1)
    results = results.sort_values(by='Score', ascending=False).reset_index(drop=True)
    
    print(results[['Feature', 'Score']].head(top_n))
    return results

cols_to_drop_base = ['Kod', 'A-DATA', 'E-DATAUR']
existing_drop = [c for c in cols_to_drop_base if c in df.columns]

df_zgon = df.copy()
y_zgon = df_zgon['Zgon']
X_zgon = df_zgon.drop(columns=existing_drop + ['Zgon', 'Dializa'])

results_zgon = run_consensus_selection(X_zgon, y_zgon, "Zgon", top_n=15)

df_dial = df.dropna(subset=['Dializa']).copy()
y_dial = df_dial['Dializa'].apply(lambda x: 1 if x > 0 else 0)
X_dial = df_dial.drop(columns=existing_drop + ['Zgon', 'Dializa'])

results_dial = run_consensus_selection(X_dial, y_dial, "Dializa", top_n=15)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

sns.barplot(x='Score', y='Feature', data=results_zgon.head(15), ax=ax1, palette='Reds_r')
ax1.set_title('Top 15 Cech - Ryzyko ZGONU (Metoda Hybrydowa)')
ax1.set_xlabel('Wskaźnik Ważności (Consensus Score)')

sns.barplot(x='Score', y='Feature', data=results_dial.head(15), ax=ax2, palette='Blues_r')
ax2.set_title('Top 15 Cech - Ryzyko DIALIZY (Metoda Hybrydowa)')
ax2.set_xlabel('Wskaźnik Ważności (Consensus Score)')

plt.tight_layout()
plt.savefig('feature_selection.png')
print("\nZapisano wykres: feature_selection.png")