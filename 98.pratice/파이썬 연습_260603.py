import os
import multiprocessing
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed

cl = multiprocessing.cpu_count() - 1

path_001 = r'D:/github/제6기이후'

df_list_001 = list(Path(path_001).rglob('hn*.sas7bdat'))

def load_sas(file_01):
    return pd.read_sas(file_01, format = 'sas7bdat', encoding = None)

df_ls_001 = Parallel(n_jobs = cl)(delayed(load_sas)(file_01) for file_01 in df_list_001)

df_001 = pd.concat(df_ls_001, axis = 0)

df_001['DI1_dg'].value_counts(dropna = False).sort_index()

df_002 = df_001[df_001['DI1_dg'].notna() &
                ~df_001['DI1_dg'].isin([8.0, 9.0])
                ]

df_003 = df_002.dropna(subset = ['HE_sbp2', 'HE_sbp3'])

df_003['cal_sbp'] = df_003[['HE_sbp2', 'HE_sbp3']].mean(axis = 1)
df_003['cal_dbp'] = df_003[['HE_dbp2', 'HE_dbp3']].mean(axis = 1)

df_003['BP_HT'] = np.select([
    (df_003['cal_sbp'] >= 140) | (df_003['cal_dbp'] >= 90),
    (df_003['cal_sbp'] >= 130) | (df_003['cal_dbp'] >= 80),
    (df_003['cal_sbp'] >= 120) & (df_003['cal_dbp'] < 80),
    (df_003['cal_sbp'] < 120)  & (df_003['cal_dbp'] < 80)
    ], [3, 2, 1, 0])

print(df_003['BP_HT'].value_counts(dropna = False).sort_index())