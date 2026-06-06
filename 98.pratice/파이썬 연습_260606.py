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
    return pd.read_sas(file_01, format = 'sas7bdat', encoding = None)

df_ls_001 = Parallel(n_jobs = cl)(delayed(read_sas_001)(file_01) for file_01 in df_list_001)
    
df_001 = pd.concat(df_ls_001, axis = 0, ignore_index = True)

df_002 = df_001[df_001['DE1_dg'].notna() &
                ~ df_001['DE1_dg'].isin([8.0, 9.0])                 
                ]

df_003 = df_002.dropna(subset = ['HE_glu', 'HE_HbA1c'])

df_003['BS_BG'] = np.select([
    (df_003['HE_glu'] >= 126) | (df_003['HE_HbA1c'] >= 6.5),
    (df_003['HE_glu'] >= 100) | (df_003['HE_HbA1c'] >= 5.7),
    (df_003['HE_glu'] < 100)  | (df_003['HE_HbA1c'] < 5.7)
    ],[2, 1, 0])

print(df_003['BS_BG'].value_counts(normalize = True, dropna = False).sort_index())

print(df_003[df_003['DE1_dg'] == 1]['BS_BG'].value_counts(normalize = True, dropna = False).sort_index())
