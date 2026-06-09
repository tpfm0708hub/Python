import os
import multiprocessing
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed

cl = multiprocessing.cpu_count() - 1

path_001 = r'D:/github/제6기이후'

df_list_001 = list(Path(path_001).rglob('*.sas7bdat'))

def read_sas_001(file_01):
    return pd.read_sas(file_01)

df_ls_001 = Parallel(n_jobs = cl)(delayed(read_sas_001)(file_01) for file_01 in df_list_001)

df_001 = pd.concat(df_ls_001, ignore_index = True, axis = 0)

df_002 = df_001[df_001['DI2_dg'].notna() &
                ~df_001['DI2_dg'].isin([8.0, 9.0])
                ]

df_003 = df_002[df_002['HE_chol'].notna() & df_002['HE_TG'].notna()]

df_003['cls_hchol'] = np.where(
    (df_003['HE_chol'] >= 240), 1, 0)

df_003['cls_htg'] = np.where(
    (df_003['HE_TG'] >= 200), 1, 0)

print(df_003['cls_hchol'].value_counts(normalize = True, dropna = False).sort_index())
print(df_003['cls_htg'].value_counts(normalize = True, dropna = False).sort_index())

print(df_003[df_003['DI2_dg'] == 1]['cls_hchol'].value_counts(normalize = True, dropna = False).sort_index())
print(df_003[df_003['DI2_dg'] == 1]['cls_htg'].value_counts(normalize = True, dropna = False).sort_index())
