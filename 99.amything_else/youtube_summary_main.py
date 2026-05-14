import os
import re
import yaml
import base64
import sqlite3
import logging
import requests
import feedparser

from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 한국 시간대 전역 설정
KST = timezone(timedelta(hours=9))


# =========================================================
# 1. 설정 및 환경 관리 (응집도: 환경 셋업 전담)
# =========================================================
class EnvironmentManager:
    @staticmethod
    def load_config(config_path="D:/youtube_summary/config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @staticmethod
    def setup_directories_and_logger(config):
        paths = config["paths"]
        for key in ["base_dir", "transcript_dir", "summary_dir"]:
            Path(paths[key]).mkdir(parents=True, exist_ok=True)
        
        Path(paths["log_file"]).parent.mkdir(parents=True, exist_ok=True)
        Path(paths["credentials_file"]).parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            filename=paths["log_file"],
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            encoding="utf-8"
        )
        
        root_logger = logging.getLogger("")
        if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            root_logger.addHandler(console)

    @staticmethod
    def save_text(text, save_dir, filename):
        save_path = Path(save_dir) / filename
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)
        return str(save_path)


# =========================================================
# 2. 데이터베이스 관리 (응집도: DB I/O 전담)
# =========================================================
class VideoDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS processed_videos (
                    video_id TEXT PRIMARY KEY,
                    channel_name TEXT,
                    title TEXT,
                    url TEXT,
                    published TEXT,
                    status TEXT,
                    processed_at TEXT
                )
            """)
            cur.execute("PRAGMA table_info(processed_videos)")
            columns = [row[1] for row in cur.fetchall()]
            if "channel_name" not in columns:
                cur.execute("ALTER TABLE processed_videos ADD COLUMN channel_name TEXT")
            conn.commit()

    def is_processed(self, video_id):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM processed_videos WHERE video_id = ?", (video_id,))
            return cur.fetchone()[0] > 0

    def mark_processed(self, video_id, channel_name, title, url, published, status):
        processed_at_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO processed_videos
                (video_id, channel_name, title, url, published, status, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (video_id, channel_name, title, url, published, status, processed_at_kst))
            conn.commit()


# =========================================================
# 3. 유튜브 데이터 수집 (응집도: RSS 피드 파싱 및 필터링 전담)
# =========================================================
class YouTubeFetcher:
    def __init__(self, config):
        self.config = config

    def get_latest_videos(self, channel_info):
        channel_id = channel_info.get("channel_id", "").strip()
        channel_url = channel_info.get("channel_url", "").strip()
        channel_name = channel_info.get("channel_display_name", "알 수 없는 채널")

        if not channel_id:
            channel_id = self._extract_channel_id(channel_url)

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)

        videos = []
        for entry in feed.entries:
            video_url = entry.link
            videos.append({
                "video_id": video_url.split("v=")[-1].split("&")[0],
                "title": entry.title,
                "url": video_url,
                "published": getattr(entry, "published", ""),
                "channel_display_name": channel_name
            })
        return videos

    def _extract_channel_id(self, channel_url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(channel_url, headers=headers, timeout=20)
        res.raise_for_status()
        
        patterns = [
            r'"channelId":"(UC[^"]+)"',
            r'"externalId":"(UC[^"]+)"',
            r'<meta itemprop="channelId" content="(UC[^"]+)">'
        ]
        for pattern in patterns:
            match = re.search(pattern, res.text)
            if match:
                return match.group(1)
        raise ValueError("채널 ID 자동 추출 실패")

    def filter_video(self, video):
        # 1. Shorts / Live 필터
        title_lower = video["title"].lower()
        url_lower = video["url"].lower()
        
        if self.config["youtube"].get("exclude_shorts", True):
            if any(k in title_lower or k in url_lower for k in ["#shorts", "shorts", "쇼츠"]):
                return False, "쇼츠 제외"

        if self.config["youtube"].get("exclude_live_replay", True):
            if any(k in title_lower for k in ["live", "라이브", "실시간", "생방송"]):
                return False, "라이브 다시보기 제외"

        # 2. 업로드 날짜 필터
        days = self.config["youtube"].get("published_after_days", None)
        if days is not None:
            pub_text = video.get("published", "")
            if not pub_text:
                return False, "업로드일 파싱 실패"
            try:
                published_dt = datetime.fromisoformat(pub_text.replace("Z", "+00:00"))
                if published_dt.astimezone(KST) < datetime.now(KST) - timedelta(days=days):
                    return False, f"작성일 기준 제외"
            except Exception:
                return False, "업로드일 파싱 실패"

        return True, "통과"


# =========================================================
# 4. 자막 추출 (응집도: 유튜브 자막 API 전담)
# =========================================================
class TranscriptExtractor:
    @staticmethod
    def get_korean_transcript(video_id):
        try:
            fetched = YouTubeTranscriptApi().fetch(video_id, languages=["ko"])
            text = "\n".join(s.text.replace("\n", " ").strip() for s in fetched if s.text and s.text.strip())
            if not text.strip():
                return None, "요약 불가(자막 없음)"
            return text, "자막 추출 성공"
        except NoTranscriptFound:
            return None, "요약 불가(한국어 자막 없음)"
        except TranscriptsDisabled:
            return None, "요약 불가(자막 비활성화)"
        except VideoUnavailable:
            return None, "요약 불가(영상 접근 불가)"
        except Exception as e:
            return None, f"요약 불가(자막 추출 오류: {e})"


# =========================================================
# 5. LLM 요약 (응집도: Ollama API 통신 전담)
# =========================================================
class OllamaSummarizer:
    def __init__(self, config):
        self.api_url = config["ollama"]["api_url"]
        self.model = config["ollama"]["model"]

    def summarize(self, title, text):
        prompt = f"""다음은 유튜브 영상의 한국어 자막입니다.
