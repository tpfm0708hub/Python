import os
import multiprocessing
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed

cl = multiprocessing.cpu_count() - 1

path_001 = r'D:/github'

df_list_001 = list(Path(path_001).glob('hn*.sas7bdat'))

def read_sas_001(file_01):
    return pd.read_sas(file_01)

df_ls_001 = Parallel(n_jobs = -1)(delayed(read_sas_001)(file_02) for file_02 in df_list_001)

df_001 = pd.concat(df_ls_001, ignore_index = True, axis = 0)

df_001 = df_001[df_001['age'] >= 20]

df_002 = df_001.copy()
df_002['age_group'] = np.select([
    (df_002['age']>=80),(df_002['age']>=60),
    (df_002['age']>=40),(df_002['age']>=20)],
    [3, 2, 1, 0])

df_003 = df_002[df_002['HE_wt'].notna() &
                df_002['HE_ht'].notna()
                ]

df_003['set_bmi'] = df_002['HE_ht'] / (df_002['HE_wt'] / 100)**2

print(df_003['BS1_1'].value_counts(dropna = False).sort_index())
print(df_003['BS12_37'].value_counts(dropna = False).sort_index())
print(df_003['BS12_1'].value_counts(dropna = False).sort_index())

df_004 = df_003[(df_003['BS1_1'] != 9) & (df_003['BS12_37'] != 9) & (df_003['BS12_1'] != 9) &
                (df_003['BS1_1'].notna()) & (df_003['BS12_37'].notna()) & (df_003['BS12_1'].notna())
                ]

print(df_003['BS3_1'].value_counts(dropna = False).sort_index())
print(df_003['BS12_47'].value_counts(dropna = False).sort_index())
print(df_003['BS12_2'].value_counts(dropna = False).sort_index())

df_004['current_smoking'] = np.select([
    (df_004['BS3_1'].isin([1, 2]))|(df_004['BS12_47'].isin([1, 2]))|(df_004['BS12_2'] == 1),
    (df_004['BS3_1'] == 3) | (df_004['BS12_47'] == 3),
    (df_004['BS3_1'] == 8) | (df_004['BS12_47'] == 8) | (df_004['BS12_2'].isin([2, 8]))
    ], [2, 1, 0], default = np.nan)

print(df_004['current_smoking'].value_counts(dropna = False).sort_index())