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

df_lr_001 = Parallel(n_jobs = cl)(delayed(read_sas_001)(file_01) for file_01 in df_list_001)
df_001 = pd.concat(df_lr_001, axis = 0, ignore_index = True)

#df_001['DE1_dg'].value_counts(dropna = False).sort_index()

df_002 = df_001.copy()
df_002['DE1_dg'] = df_001[df_001['DE1_dg'].notna() &
                          ~df_001['DE1_dg'].isin([8.0, 9.0])
                          ]

print(len(df_002))
#   89967
print(df_002['HE_glu'].describe())
#count    74181.000000
#mean       100.540758
#std         22.930377
#min         40.000000
#25%         89.000000
#50%         95.000000
#75%        104.000000
#max        553.000000
#Name: HE_glu, dtype: float64

print(df_002['HE_HbA1c'].describe())
#count    74021.000000
#mean         5.708138
#std          0.787884
#min          3.100000
#25%          5.300000
#50%          5.500000
#75%          5.900000
#max         17.600000
#Name: HE_HbA1c, dtype: float64

df_002 = df_002[df_002['HE_glu'].notna() &
                df_002['HE_HbA1c'].notna()                
                ]
print(len(df_002))
#   74008