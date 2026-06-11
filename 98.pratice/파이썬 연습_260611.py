import os
import multiprocessing
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed

cl = multiprocessing.cpu_count() - 1

path_001 = r'D:/github'

df_list_001 = list(Path(path_001).rglob('hn*.sas7bdat'))

def read_sas_001(file_01):
    return pd.read_sas(file_01)

df_ls_001 = Parallel(n_jobs = -1)(delayed(read_sas_001)(file_01) for file_01 in df_list_001)

df_001 = pd.concat(df_ls_001, ignore_index = True, axis = 0)

df_001['age'].describe()

df_001 = df_001[df_001['age'] >= 20]

df_002 = df_001.copy()
df_002['age_group'] = np.select([
    (df_001['age'] >= 80), (df_001['age'] >= 60),
    (df_001['age'] >= 40), (df_001['age'] >= 20),
    ], [3, 2, 1, 0])

df_002['age_group'].value_counts(dropna=False).sort_index()

df_002[df_002['DI1_dg']==1]['age_group'].value_counts(dropna=False).sort_index()
