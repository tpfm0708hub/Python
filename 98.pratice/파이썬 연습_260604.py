import os
import multiprocessing
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed

cl = multiprocessing.cpu_count() - 1

path_001 = r'D:/github/제6기이후'

df_list_001 = list(Path(path_001).rglob('hn*.sas7bdat'))

def read_sas(file_01):
    return pd.read_sas(file_01, format = 'sas7bdat', encoding = None)

df_ls_001 = Parallel(n_jobs = cl)(delayed(read_sas)(file_01) for file_01 in df_list_001)

df_001 = pd.concat(df_ls_001, ignore_index = True)

df_001['DE1_dg'].value_counts(dropna = False).sort_index()
#DE1_dg
#0.0    71024
#1.0     7422
#8.0     6547
#9.0      918
#NaN     4056

df_002 = df_001[
    df_001['DI1_dg'].notna() &
    ~df_001['DI1_dg'].isin([8.0, 9.0])
    ]

df_002['DI1_dg'].value_counts(dropna = False).sort_index()
#DI1_dg
#0.0    51367
#1.0    17971