# =========================================================
# youtube_summary.py
# 역할:
#   1. 유튜브 RSS 수집
#   2. 영상 필터링
#   3. 자막 추출
#   4. 유튜브 요약 프롬프트 생성
#   5. 처리 이력 DB 관리
#   6. 이메일 제목/본문 구성
#   7. 전체 파이프라인 실행
# =========================================================

import re
import sqlite3
import logging
import requests
import feedparser

from pathlib import Path
from datetime import datetime, timezone, timedelta

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

from common_utils import (
    KST,
    CommonManager,
    OllamaClient,
    GmailClient
)


class VideoDatabase:
    """
    유튜브 영상 처리 이력 DB 관리 클래스입니다.

    DB는 프로젝트별로 따로 관리하는 것이 좋기 때문에
    공통 모듈이 아니라 유튜브 프로젝트 내부에 둡니다.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
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

    def is_processed(self, video_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM processed_videos WHERE video_id = ?",
                (video_id,)
            )
            return cur.fetchone()[0] > 0

    def mark_processed(
        self,
        video_id: str,
        channel_name: str,
        title: str,
        url: str,
        published: str,
        status: str
    ) -> None:
        processed_at_kst = CommonManager.now_kst_string()

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            cur.execute("""
                INSERT OR REPLACE INTO processed_videos
                (video_id, channel_name, title, url, published, status, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                video_id,
                channel_name,
                title,
                url,
                published,
                status,
                processed_at_kst
            ))

            conn.commit()


class YouTubeFetcher:
    """
    유튜브 RSS 수집 및 영상 필터링 클래스입니다.
    """

    def __init__(self, config: dict):
        self.config = config
        self.youtube_config = config.get("youtube", {})

    def get_latest_videos(self, channel_info: dict) -> list[dict]:
        channel_id = channel_info.get("channel_id", "").strip()
        channel_url = channel_info.get("channel_url", "").strip()
        channel_name = channel_info.get("channel_display_name", "알 수 없는 채널")

        if not channel_id:
            channel_id = self._extract_channel_id(channel_url)

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)

        videos = []

        for entry in feed.entries:
            video_url = getattr(entry, "link", "")
            video_id = getattr(entry, "yt_videoid", "")

            if not video_id and "v=" in video_url:
                video_id = video_url.split("v=")[-1].split("&")[0]

            if not video_id:
                continue

            videos.append({
                "video_id": video_id,
                "title": getattr(entry, "title", "제목 없음"),
                "url": video_url,
                "published": getattr(entry, "published", ""),
                "channel_display_name": channel_name
            })

        return videos

    def _extract_channel_id(self, channel_url: str) -> str:
        if not channel_url:
            raise ValueError("channel_id와 channel_url이 모두 비어 있습니다.")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
        }

        response = requests.get(channel_url, headers=headers, timeout=20)
        response.raise_for_status()

        patterns = [
            r'"channelId":"(UC[^"]+)"',
            r'"externalId":"(UC[^"]+)"',
            r'<meta itemprop="channelId" content="(UC[^"]+)">'
        ]

        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                return match.group(1)

        raise ValueError(f"채널 ID 자동 추출 실패: {channel_url}")

    def filter_video(self, video: dict) -> tuple[bool, str]:
        title_lower = video.get("title", "").lower()
        url_lower = video.get("url", "").lower()

        if self.youtube_config.get("exclude_shorts", True):
            shorts_keywords = ["#shorts", "shorts", "쇼츠"]
            if any(keyword in title_lower or keyword in url_lower for keyword in shorts_keywords):
                return False, "쇼츠 제외"

        if self.youtube_config.get("exclude_live_replay", True):
            live_keywords = ["live", "라이브", "실시간", "생방송"]
            if any(keyword in title_lower for keyword in live_keywords):
                return False, "라이브 다시보기 제외"

        days = self.youtube_config.get("published_after_days", None)

        if days is not None:
            pub_text = video.get("published", "")

            if not pub_text:
                return False, "업로드일 파싱 실패"

            published_dt = CommonManager.parse_youtube_datetime(pub_text)

            if not published_dt:
                return False, "업로드일 파싱 실패"

            cutoff = datetime.now(KST) - timedelta(days=days)

            if published_dt.astimezone(KST) < cutoff:
                return False, "작성일 기준 제외"

        return True, "통과"


