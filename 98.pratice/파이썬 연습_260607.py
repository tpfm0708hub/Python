import os
import multiprocessing
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed

cl = multiprocessing.cpu_count() - 1

path_001 = r'D:/github/제6기이후'

df_list_001 = list(Path(path_001).rglob('hn*.sas7bdat'))

def read_sas_001(file_01):
    return pd.read_sas(file_01)

df_ls_001 = Parallel(n_jobs = cl)(delayed(read_sas_001)(file_01) for file_01 in df_list_001)

df_001 = pd.concat(df_ls_001, ignore_index = True, axis = 0)

df_001['DI2_dg'].value_counts(dropna=False).sort_index()

df_002 = df_001[df_001['DI2_dg'].notna() &
                ~df_001['DI2_dg'].isin([8.0, 9.0])
                ]

df_002 ['DI2_dg'].value_counts(dropna=False).sort_index()