영상 제목: {title}

요청사항:
- 전체 내용을 한국어로 요약해 주세요.
- 각 항목을 5줄 내외로 작성해 주세요.
- 광고 문구처럼 쓰지 말고, 핵심 내용을 객관적으로 정리해 주세요.
- 번호는 1. 2. 3. 4. 5. 형식으로 붙여 주세요.

자막:
{text}"""
        payload = {"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}}
        res = requests.post(self.api_url, json=payload, timeout=600)
        res.raise_for_status()
        summary = res.json().get("response", "").strip()
        if not summary:
            raise ValueError("Ollama 응답이 비어 있습니다.")
        return summary


# =========================================================
# 6. 알림/이메일 (응집도: Gmail API 전담)
# =========================================================
class GmailNotifier:
    def __init__(self, config):
        self.config = config
        self.service = self._get_service()

    def _get_service(self):
        paths = self.config["paths"]
        creds = None
        if os.path.exists(paths["token_file"]):
            creds = Credentials.from_authorized_user_file(paths["token_file"], ["https://www.googleapis.com/auth/gmail.send"])
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(paths["credentials_file"], ["https://www.googleapis.com/auth/gmail.send"])
                creds = flow.run_local_server(port=0)
            with open(paths["token_file"], "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    def make_email_subject(self, channel_name, video_title):
        """
        이메일 제목에 config의 prefix 대신 channel_name이 들어가도록 변경되었습니다.
        """
        date_tag = datetime.now(KST).strftime("%y%m%d")
        safe_title = re.sub(r'[\\/:*?"<>|]', " ", video_title)
        safe_title = re.sub(r"\s+", " ", safe_title).strip()
        
        # 형식: 채널명_날짜_영상제목
        subject = f"{channel_name}_{date_tag}_{safe_title}"
        return subject[:180]

    def make_email_body(self, video, summary, transcript_status):
        channel_name = video.get("channel_display_name", "알 수 없는 채널")
        # 날짜 포맷팅 간소화 (에러 방지 차원에서 try-except 처리)
        pub_text = video.get("published", "")
        try:
            published_kst = datetime.fromisoformat(pub_text.replace("Z", "+00:00")).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")
        except Exception:
            published_kst = pub_text or "업로드일 확인 불가"

        return f"""유튜브 AI 요약 결과입니다.

