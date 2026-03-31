import pandas as pd
import numpy as np

#  임의의 표본 500개 생성
idx_001=list(
    range(1,500+1))

# seed값 설정
np.random.seed(1234)

#  주소구성: "수정구", "분당구", "중원구"
address_001=np.random.choice(
    ["수정구","분당구","중원구"],size=len(idx_001),replace=True
    )

# seed값 설정
np.random.seed(2345)

#  수입범위: 240~500
income_001=np.random.choice(
    range(240,500+1),size=len(idx_001),replace=True
    )

df_001=pd.DataFrame({
    '순번':idx_001,
    '주소':address_001,
    '수입':income_001
    })

#   결측삽입 함수 생성
##  매개변수로 데이터 및 설정 열 입력
def na_001(db_01,col_01):
    ##  새로운 데이터에 결과 지정
    db_02=db_01.copy()
    np.random.seed(1234)
    ##  설정 열 내부구조는 열 이름, 비율 순으로 지정
    for col_02,rate_02 in col_01:
        ##  db_01 내 행 갯수 연산
        na_01=len(db_01)
        ##  각 열에 따른 비율이 반영된 값 연산
        na_02=int(na_01*rate_02)
        ## 결측이 삽입된 행 생성 
        na_03=np.random.choice(db_01.index,size=na_02,replace=False)
        ##  각 열에 결측이 삽입된 행 반영
        db_02.loc[na_03,col_02]=np.nan
    return db_02
    
#   df_001 내 열 이름 list 생성
col_001=df_001.columns.tolist()

print(col_001)
#   출력결과: ['순번', '주소', '수입']

col_002=[
    # 주소: 25개 행(500*5%)에 결측 삽입
    (col_001[1],0.05),
    # 수입: 30개 행(500*6%)에 결측 삽입
    (col_001[2],0.06)
    ]

#   기존 데이터에서 결측삽입 함수 반영한 데이터 생성
df_002=na_001(df_001,col_002)

# df_01과 동일한 구조 생성
tbl_001=pd.DataFrame({
    '순번':range(501,1000+1),
    '주소':address_001,
    '수입':income_001
    })

df_003=pd.concat([df_002,tbl_001],axis=0)

tbl_001=pd.DataFrame({
    '순번':range(501,1000+1),
    '주소':address_001,
    '수입':income_001
    })

np.random.seed(3456)

# df_03 행수 만큼의 성별 열 생성
tbl_002=np.random.choice(
    ['남성','여성'],size=len(df_003),replace=True
    )

# 새로운 데이터 프레임으로 복사
df_004=df_003.copy()
# 성별 열 생성 후 값 대입
df_004['성별']=tbl_002
