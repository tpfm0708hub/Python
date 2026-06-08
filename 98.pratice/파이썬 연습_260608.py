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
    return pd.read_sas(file_01, format = 'sas7bdat', encoding = None)

df_lr_001 = Parallel(n_jobs = -1)(delayed(read_sas_001)(file_01) for file_01 in df_list_001)

df_001 = pd.concat(df_lr_001, axis = 0, ignore_index = True)

df_002 = df_001[df_001['DI2_dg'].notna() &
                ~df_001['DI2_dg'].isin([8.0, 9.0])]

print(df_002['HE_chol'].describe())
#count    66391.000000
#mean       189.519453
#std         38.304935
#min         66.000000
#25%        163.000000
#50%        188.000000
#75%        214.000000
#max        525.000000

print(df_002['HE_TG'].describe())
#count    66391.000000
#mean       131.930744
#std        104.734104
#min         11.000000
#25%         74.000000
#50%        106.000000
#75%        157.000000
#max       3367.000000

df_003 = df_002.dropna(subset = ['HE_chol', 'HE_TG'])

print(df_003[['HE_chol', 'HE_TG']].isnull().sum())
#HE_chol    0
#HE_TG      0
#dtype: int64