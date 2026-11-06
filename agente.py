"""Agente de turno: recorre hora a hora el periodo de prueba (como si fuera en vivo),
compara la estimacion del laboratorio virtual con la especificacion y redacta el aviso
para el jefe de turno, con las variables de proceso que mas se movieron.

Uso:  python agente.py            -> simula y guarda alertas en resultados/alertas.json
      TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... python agente.py --enviar 3   -> envia las 3 primeras a Telegram
"""
import json, os, sys, urllib.parse, urllib.request
import pandas as pd

SPEC = 3.0          # % SiO2 en concentrado (umbral ilustrativo)
D = 2               # horas que tarda el laboratorio
est = pd.read_csv(f'resultados/out_D{D}.csv', index_col=0, parse_dates=True)
H = pd.read_pickle('data/hourly.pkl')
mean = H.xs('mean', axis=1, level=1).asfreq('h')
NOMBRES = {'Starch Flow': 'Flujo de almidón', 'Amina Flow': 'Flujo de amina', 'Ore Pulp Flow': 'Flujo de pulpa',
           'Ore Pulp pH': 'pH de pulpa', 'Ore Pulp Density': 'Densidad de pulpa'}
proc = [c for c in mean.columns if c not in ('% Iron Concentrate', '% Silica Concentrate', '% Iron Feed', '% Silica Feed')]
z = (mean[proc] - mean[proc].rolling(24, min_periods=12).mean()) / mean[proc].rolling(24, min_periods=12).std()

def nombre(c):
    if c in NOMBRES: return NOMBRES[c]
    n = c.split()[2]; return ('Aire columna ' if 'Air' in c else 'Nivel columna ') + n

def mensaje(t, r, prev):
    mov = z.loc[t].abs().sort_values(ascending=False).head(3)
    lineas = [f"• {nombre(c)}: {'↑' if z.loc[t, c] > 0 else '↓'} {abs(z.loc[t, c]):.1f} desv. vs últimas 24 h" for c in mov.index]
    tend = '↑ subiendo' if r.hibrido > prev else '↓ bajando'
    return (f"⚠️ Sílice estimada sobre especificación — {t:%d-%m %H:%M}\n"
            f"Estimación ahora: {r.hibrido:.2f}% SiO₂ ({tend}) · límite {SPEC:.1f}%\n"
            f"Último laboratorio disponible (de hace {D} h): {r.lab_conocido:.2f}%\n"
            f"Lo que más se movió esta hora:\n" + "\n".join(lineas) +
            "\nNo es una causa confirmada: es dónde mirar primero.")

alertas, activo, prev = [], False, est.hibrido.iloc[0]
for t, r in est.iterrows():
    sobre = r.hibrido > SPEC
    if sobre and not activo:           # avisa al entrar en zona fuera de especificacion, no cada hora
        alertas.append(dict(hora=str(t), estimado=round(float(r.hibrido), 2), lab_conocido=round(float(r.lab_conocido), 2),
                            real_confirmado_despues=round(float(r.real), 2), texto=mensaje(t, r, prev)))
    activo = sobre if not activo else r.hibrido > SPEC - 0.2      # histeresis para no repetir avisos
    prev = r.hibrido

conf = int(sum(a['real_confirmado_despues'] > SPEC for a in alertas))
resumen = dict(alertas=len(alertas), dias=round(len(est) / 24, 1), confirmadas_por_laboratorio=conf)
json.dump(dict(resumen=resumen, alertas=alertas), open('resultados/alertas.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(resumen, ensure_ascii=False)); print(alertas[0]['texto'] if alertas else 'sin alertas')

if '--enviar' in sys.argv:
    n = int(sys.argv[sys.argv.index('--enviar') + 1]); tok, chat = os.environ['TELEGRAM_TOKEN'], os.environ['TELEGRAM_CHAT_ID']
    for a in alertas[:n]:
        data = urllib.parse.urlencode({'chat_id': chat, 'text': a['texto']}).encode()
        urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data=data, timeout=15)
    print(f'enviadas {n}')
