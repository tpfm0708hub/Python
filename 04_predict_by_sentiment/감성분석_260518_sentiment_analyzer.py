import joblib
from kiwipiepy import Kiwi

class SentimentAnalyzer:
    def __init__(self, vectorizer_file, model_file):
        #   모델 로딩
        #   joblib: 파이썬에서 객체 저장
        #           직렬화
        self.__vertorizer = joblib.load(vectorizer_file)
        self.__sa_model = joblib.load(model_file)
        
        #   Kiwi 형태소 분석기 설정
        self.__kiwi = Kiwi()
        self.__stopwords = []
        
        #   ★. Vectorizer 기존 토크나이저 → korean_tokenizer로 교체
        self.__vertorizer.tokenizer = self.__korean_tokenizer
        
    def __korean_tokenizer(self, 본문):
        """Kiwi 형태소 분석기"""
        #   결측 예외처리
        if not 본문: return []
        
        #   ★. token 객체 리스트 반환
        tokens = self.__kiwi.tokenize(본문)
        
        #   Kiwi 품사 매핑
        #   명사: N으로 시작(NNG, NNP, NNB, NP, NR)
        #   동사: VV
        #   형용사: VA
        result = [
            token.form for token in tokens
            if (token.tag.startswith('N') or token.tag in ['VV', 'VA'])
            and token.form not in self.__stopwords
        ]
        return result
    
    def tokenizer(self, 본문):
        return self.__korean_tokenizer(본문)
    
    def analyze_sentiment(self, 본문):
        #   전처리 및 특정 벡터 추출(__korean_tokenizer 자동 호출)
        body_fv = self.__vertorizer.transform([본문])
        
        #   모델 예측
        result = self.__sa_model.predict(body_fv)
        
        show = '긍정' if result[0] >= 0.5 else '부정'
        return show
