import os
import pandas as pd

# d드라이브 내 "260403_파일출력.pkl" 불러오기
df_001 = pd.read_pickle(os.path.join('D:/','github','260403_파일출력.pkl'))

# 데이터 구조 확인
print(df_001.info())