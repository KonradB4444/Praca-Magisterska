import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

file_path = 'dane_med_CLN.csv'
df = pd.read_csv(file_path, sep='|')

target = 'Zgon'
cols_to_drop = ['Kod', 'A-DATA', 'E-DATAUR', 'Zgon', 'Dializa']
cols_to_drop = [c for c in cols_to_drop if c in df.columns]

X = df.drop(columns=cols_to_drop)
y = df[target]

X = X.select_dtypes(include=[np.number])

models = [
    ('LogReg', LogisticRegression(max_iter=1000, random_state=42)),
    ('KNN', KNeighborsClassifier(n_neighbors=5)), # Distance based
    ('CART', DecisionTreeClassifier(random_state=42, max_depth=5)), # Rule based (RST-like)
    ('SVM', SVC(probability=True, random_state=42)), # Vector based
    ('RF', RandomForestClassifier(n_estimators=100, random_state=42)), # Ensemble Bagging
    ('XGB', GradientBoostingClassifier(n_estimators=100, random_state=42)) # Ensemble Boosting (sklearn implementation for simplicity)
]

results = []
names = []
scoring_metric = 'roc_auc'

print(f"--- TURNIEJ MODELI (Metryka: {scoring_metric}) ---")
print(f"Liczba cech: {X.shape[1]}")

for name, model in models:
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')), # Handle NaNs
        ('scaler', StandardScaler()), # Normalize features
        ('model', model)
    ])

    kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_val_score(pipeline, X, y, cv=kfold, scoring=scoring_metric)
    
    results.append(cv_results)
    names.append(name)
    print(f"{name}: {cv_results.mean():.4f} (+/- {cv_results.std():.4f})")

plt.figure(figsize=(10, 6))
plt.boxplot(results, labels=names, patch_artist=True)
plt.title(f'Porównanie Modeli (Benchmark) - Metryka: {scoring_metric}')
plt.ylabel('ROC AUC Score')
plt.grid(True, axis='y', linestyle='--', alpha=0.7)
plt.savefig('model_benchmark.png')