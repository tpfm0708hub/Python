import os
import multiprocessing
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed

cl = multiprocessing.cpu_count() - 1

path_001 = r'd:/github'

df_list_001 = list(Path(path_001).glob('hn*.sas7bdat'))
#   rglob면 하위 영역의 패턴까지 확인!

def read_sas_001(file_01):
    return pd.read_sas(file_01)

df_ls_001 = Parallel(n_jobs = -1)(delayed(read_sas_001)(file_02) for file_02 in df_list_001)

df_001 = pd.concat(df_ls_001, ignore_index = True, axis = 0)

df_001 = df_001[df_001['age'] >= 20]

df_002 = df_001.copy()
df_002['age_group'] = np.select([
    (df_001['age'] >= 80), (df_001['age'] >= 60),
    (df_001['age'] >= 40), (df_001['age'] >= 20),
    ], [3, 2, 1, 0])

df_002['HE_ht'].describe()
df_002['HE_wt'].describe()

df_003 = df_002[df_002['HE_ht'].notna() &
                df_002['HE_wt'].notna()
                ]

df_003['set_bmi'] = df_002['HE_wt'] / (df_002['HE_ht'] / 100)**2

sum(df_003['set_bmi'] != df_003['HE_BMI'])
