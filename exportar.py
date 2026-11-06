"""Genera los CSV que publica la demo, todos desde las salidas de exp2.py y agente.py."""
import json, pandas as pd
R = json.load(open('resultados/res_exp2.json')); SPEC = 3.0
s = pd.read_csv('resultados/out_D2.csv', index_col=0, parse_dates=True)
pd.DataFrame({'hora': s.index.strftime('%Y-%m-%d %H:%M'), 'real': s.real.round(3), 'lab_conocido': s.lab_conocido.round(3),
              'estimado': s.hibrido.round(3), 'solo_proceso': s.proceso.round(3)}).to_csv('resultados/serie.csv', index=False)
rows = [dict(retraso_h=int(k[2:]), ultimo_lab=v['persistencia']['RMSE'], lab_virtual=v['hibrido']['RMSE'],
             solo_proceso=v['solo_proceso']['RMSE']) for k, v in R.items() if k.startswith('D=')]
pd.DataFrame(rows).to_csv('resultados/retraso.csv', index=False)
pd.DataFrame([
    dict(orden=1, escenario='Validación aleatoria + % hierro del concentrado de la misma hora', r2=R['fuga_split_aleatorio_con_Fe_conc']['R2'], honesto='no'),
    dict(orden=2, escenario='Validación aleatoria, solo variables de proceso', r2=R['split_aleatorio_solo_proceso']['R2'], honesto='no'),
    dict(orden=3, escenario='Mes futuro, solo variables de proceso', r2=R['D=2']['solo_proceso']['R2'], honesto='sí'),
    dict(orden=4, escenario='Mes futuro, proceso + último laboratorio', r2=R['D=2']['hibrido']['R2'], honesto='sí'),
]).to_csv('resultados/validacion.csv', index=False)

def politica(serie, h=0.2):
    al, act = [], False
    for t, v in serie.items():
        if v > SPEC and not act: al.append(t)
        act = (v > SPEC) if not act else v > SPEC - h
    return al
real = s.real > SPEC; g = (real != real.shift()).cumsum()
ev = [gr.index for _, gr in real[real].groupby(g[real]) if len(gr) >= 2]
out = []
for nombre, col in [('Aviso con el último laboratorio', 'lab_conocido'), ('Aviso con el laboratorio virtual', 'hibrido')]:
    a = politica(s[col]); al = s[col] > SPEC
    out.append(dict(politica=nombre, avisos=len(a), confirmados=int(sum(s.real[t] > SPEC for t in a)),
                    eventos_con_aviso=int(sum(al[i].any() for i in ev)), eventos=len(ev)))
pd.DataFrame(out).to_csv('resultados/alertas.csv', index=False)
A = json.load(open('resultados/alertas.json'))['alertas']
pd.DataFrame([dict(hora=a['hora'][:16], estimado=a['estimado'], lab_conocido=a['lab_conocido'],
                   real=a['real_confirmado_despues'], texto=a['texto']) for a in A]).to_csv('resultados/mensajes.csv', index=False)
for f in ['retraso', 'validacion', 'alertas']: print(open(f'resultados/{f}.csv').read())