class TranscriptExtractor:
    """
    유튜브 자막 추출 클래스입니다.
    """

    def __init__(self, language: str = "ko"):
        self.language = language

    def get_transcript(self, video_id: str) -> tuple[str | None, str]:
        try:
            fetched = YouTubeTranscriptApi().fetch(
                video_id,
                languages=[self.language]
            )

            text = "\n".join(
                item.text.replace("\n", " ").strip()
                for item in fetched
                if item.text and item.text.strip()
            )

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


class YouTubeSummarizer:
    """
    유튜브 자막 요약 전담 클래스입니다.

    Ollama API 호출 자체는 공통 OllamaClient가 담당하고,
    이 클래스는 유튜브 자막에 맞는 프롬프트만 구성합니다.
    """

    def __init__(self, ollama_client: OllamaClient, config: dict):
        self.ollama_client = ollama_client
        self.config = config
        self.ollama_config = config.get("ollama", {})

    def summarize(self, title: str, transcript_text: str) -> str:
        prompt = self._make_prompt(title, transcript_text)

        return self.ollama_client.generate(
            prompt=prompt,
            temperature=self.ollama_config.get("temperature", 0.2),
            timeout=self.ollama_config.get("timeout", 600)
        )

    @staticmethod
    def _make_prompt(title: str, transcript_text: str) -> str:
        return f"""다음은 유튜브 영상의 한국어 자막입니다.

영상 제목:
{title}

요청사항:
- 전체 내용을 한국어로 요약해 주세요.
- 핵심 내용을 5개 항목으로 정리해 주세요.
- 각 항목은 1~2문장 정도로 작성해 주세요.
- 광고 문구처럼 쓰지 말고 객관적으로 정리해 주세요.
- 번호는 1. 2. 3. 4. 5. 형식으로 붙여 주세요.

자막:
{transcript_text}
"""


class YouTubeEmailComposer:
    """
    유튜브 요약 결과 이메일의 제목과 본문을 구성하는 클래스입니다.
    Gmail 발송 자체는 공통 GmailClient가 담당합니다.
    """

    def __init__(self, config: dict):
        self.config = config

    def make_subject(self, channel_name: str, video_title: str) -> str:
        date_tag = datetime.now(KST).strftime("%y%m%d")
        safe_title = CommonManager.safe_filename(video_title, max_length=120)

        subject = f"{channel_name}_{date_tag}_{safe_title}"
        return subject[:180]

    def make_body(
        self,
        video: dict,
        summary: str,
        transcript_status: str
    ) -> str:
        channel_name = video.get("channel_display_name", "알 수 없는 채널")
        published_kst = CommonManager.format_youtube_datetime_kst(
            video.get("published", "")
        )

        return f"""유튜브 AI 요약 결과입니다.

[채널]
{channel_name}

[영상 제목]
{video.get("title", "")}

[영상 URL]
{video.get("url", "")}

[업로드일]
{published_kst}

[자막 상태]
{transcript_status}

[5줄 요약]
{summary}

--
본 메일은 Python + Ollama + Gmail API 기반 자동 요약 프로그램으로 발송되었습니다.
"""


