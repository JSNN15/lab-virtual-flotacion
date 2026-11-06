"""Lee el CSV original (Kaggle, CC0) y lo agrega por hora: media y desviacion de cada variable."""
import pandas as pd
df = pd.read_csv('data/MiningProcess_Flotation_Plant_Database.csv', decimal=',', parse_dates=['date'])
df.groupby('date').agg(['mean', 'std']).to_pickle('data/hourly.pkl')
print('horas:', df.date.nunique())
