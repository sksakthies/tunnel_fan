import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import silhouette_score
from sklearn.ensemble import IsolationForest
from scipy.stats import ks_2samp
import joblib
import pickle

# ── STEP 1: LOAD MODEL ───────────────────────────────────
try:
    iso_forest = joblib.load('isolation_model.pkl')
    print(" Model loaded successfully")
except:
    with open('isolation_model.pkl', 'rb') as f:
        iso_forest = pickle.load(f)
    print(" Model loaded via pickle")

# ── STEP 2: LOAD YOUR DATA ───────────────────────────────
# Replace this with your actual data loading
# Example:
# import pandas as pd
# df = pd.read_csv('your_data.csv')
# X_test = df.values

# ── STEP 3: EVALUATION FUNCTION ─────────────────────────
def evaluate_isolation_forest(model, X_test):
    print("=" * 55)
    print("   ISOLATION FOREST — UNSUPERVISED EVALUATION")
    print("=" * 55)

    predictions = model.predict(X_test)
    scores      = model.score_samples(X_test)

    normal_scores  = scores[predictions == 1]
    anomaly_scores = scores[predictions == -1]

    # METHOD 1: KS Test
    print("\n METHOD 1: Score Separation (KS Test)")
    if len(anomaly_scores) > 0:
        ks_stat, p_value = ks_2samp(normal_scores, anomaly_scores)
        print(f"   KS Statistic : {ks_stat:.4f}  (closer to 1 = better)")
        print(f"   P-Value      : {p_value:.6f}  (< 0.05 = significant)")
        if ks_stat > 0.5 and p_value < 0.05:
            print("   Strong separation")
        elif ks_stat > 0.3:
            print("   Moderate separation")
        else:
            print("   Weak separation")
    else:
        print("    No anomalies detected — lower contamination")

    # METHOD 2: Score Statistics
    print("\n📌 METHOD 2: Score Statistics")
    print(f"   Normal  — Mean: {normal_scores.mean():.4f} | Std: {normal_scores.std():.4f}")
    if len(anomaly_scores) > 0:
        print(f"   Anomaly — Mean: {anomaly_scores.mean():.4f} | Std: {anomaly_scores.std():.4f}")
        gap = normal_scores.mean() - anomaly_scores.mean()
        print(f"   Score Gap : {gap:.4f}  (larger = better)")
        if gap > 0.1:
            print("    Good score gap")
        else:
            print("    Small score gap — consider retuning")

    # METHOD 3: Silhouette Score
    print("\n📌 METHOD 3: Silhouette Score")
    if len(np.unique(predictions)) > 1:
        sil_score = silhouette_score(X_test, predictions,
                                     sample_size=min(5000, len(X_test)))
        print(f"   Silhouette Score: {sil_score:.4f}")
        if sil_score > 0.5:
            print("   Good separation")
        elif sil_score > 0.2:
            print("    Moderate separation")
        else:
            print("   Poor separation")
    else:
        print("   Only one class — adjust contamination")

    # METHOD 4: Contamination Sensitivity
    print("\n📌 METHOD 4: Contamination Sensitivity")
    print(f"   {'Contamination':<20} {'Anomalies':<20} {'Rate'}")
    print(f"   {'-'*45}")
    for c in [0.01, 0.05, 0.10, 0.15, 0.20]:
        tmp = IsolationForest(n_estimators=model.n_estimators,
                              contamination=c, random_state=42)
        tmp.fit(X_test)
        tmp_preds = tmp.predict(X_test)
        n_anom = (tmp_preds == -1).sum()
        print(f"   {c:<20} {n_anom:<20} {n_anom/len(X_test):.2%}")

    # METHOD 5: Plots
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))

    axes[0].hist(normal_scores,  bins=40, alpha=0.6, color='steelblue', label='Normal')
    axes[0].hist(anomaly_scores, bins=40, alpha=0.6, color='tomato',    label='Anomaly')
    axes[0].axvline(model.threshold_, color='black', linestyle='--',
                    label=f'Threshold: {model.threshold_:.3f}')
    axes[0].set_title('Score Distribution')
    axes[0].legend()

    axes[1].boxplot([normal_scores, anomaly_scores],
                    labels=['Normal', 'Anomaly'], patch_artist=True)
    axes[1].set_title('Score Boxplot')

    colors = ['tomato' if p == -1 else 'steelblue' for p in predictions]
    axes[2].scatter(range(len(scores)), scores, c=colors, s=5, alpha=0.5)
    axes[2].axhline(model.threshold_, color='black', linestyle='--')
    axes[2].set_title('Score per Sample')

    plt.suptitle('Isolation Forest — Unsupervised Evaluation', fontweight='bold')
    plt.tight_layout()
    plt.show()

    # SUMMARY
    print("\n" + "=" * 55)
    print("   SUMMARY")
    print("=" * 55)
    print(f"   Total Samples  : {len(X_test)}")
    print(f"   Normal Points  : {(predictions == 1).sum()}")
    print(f"   Anomalies      : {(predictions == -1).sum()}")
    print(f"   Anomaly Rate   : {(predictions == -1).mean():.2%}")
    print("=" * 55)

# ── RUN ──────────────────────────────────────────────────
evaluate_isolation_forest(iso_forest, X_test)  # fixed variable name
