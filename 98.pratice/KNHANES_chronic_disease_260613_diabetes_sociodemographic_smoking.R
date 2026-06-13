rm(list=ls())
library(fs)# dir_ls()
library(psych)# describe()
library(dplyr)
library(haven)
library(doParallel)#  foreach()
# 활용자료: "국민건강영양조사 제9기(2022-2024)
# URL: https://knhanes.kdca.go.kr/knhanes/rawDataDwnld/rawDataDwnld.do

# 병렬처리 코어 설정
cl <- makeCluster(detectCores() - 1)
registerDoParallel(cl)

# 파일 경로 설정
path_001 <- 'D:/github'

# 경로 내 파일 형식 지정
df_list_001 <- dir_ls(path = path_001, regexp = 'hn.*\\.sas7bdat$')

# 경로 내 해당 파일 불러온 후 병합
df_001 <- foreach(f = df_list_001, .combine = bind_rows, .packages = c('haven')) %dopar% {
  df_01 <- read_sas(f)
  return(df_01)
}

# 병렬처리 종료
stopCluster(cl)

# 20세 이상 성인 대상 분석 진행
df_001 <- df_001 %>% filter(age >= 20)

# 연령집단 분류 기준: 20~39세, 40~59세, 60~79세, 80세 이상
# 기준 자료: Cha, J. E., & Yun, S. N. (2015). The comparison of health behaviors, use of health services, and health expenditures among diabetic patients according to the practice of exercise. Journal of Korean Academy of Community Health Nursing, 26(1), 31-41.
df_002 <- df_001 %>% mutate(
  age_group = case_when(
    age >= 80 ~ 3,
    age >= 60 ~ 2,
    age >= 40 ~ 1,
    age >= 20 ~ 0,
    TRUE      ~ 99
  )
)

# 신장 및 체중 결측 제거
df_003 <- df_002 %>% filter(!is.na(HE_ht) & !is.na(HE_wt))

# BMI(set_bmi) 지표 생성
# 참고자료: 국민건강영양조사 제9기(2022-2024) 원시자료 이용지침서
df_003 <- df_003 %>% mutate(set_bmi = HE_wt / (HE_ht / 100)^2)

# 흡연여부 변수 생성
# 기준 자료: Lee, D. Y. (2024). Prevalence and risk factors of osteoarthritis in Korea: a cross-sectional study. Medicina, 60(4), 665.
# 평생 일반담배(궐련) 흡연 여부(BS1_1) 및 현재 일반담배(궐련) 흡연 여부(BS3_1)
# 궐련형 전자담배 평생사용여부(BS12_37) 및 궐련형 전자담배 현재사용여부(BS12_47)
# 액상형 전자담배 평생사용여부(BS12_1) 및 액상형 전자담배 현재(최근 1달)사용여부(BS12_2)

# 평생 일반담배(궐련) 흡연 여부 범주별 빈도 확인
df_003 %>% count(BS1_1)
#  BS1_1     n  내용
#1     1   341  5갑(100개비) 미만
#2     2  6019  5갑(100개비) 이상
#3     3 10069  피운 적 없음
#4     9   388  모름, 무응답
#5    NA     5

# 궐련형 전자담배 평생사용여부 범주별 빈도 확인
df_003 %>% count(BS12_37)
#  BS12_37     n  내용
#1       1  1463  예
#2       2 14967  아니요
#3       9   387  모름, 무응답
#4      NA     5

# 액상형 전자담배 평생사용여부 범주별 빈도 확인
df_003 %>% count(BS12_1)
#  BS12_1     n 내용
#1      1  1194 예
#2      2 15236 아니요
#3      9   387 모름, 무응답
#4     NA     5

# 담배 평생사용여부 무응답 및 결측 제거
df_004 <- df_003 %>% filter(
  BS1_1 != 9 & BS12_37 != 9 & BS12_1 != 9 &
  !is.na(BS1_1) & !is.na(BS12_37) & !is.na(BS12_1) 
  )

# 현재 일반담배(궐련) 흡연 여부 범주별 빈도 확인
df_004 %>% count(BS3_1)
#  BS3_1     n  내용
#1     1  2136  매일피움
#2     2   327  가끔피움
#3     3  3897  과거엔 피웠으나, 현재 피우지 않음
#4     8 10069  피운적 없음

# 궐련형 전자담배 현재사용여부 범주별 빈도 확인
df_004 %>% count(BS12_47)
#  BS12_47     n  내용
#1       1   495  매일피움
#2       2   147  가끔피움
#3       3   821  과거엔 피웠으나, 현재 피우지 않음  
#4       8 14966  피운적 없음

# 액상형 전자담배 현재(최근 1달)사용여부 범주별 빈도 확인
df_004 %>% count(BS12_2)
#  BS12_2     n 내용
#1      1   379 예
#2      2   815 아니요
#3      8 15235 모름, 무응답

# 현재 흡연여부(current_smoke) 변수 생성
df_004 <- df_004 %>% mutate(
  current_smoking = case_when(
    # 현재흡연자(2): 담배관련 '매일피움'이거나 '가끔피움', 현재 사용여부 '네' 응답에 해당
    BS3_1 %in% c(1, 2) | BS12_47 %in% c(1, 2) | BS12_2 == 1~ 2,
    # 과거흡연자(1): 담배관련 '과거엔 피웠으나, 현재 피우지 않음' 응답에 해당
    BS3_1 == 3 | BS12_47 == 3 ~ 1,
    # 비흡연자(0): 담배 관련 '피운적 없음' 및 현재 사용여부 '아니요' 응답에 해당
    BS3_1 == 8 | BS12_47 == 8 | BS12_2 %in% c(2, 8) ~ 0,
    TRUE ~ NA)
  )

# 현재 흡연여부 범주별 빈도 확인
df_004 %>% count(current_smoking)
#  current_smoke     n  내용
#1             0 10034  비흡연자
#2             1  3488  과거흡연자
#3             2  2907  현재흡연자