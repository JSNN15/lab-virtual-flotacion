"""Laboratorio virtual: compara estimadores de % silice con validacion temporal, demuestra la fuga de datos y mide el efecto del retraso del laboratorio."""
import json, sys, warnings
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.metrics import mean_absolute_error as MAE, mean_squared_error, r2_score
warnings.filterwarnings('ignore')
SPEC = 3.0
H = pd.read_pickle('data/hourly.pkl')
mean = H.xs('mean', axis=1, level=1).asfreq('h'); std = H.xs('std', axis=1, level=1).asfreq('h')
proc = [c for c in mean.columns if c not in ('% Iron Concentrate', '% Silica Concentrate', '% Iron Feed', '% Silica Feed')]
y = mean['% Silica Concentrate']
P = dict(objective='regression_l1', learning_rate=0.03, num_leaves=31, min_data_in_leaf=40, feature_fraction=0.7,
         bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, verbose=-1, seed=7)
def rmse(a, b): return mean_squared_error(a, b) ** .5
def m(yt, yp): return dict(MAE=round(MAE(yt, yp), 3), RMSE=round(rmse(yt, yp), 3), R2=round(r2_score(yt, yp), 3))

def feats(D):
    X = pd.DataFrame(index=mean.index)
    for c in proc:
        X[c] = mean[c]; X[c + ' sd'] = std[c]; X[c + ' L1'] = mean[c].shift(1); X[c + ' L2'] = mean[c].shift(2)
        X[c + ' dD'] = mean[c] - mean[c].shift(D)            # cambio desde la ultima muestra con lab conocido
    X['% Iron Feed'] = mean['% Iron Feed']; X['% Silica Feed'] = mean['% Silica Feed']
    X['amina_per_pulp'] = mean['Amina Flow'] / mean['Ore Pulp Flow']; X['starch_per_pulp'] = mean['Starch Flow'] / mean['Ore Pulp Flow']
    L = pd.DataFrame({'si_known': y.shift(D), 'si_known2': y.shift(D + 1), 'fe_known': mean['% Iron Concentrate'].shift(D)}, index=mean.index)
    return X, L

def masks(X, L):
    ok = (X.index >= '2017-03-29 12:00') & y.notna() & L.si_known.notna() & L.si_known2.notna()
    tr = ok & (X.index < '2017-08-01'); va = ok & (X.index >= '2017-08-01') & (X.index < '2017-08-16'); te = ok & (X.index >= '2017-08-16')
    return tr, va, te

def fit(F, t, tr, va):
    mm = lgb.train(P, lgb.Dataset(F[tr], t[tr]), 3000, valid_sets=[lgb.Dataset(F[va], t[va])], callbacks=[lgb.early_stopping(150, verbose=False)])
    return lgb.train(P, lgb.Dataset(F[tr | va], t[tr | va]), mm.best_iteration)

def det(yt, pred):
    real = yt > SPEC; al = pred > SPEC
    tp = int((real & al).sum()); fp = int((~real & al).sum()); fn = int((real & ~al).sum())
    grp = (real != real.shift()).cumsum()
    starts = [g.index[0] for _, g in real[real].groupby(grp[real])]
    first = [s for s in starts]
    caught0 = sum(bool(al.get(s, False)) for s in first)
    # horas hasta la primera alarma dentro de cada evento
    lags = []
    for _, g in real[real].groupby(grp[real]):
        a = al[g.index]; lags.append(int(np.argmax(a.values)) if a.any() else None)
    return dict(precision=round(tp / max(tp + fp, 1), 2), recall=round(tp / max(tp + fn, 1), 2), fp_dia=round(fp / (len(yt) / 24), 2),
                eventos=len(starts), detectados_1a_hora=caught0, detectados_alguna_vez=sum(l is not None for l in lags))

R = {}
# 1) Demostracion de fuga: split aleatorio + % Iron Concentrate del mismo momento
X, L = feats(2); tr, va, te = masks(X, L)
ok = tr | va | te
Xl = X.copy(); Xl['% Iron Concentrate (MISMA hora)'] = mean['% Iron Concentrate']
rng = np.random.RandomState(0); idx = np.where(ok)[0]; rng.shuffle(idx); cut = int(len(idx) * .8)
rtr = np.zeros(len(X), bool); rtr[idx[:cut]] = True; rte = np.zeros(len(X), bool); rte[idx[cut:]] = True
mleak = lgb.train(P, lgb.Dataset(Xl[rtr], y[rtr]), 1500)
R['fuga_split_aleatorio_con_Fe_conc'] = m(y[rte], mleak.predict(Xl[rte]))
m2 = lgb.train(P, lgb.Dataset(X[rtr], y[rtr]), 1500)
R['split_aleatorio_solo_proceso'] = m(y[rte], m2.predict(X[rte]))

for D in [1, 2, 3, 4]:
    X, L = feats(D); tr, va, te = masks(X, L); yt = y[te]; r = {}
    r['persistencia'] = m(yt, L.si_known[te]); r['det_persistencia'] = det(yt, L.si_known[te])
    mp = fit(X, y, tr, va); pp = pd.Series(mp.predict(X), X.index)
    r['solo_proceso'] = m(yt, pp[te])
    # actualizacion de sesgo clasica de soft sensor: corrige con el ultimo lab conocido
    bias = (L.si_known - pp.shift(D)); pb = pp + bias.rolling(3, min_periods=1).mean()
    r['proceso_con_sesgo'] = m(yt, pb[te])
    # modelo de residuo: predice cuanto cambiara la silice desde el ultimo lab conocido
    XL = X.join(L); t = y - L.si_known
    mr = fit(XL, t, tr, va); pr = pd.Series(mr.predict(XL), X.index) + L.si_known
    r['residuo'] = m(yt, pr[te]); r['det_residuo'] = det(yt, pr[te])
    mh = fit(XL, y, tr, va); ph = pd.Series(mh.predict(XL), X.index)
    r['hibrido'] = m(yt, ph[te]); r['det_hibrido'] = det(yt, ph[te])
    R[f'D={D}'] = r
    pd.DataFrame({'real': yt, 'lab_conocido': L.si_known[te], 'hibrido': ph[te], 'residuo': pr[te], 'proceso': pp[te]}).to_csv(f'resultados/out_D{D}.csv')
print(json.dumps(R, ensure_ascii=False, indent=1))
json.dump(R, open('resultados/res_exp2.json', 'w'), ensure_ascii=False, indent=1)
