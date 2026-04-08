import pandas as pd
import numpy as np

#  임의의 표본 500개 생성
idx_01=list(
    range(1,500+1))

#  주소구성: "수정구", "분당구", "중원구"
address_01=np.random.choice(
    ["수정구","분당구","중원구"],size=len(idx_01),replace=True
    )

#  수입범위: 240~500
income_01=np.random.choice(
    range(240,500+1),size=len(idx_01),replace=True
    )

df_01=pd.DataFrame({
    '순번':idx_01,
    '주소':address_01,
    '수입':income_01
    })
