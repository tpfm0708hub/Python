import os
import multiprocessing
import pandas as pd
from pathlib import Path
from joblib import Parallel, delayed#  ≒ doParallel, foreach

#  ≒ makeCluster(parallel::detectCores()-1)
cl = multiprocessing.cpu_count() - 1

path_001 = r'D:\github\제6기이후'

#  ≒ dir_ls(path_001, regexp = 'hn.*\\sas7dbat$)
df_list_001 = list(Path(path_001).rglob('hn*.sas7bdat'))

#  ≒ foreach() %dopar% { read_sas(f) }
def load_sas(f_01):
    #  ≒ haven::read_sas
    return pd.read_sas(f_01, format = 'sas7bdat', encoding=None)

#  ≒ foreach %dopar%
df_ls_001 = Parallel(n_jobs = cl)(delayed(load_sas)(f) for f in df_list_001)

#  ≒ bind_orws
df_001 = pd.concat(df_ls_001, ignore_index = True)


#   1) 고혈압 의산진단 여부 확인
df_001['DI1_dg'].value_counts(dropna=False).sort_index()
#0.0    51367
#1.0    17971
#8.0    15677
#9.0      896
#NaN     4056

df_002 = df_001[
    df_001['DI1_dg'].notna() &
    ~df_001['DI1_dg'].isin([8.0, 9.0])
    ]

df_002 ['DI1_dg'].value_counts(dropna=False).sort_index()
#0.0    51367
#1.0    17971
