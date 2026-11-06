# Laboratorio virtual de flotación

Pregunta: ¿puede un modelo estimar la sílice del concentrado antes de que llegue el laboratorio?

Lo probé con datos reales de una planta de flotación de hierro (dataset público de Kaggle, licencia CC0): variables de proceso cada 20 segundos y análisis de laboratorio cada hora, de marzo a septiembre de 2017. Entrené con el pasado y evalué en el último mes (16 ago – 9 sep 2017, 600 horas), que el modelo nunca vio.

## Resultados (retraso de laboratorio supuesto: 2 horas)

| Método | RMSE (% SiO₂) | R² |
|---|---|---|
| Decidir con el último análisis disponible | 0,93 | 0,41 |
| Solo variables de proceso | 1,22 | −0,03 |
| Laboratorio virtual (proceso + último análisis) | 0,86 | 0,49 |

- **Sin laboratorio, el modelo no sirve aquí.** Con validación temporal, las variables de proceso solas no superan al promedio.
- **Con el último análisis, baja entre 6 y 9 %** el error de decidir con el dato viejo, según cuánto tarde el laboratorio (1 a 4 horas en `resultados/retraso.csv`).
- **Ojo con los R² altos.** El mismo problema con validación aleatoria y usando el % de hierro del concentrado de la misma hora da R² 0,77. Eso es fuga de información, no capacidad predictiva.
- **El agente de turno** emite 21 avisos en el mes contra 33 del aviso con el último análisis (11 y 14 confirmados), pero cubre 11 de 19 eventos contra 15. Filtra ruido; no anticipa.

## Demo en línea

La carpeta `docs/` tiene la demo como una sola página (datos incluidos). Para publicarla en GitHub Pages: Settings → Pages → Deploy from a branch → rama `main`, carpeta `/docs`. Queda en `https://<tu-usuario>.github.io/lab-virtual-flotacion/`.

## Cómo reproducirlo

1. Descarga `MiningProcess_Flotation_Plant_Database.csv` desde Kaggle ("Quality Prediction in a Mining Process") y déjalo en `data/`.
2. `pip install -r requirements.txt`
3. `python preparar.py && python modelo.py && python agente.py && python exportar.py`

Corre en menos de un minuto en un notebook. Los resultados quedan en `resultados/`.

Para enviar avisos reales a Telegram: `TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... python agente.py --enviar 3`.

## Supuestos y límites

- El retraso del laboratorio (2 h) y el límite de 3,0 % de sílice son supuestos; los de esta planta no son públicos.
- Las leyes de alimentación se usan como disponibles en el momento.
- Las variables que "más se movieron" en cada aviso orientan dónde mirar; no son causas confirmadas.
- No es una planta chilena ni un caso de cliente.

Proyecto personal de Julián Neira Nova.