class YouTubeSummaryPipeline:
    """
    유튜브 요약 전체 파이프라인입니다.

    실행 순서:
    1. 채널별 RSS 수집
    2. 업로드일 기준 정렬
    3. DB 중복 확인
    4. 쇼츠/라이브/날짜 필터링
    5. 자막 추출
    6. Ollama 요약
    7. 이메일 발송
    8. 처리 결과 DB 기록
    """

    def __init__(self, config: dict):
        self.config = config

        self.db = VideoDatabase(config["paths"]["database_file"])
        self.fetcher = YouTubeFetcher(config)

        transcript_language = config.get("youtube", {}).get(
            "transcript_language",
            "ko"
        )
        self.extractor = TranscriptExtractor(language=transcript_language)

        self.ollama_client = OllamaClient.from_config(config)
        self.summarizer = YouTubeSummarizer(self.ollama_client, config)

        self.gmail_client = GmailClient.from_config(config)
        self.email_composer = YouTubeEmailComposer(config)

    def run(self) -> None:
        logging.info("유튜브 요약 파이프라인 시작")

        all_videos = self._collect_all_videos()
        all_videos.sort(key=self._sort_key)

        max_videos = self.config.get("youtube", {}).get("max_videos_per_run", 10)
        processed_count = 0

        for video in all_videos:
            if processed_count >= max_videos:
                break

            video_id = video["video_id"]
            title = video["title"]
            channel_name = video["channel_display_name"]

            if self.db.is_processed(video_id):
                continue

            is_valid, reason = self.fetcher.filter_video(video)

            if not is_valid:
                self.db.mark_processed(
                    video_id=video_id,
                    channel_name=channel_name,
                    title=title,
                    url=video["url"],
                    published=video["published"],
                    status=reason
                )
                continue

            logging.info(f"[{channel_name}] 신규 영상 처리 시작: {title}")

            summary, status = self._extract_and_summarize(video)

            subject = self.email_composer.make_subject(channel_name, title)
            body = self.email_composer.make_body(video, summary, status)

            final_status = status

            try:
                self.gmail_client.send_email(subject, body)
                logging.info(f"[{channel_name}] 메일 발송 완료: {title}")
            except Exception as e:
                logging.exception(f"[{channel_name}] 메일 발송 실패: {e}")
                final_status = f"메일 발송 실패 / 기존 상태: {status} / 오류: {e}"

            # 선생님 운영 방침 반영:
            # 메일 실패, 요약 실패, 자막 없음도 모두 처리 완료로 기록하여
            # 다음 실행 때 반복 처리하지 않도록 합니다.
            self.db.mark_processed(
                video_id=video_id,
                channel_name=channel_name,
                title=title,
                url=video["url"],
                published=video["published"],
                status=final_status
            )

            processed_count += 1

        logging.info("유튜브 요약 파이프라인 종료")

    def _collect_all_videos(self) -> list[dict]:
        channels = self.config.get("youtube", {}).get("channels", [])
        all_videos = []

        for channel in channels:
            channel_name = channel.get("channel_display_name", "알 수 없는 채널")

            try:
                videos = self.fetcher.get_latest_videos(channel)
                all_videos.extend(videos)
                logging.info(f"[{channel_name}] RSS 영상 수집 완료: {len(videos)}건")
            except Exception as e:
                logging.exception(f"[{channel_name}] 수집 실패: {e}")

        return all_videos

    @staticmethod
    def _sort_key(video: dict):
        dt = CommonManager.parse_youtube_datetime(video.get("published", ""))

        if dt:
            return dt

        return datetime.min.replace(tzinfo=timezone.utc)

    def _extract_and_summarize(self, video: dict) -> tuple[str, str]:
        video_id = video["video_id"]
        title = video["title"]

        transcript_text, status = self.extractor.get_transcript(video_id)

        if not transcript_text:
            return status, status

        safe_id = CommonManager.safe_filename(video_id, max_length=80)

        CommonManager.save_text(
            text=transcript_text,
            save_dir=self.config["paths"]["transcript_dir"],
            filename=f"{safe_id}_transcript.txt"
        )

        try:
            summary = self.summarizer.summarize(title, transcript_text)

            CommonManager.save_text(
                text=summary,
                save_dir=self.config["paths"]["summary_dir"],
                filename=f"{safe_id}_summary.txt"
            )

            return summary, "요약 완료"

        except Exception as e:
            logging.exception(f"요약 실패: {title} / {e}")
            return f"요약 불가(오류: {e})", "요약 실패"
