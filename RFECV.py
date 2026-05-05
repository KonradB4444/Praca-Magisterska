import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_selection import RFECV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.impute import SimpleImputer

file_path = 'dane_med_CLN.csv'
df = pd.read_csv(file_path, sep='|')

def run_rfecv_analysis(X, y, target_name):

    
    X_num = X.select_dtypes(include=[np.number])
    imputer = SimpleImputer(strategy='median')
    X_clean = pd.DataFrame(imputer.fit_transform(X_num), columns=X_num.columns)
    
    clf = GradientBoostingClassifier(n_estimators=50, random_state=42)
    
    rfecv = RFECV(estimator=clf, step=1, cv=StratifiedKFold(5), scoring='roc_auc', n_jobs=-1)
    rfecv.fit(X_clean, y)
    
    print(f"Optymalna liczba cech: {rfecv.n_features_}")
    print(f"Maksymalny wynik (ROC AUC): {rfecv.cv_results_['mean_test_score'][rfecv.n_features_ - 1]:.4f}")
    
    return rfecv

df_zgon = df.copy()
y_zgon = df_zgon['Zgon']
X_zgon = df_zgon.drop(columns=['Kod', 'A-DATA', 'E-DATAUR', 'Zgon', 'Dializa'], errors='ignore')

rfecv_zgon = run_rfecv_analysis(X_zgon, y_zgon, "Zgon")

df_dial = df.dropna(subset=['Dializa']).copy()
y_dial = df_dial['Dializa'].apply(lambda x: 1 if x > 0 else 0)
X_dial = df_dial.drop(columns=['Kod', 'A-DATA', 'E-DATAUR', 'Zgon', 'Dializa'], errors='ignore')

rfecv_dial = run_rfecv_analysis(X_dial, y_dial, "Dializa")

plt.figure(figsize=(12, 6))

plt.subplot(1, 2, 1)
n_scores_zgon = len(rfecv_zgon.cv_results_['mean_test_score'])
plt.xlabel("Liczba Cech")
plt.ylabel("ROC AUC")
plt.plot(range(1, n_scores_zgon + 1), rfecv_zgon.cv_results_['mean_test_score'])
plt.title(f"Zgon: Optymalnie {rfecv_zgon.n_features_} cech")
plt.axvline(x=12, color='r', linestyle='--', label='Nasze odcięcie (12)')
plt.legend()
plt.grid()

plt.subplot(1, 2, 2)
n_scores_dial = len(rfecv_dial.cv_results_['mean_test_score'])
plt.xlabel("Liczba Cech")
plt.ylabel("ROC AUC")
plt.plot(range(1, n_scores_dial + 1), rfecv_dial.cv_results_['mean_test_score'])
plt.title(f"Dializa: Optymalnie {rfecv_dial.n_features_} cech")
plt.axvline(x=7, color='r', linestyle='--', label='Nasze odcięcie (7)')
plt.legend()
plt.grid()

plt.tight_layout()
plt.savefig('rfecv_analysis.png')

print("\nAnaliza Porównawcza (Manual vs Auto)")
score_at_12_zgon = rfecv_zgon.cv_results_['mean_test_score'][11]
score_max_zgon = max(rfecv_zgon.cv_results_['mean_test_score'])
print(f"ZGON: Wynik przy 12 cechach: {score_at_12_zgon:.4f} vs Max: {score_max_zgon:.4f}")

score_at_7_dial = rfecv_dial.cv_results_['mean_test_score'][6]
score_max_dial = max(rfecv_dial.cv_results_['mean_test_score'])
print(f"DIALIZA: Wynik przy 7 cechach: {score_at_7_dial:.4f} vs Max: {score_max_dial:.4f}")