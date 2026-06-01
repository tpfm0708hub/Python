import os
import multiprocessing
import pandas as pd
from pathlib import Path
from joblib import Parallel, delayed

#  ≒ makeCluster(parallel::detectCores()-1)
cl = multiprocessing.cpu_count() - 1

path_001 = r'D:/github/제6기이후'

#  ≒ dir_ls(path_001, regexp = 'hn.*\\sas7dbat$)
df_list_001 = list(Path(path_001).rglob('hn*.sas7bdat'))

#  ≒ foreach() %dopar% { read_sas(f) }
def load_sas(f_01):
    #  ≒ haven::read_sas
    return pd.read_sas(f_01, format = 'sas7bdat', encoding = None)    

#  ≒ foreach %dopar%
df_ls_001 = Parallel(n_jobs = cl)(delayed(load_sas)(f_01) for f_01 in df_list_001)

#  ≒ bind_orws
df_001 = pd.concat(df_ls_001, ignore_index = True)

print(len(df_001))
#   89967
print(df_001['HE_sbp2'].describe())
#count    78799.000000
#mean       118.465323
#std         16.791141
#min         62.000000
#25%        106.000000
#50%        116.000000
#75%        128.000000
#max        246.000000

df_002 = df_001[df_001['HE_sbp2'].notna()]
print(len(df_002))
#   78799