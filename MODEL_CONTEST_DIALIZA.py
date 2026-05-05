import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from sklearn.ensemble import GradientBoostingClassifier, AdaBoostClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier

file_path = 'dane_med_CLN.csv'
df = pd.read_csv(file_path, sep='|')

df_clean = df.dropna(subset=['Dializa']).copy()
print(f"Liczba próbek po usunięciu braków w celu: {len(df_clean)}")

df_clean['Target'] = df_clean['Dializa'].apply(lambda x: 1 if x > 0 else 0)

counts = df_clean['Target'].value_counts()
print(f"Rozkład klasy docelowej (0=Nie, 1=Tak): \n{counts}")
print(f"Procent dializowanych: {counts[1] / len(df_clean) * 100:.2f}%")

cols_to_drop = ['Kod', 'A-DATA', 'E-DATAUR', 'Zgon', 'Dializa', 'Target']
cols_to_drop = [c for c in cols_to_drop if c in df_clean.columns]

X = df_clean.drop(columns=cols_to_drop)
y = df_clean['Target']

X = X.select_dtypes(include=[np.number])

models = [
    ('XGBoost', GradientBoostingClassifier(n_estimators=100, random_state=42)),
    ('AdaBoost', AdaBoostClassifier(n_estimators=100, random_state=42)),
    ('NeuralNet', MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=1000, random_state=42)),
    ('DecisionTree', DecisionTreeClassifier(max_depth=5, random_state=42))
]

results = []
names = []
scoring_metric = 'roc_auc'

print(f"\nRozpoczynam walidację krzyżową (5-fold CV, Metric: {scoring_metric})...")

for name, model in models:
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')), 
        ('scaler', StandardScaler()), 
        ('model', model)
    ])

    kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_val_score(pipeline, X, y, cv=kfold, scoring=scoring_metric)
    
    results.append(cv_results)
    names.append(name)
    print(f" -> {name}: {cv_results.mean():.4f} (+/- {cv_results.std():.4f})")

plt.figure(figsize=(10, 6))
plt.boxplot(results, labels=names, patch_artist=True)
plt.title(f'Benchmark Modeli - DIALIZA (Metryka: ROC AUC)')
plt.ylabel('ROC AUC Score')
plt.grid(True, axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('dializa_benchmark.png')

print(f"\nZapisano wykres: dializa_benchmark.png")