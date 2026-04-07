import os
import pandas as pd

# d드라이브 내 "260403_파일출력.pkl" 불러오기
df_001 = pd.read_pickle(os.path.join('D:/','github','260403_파일출력.pkl'))

# 데이터 구조 확인
print(df_001.info())

# 결츨 미포함
print(df_001['주소'].value_counts())
#   주소
#   분당구    351
#   중원구    315
#   수정구    309
# 결측 포함
print(df_001['주소'].value_counts(dropna=False))
#   주소
#   분당구    351
#   중원구    315
#   수정구    309
#   NaN     25

#   '수입' 변수 결측 확인
print(df_001['수입'].isna().sum())
#   '수입' 변수 기술통계량 확인
print(df_001['수입'].describe())