[채널]
{channel_name}

[영상 제목]
{video["title"]}

[영상 URL]
{video["url"]}

[업로드일]
{published_kst}

[자막 상태]
{transcript_status}

[5줄 요약]
{summary}

--
본 메일은 Python + Ollama + Gmail API 기반 자동 요약 프로그램으로 발송되었습니다.
"""

    def send_email(self, subject, body):
        message = MIMEText(body, "plain", "utf-8")
        message["To"] = self.config["email"]["receiver"]
        message["From"] = self.config["email"]["sender"]
        message["Subject"] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        self.service.users().messages().send(userId="me", body={"raw": raw_message}).execute()


# =========================================================
# 7. 파이프라인 제어 (결합도 최소화: 각 모듈을 조립하여 실행)
# =========================================================
class YouTubeSummaryPipeline:
    def __init__(self, config):
        self.config = config
        self.db = VideoDatabase(config["paths"]["database_file"])
        self.fetcher = YouTubeFetcher(config)
        self.extractor = TranscriptExtractor()
        self.summarizer = OllamaSummarizer(config)
        self.notifier = GmailNotifier(config)

    def run(self):
        logging.info("유튜브 요약 파이프라인 시작")
        channels = self.config["youtube"].get("channels", [])
        all_videos = []

        # 1. 영상 수집
        for ch in channels:
            try:
                videos = self.fetcher.get_latest_videos(ch)
                all_videos.extend(videos)
            except Exception as e:
                logging.exception(f"[{ch.get('channel_display_name')}] 수집 실패: {e}")

        # 2. 과거 영상부터 처리 (업로드일 오름차순 정렬)
        def sort_key(v):
            try: return datetime.fromisoformat(v.get("published", "").replace("Z", "+00:00"))
            except: return datetime.min.replace(tzinfo=timezone.utc)
            
        all_videos.sort(key=sort_key)

        # 3. 파이프라인 실행
        max_videos = self.config["youtube"].get("max_videos_per_run", 10)
        processed_count = 0

        for video in all_videos:
            if processed_count >= max_videos:
                break

            video_id = video["video_id"]
            title = video["title"]
            channel_name = video["channel_display_name"]

            # DB 중복 체크
            if self.db.is_processed(video_id):
                continue

            # 필터링 (쇼츠, 날짜 등)
            is_valid, reason = self.fetcher.filter_video(video)
            if not is_valid:
                self.db.mark_processed(video_id, channel_name, title, video["url"], video["published"], reason)
                continue

            logging.info(f"[{channel_name}] 신규 영상 처리 시작: {title}")

            # 자막 추출
            transcript_text, status = self.extractor.get_korean_transcript(video_id)
            
            if not transcript_text:
                summary = status
            else:
                # 텍스트 저장
                safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", video_id)
                EnvironmentManager.save_text(transcript_text, self.config["paths"]["transcript_dir"], f"{safe_id}_transcript.txt")
                
                # 요약
                try:
                    summary = self.summarizer.summarize(title, transcript_text)
                    EnvironmentManager.save_text(summary, self.config["paths"]["summary_dir"], f"{safe_id}_summary.txt")
                    status = "요약 완료"
                except Exception as e:
                    summary = f"요약 불가(오류: {e})"
                    status = "요약 실패"

            # 이메일 발송
            subject = self.notifier.make_email_subject(channel_name, title)
            body = self.notifier.make_email_body(video, summary, status)
            
            try:
                self.notifier.send_email(subject, body)
                self.db.mark_processed(video_id, channel_name, title, video["url"], video["published"], status)
                processed_count += 1
            except Exception as e:
                logging.exception(f"[{channel_name}] 메일 발송 실패: {e}")

        logging.info("유튜브 요약 파이프라인 종료")


# =========================================================
# 실행 엔트리포인트
# =========================================================
if __name__ == "__main__":
    config_data = EnvironmentManager.load_config()
    EnvironmentManager.setup_directories_and_logger(config_data)
    
    pipeline = YouTubeSummaryPipeline(config_data)
    pipeline.run()