import yfinance as yf
import pandas as pd
import os

class StockDataFetcher:
    """주식 및 지수 데이터를 수집하는 모듈 (높은 응집도)"""
    
    @staticmethod
    def fetch_daily_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        특정 종목의 일별 데이터를 수집하여 원본(Raw) 상태로 반환합니다.
        결측치 처리 등의 가공은 수행하지 않습니다.
        """
        print(f"[{ticker}] 데이터를 {start_date}부터 {end_date}까지 수집 중...")
        
        # yfinance를 통한 데이터 다운로드
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            print(f"경고: [{ticker}] 해당 기간의 데이터가 존재하지 않거나 수집에 실패했습니다.")
            
        return data


class DataExporter:
    """데이터를 특정 포맷으로 저장하는 모듈 (높은 응집도)"""
    
    @staticmethod
    def save_to_csv(df: pd.DataFrame, file_path: str) -> None:
        """
        데이터프레임을 CSV 파일로 저장합니다.
        """
        if df.empty:
            print(f"저장할 데이터가 없어 작업을 건너뜁니다: {file_path}")
            return
        
        # 저장할 디렉토리가 없다면 자동 생성
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # 한글 엑셀 환경을 고려하여 utf-8-sig 인코딩 사용
        df.to_csv(file_path, encoding='utf-8-sig')
        print(f"데이터가 성공적으로 저장되었습니다: {file_path}")


def main():
    """
    모듈 간 결합도를 낮추고, 확장성을 고려한 메인 파이프라인
    """
    # 1. 데이터 수집 범위 및 조건 설정 (확장성 고려)
    # 딕셔너리 형태로 관리하여 추후 분석 대상 종목을 쉽게 추가할 수 있습니다.
    target_tickers = {
        "KOSPI": "^KS11",
        # 향후 확장을 위한 예시 (주석 해제 시 즉시 동작)
        # "KOSDAQ": "^KQ11",
        # "SAMSUNG_ELEC": "005930.KS" 
    }
    
    # 직접 설정 가능한 조회 구간
    start_date = "2025-12-22"
    end_date = "2026-05-15"
    
    # 저장될 폴더명 설정
    output_dir = r"C:\Users\SAMSUNG\Desktop\yhfinance_crawl" 
    
    # 클래스 인스턴스화
    fetcher = StockDataFetcher()
    exporter = DataExporter()
    
    # 2. 데이터 처리 루프
    for name, ticker in target_tickers.items():
        # [데이터 수집] 모듈 호출 (저장 방식에 대해 전혀 알지 못함)
        raw_df = fetcher.fetch_daily_data(
            ticker=ticker, 
            start_date=start_date, 
            end_date=end_date
        )
        
        # [데이터 저장] 모듈 호출 (데이터의 출처에 대해 전혀 알지 못함)
        if not raw_df.empty:
            file_name = f"{name}_raw_data_{start_date}_{end_date}.csv"
            file_path = os.path.join(output_dir, file_name)
            
            exporter.save_to_csv(df=raw_df, file_path=file_path)
            print("-" * 50)

if __name__ == "__main__":
    main()