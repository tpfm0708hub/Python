import os
import multiprocessing
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed

cl = multiprocessing.cpu_count() - 1

path_001 = 'd:/github'

df_list_001 = list(Path(path_001).glob('hn*.sas7bdat'))

def read_sas_001(file_01):
    return pd.read_sas(file_01)

df_ls_001 = Parallel(n_jobs = -1)(delayed(read_sas_001)(file_02) for file_02 in df_list_001)

df_001 = pd.concat(df_ls_001, ignore_index = True, axis = 0)

df_001 = df_001[df_001['age'] >= 20]

df_002 = df_001.copy()

df_002['age_group'] = np.select([
    (df_002['age']>=80),(df_002['age']>=60),
    (df_002['age']>=40),(df_002['age']>=20)
    ], [3, 2, 1, 0], default = 99)

df_003 = df_002[df_002['HE_ht'].notna() & df_002['HE_wt'].notna()]

df_003['set_bmi'] = df_003['HE_wt'] / (df_003['HE_ht'] / 100) ** 2

df_004 = df_003[(df_003['BS1_1'] != 9) & (df_003['BS12_37'] != 9) & (df_003['BS12_1'] != 9) &
                df_003['BS1_1'].notna() & df_003['BS12_37'].notna() & df_003['BS12_1'].notna()
                ]

df_004['current_smoking'] = np.select([
    (df_004['BS3_1'].isin([1, 2])) | (df_004['BS12_47'].isin([1, 2])) | (df_004['BS12_2'] == 1),
    (df_004['BS3_1'] == 3) | (df_004['BS12_47'] == 3),
    (df_004['BS3_1'].isin([1, 2])) | (df_004['BS12_47'].isin([1, 2])) | (df_004['BS12_2'] == 1)
    ], [2, 1, 0], default = np.nan)

print(df_004['BD1'].value_counts(dropna=False).sort_index())
print(df_004['BD1_11'].value_counts(dropna=False).sort_index())

df_005 = df_004[(df_004['BD1_11'] != 9)]

df_005['current_drinking'] = np.select([
    (df_005['BD1_11'].isin([3, 4, 5, 6])),
    (df_005['BD1_11'].isin([1, 2, 8]))
    ], [1, 0], default = np.nan)

print(df_005['current_drinking'].value_counts(dropna = False).sort_index())