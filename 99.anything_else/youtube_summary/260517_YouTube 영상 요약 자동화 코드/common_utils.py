# =========================================================
# common_utils.py
# 역할:
#   1. 설정 파일 로드
#   2. 폴더 및 로거 설정
#   3. 텍스트 저장 / 안전한 파일명 생성
#   4. Ollama API 공통 호출
#   5. Gmail API 공통 발송
# =========================================================

import os
import re
import yaml
import base64
import logging
import requests

from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# 한국 시간대 전역 상수
KST = timezone(timedelta(hours=9))


class CommonManager:
    """
    여러 프로젝트에서 공통으로 사용할 환경 관리 도구입니다.

    포함 기능:
    - config.yaml 로드
    - 프로젝트 폴더 생성
    - 로그 설정
    - 텍스트 저장
    - 안전한 파일명 생성
    - 날짜 문자열 변환
    """

    @staticmethod
    def load_config(config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @staticmethod
    def setup_environment(config: dict) -> None:
        """
        config.yaml의 paths 항목을 기준으로 필요한 폴더를 생성하고,
        파일 로그와 콘솔 로그를 함께 설정합니다.
        """
        paths = config.get("paths", {})

        # 생성 대상 폴더
        dir_keys = [
            "base_dir",
            "transcript_dir",
            "summary_dir"
        ]

        for key in dir_keys:
            path_value = paths.get(key)
            if path_value:
                Path(path_value).mkdir(parents=True, exist_ok=True)

        # 파일 경로의 부모 폴더 생성
        file_keys = [
            "log_file",
            "credentials_file",
            "token_file",
            "database_file"
        ]

        for key in file_keys:
            path_value = paths.get(key)
            if path_value:
                Path(path_value).parent.mkdir(parents=True, exist_ok=True)

        # 로거 설정
        log_file = paths.get("log_file")
        if log_file:
            logging.basicConfig(
                filename=log_file,
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                encoding="utf-8",
                force=True
            )

            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            console.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )

            root_logger = logging.getLogger("")
            root_logger.addHandler(console)

    @staticmethod
    def safe_filename(text: str, max_length: int = 120) -> str:
        """
        Windows 파일명에 사용할 수 없는 문자를 제거합니다.
        """
        text = str(text)
        text = re.sub(r'[\\/:*?"<>|]', " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_length]

    @staticmethod
    def save_text(text: str, save_dir: str, filename: str) -> str:
        """
        텍스트를 UTF-8 형식으로 저장합니다.
        """
        Path(save_dir).mkdir(parents=True, exist_ok=True)

        safe_name = CommonManager.safe_filename(filename, max_length=180)
        save_path = Path(save_dir) / safe_name

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)

        return str(save_path)

    @staticmethod
    def now_kst_string() -> str:
        return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def parse_youtube_datetime(date_text: str):
        """
        YouTube RSS의 published 문자열을 datetime 객체로 변환합니다.
        """
        if not date_text:
            return None

        try:
            return datetime.fromisoformat(date_text.replace("Z", "+00:00"))
        except Exception:
            return None

    @staticmethod
    def format_youtube_datetime_kst(date_text: str) -> str:
        """
        YouTube 업로드일 문자열을 KST 표시 문자열로 변환합니다.
        """
        dt = CommonManager.parse_youtube_datetime(date_text)

        if not dt:
            return date_text or "업로드일 확인 불가"

        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")


class OllamaClient:
    """
    Ollama 로컬 API 호출 전담 공통 클래스입니다.

    이 클래스는 '유튜브 요약' 또는 '리포트 본문 추출'을 알지 못합니다.
    오직 prompt를 받아 Ollama에 전달하고, 응답 문자열을 반환합니다.
    """

    def __init__(
        self,
        api_url: str,
        model: str,
        temperature: float = 0.2,
        timeout: int = 600
    ):
        self.api_url = api_url
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    @classmethod
    def from_config(cls, config: dict):
        ollama_config = config.get("ollama", {})

        return cls(
            api_url=ollama_config.get("api_url", "http://localhost:11434/api/generate"),
            model=ollama_config.get("model", "gemma4:e4b"),
            temperature=ollama_config.get("temperature", 0.2),
            timeout=ollama_config.get("timeout", 600)
        )

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        timeout: int | None = None,
        options: dict | None = None
    ) -> str:
        """
        Ollama API에 prompt를 전달하고 결과 텍스트를 반환합니다.
        """

        final_options = {
            "temperature": self.temperature if temperature is None else temperature
        }

        if options:
            final_options.update(options)

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": final_options
        }

        response = requests.post(
            self.api_url,
            json=payload,
            timeout=timeout or self.timeout
        )
        response.raise_for_status()

        result = response.json().get("response", "").strip()

        if not result:
            raise ValueError("Ollama 응답이 비어 있습니다.")

        return result


class GmailClient:
    """
    Gmail API 인증 및 발송 전담 공통 클래스입니다.

    이메일 제목과 본문을 어떻게 만들지는 각 프로젝트에서 담당하고,
    이 클래스는 최종 subject/body를 받아 발송만 수행합니다.
    """

    GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

    def __init__(
        self,
        credentials_file: str,
        token_file: str,
        sender: str,
        receiver: str
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.sender = sender
        self.receiver = receiver
        self.service = self._get_service()

    @classmethod
    def from_config(cls, config: dict):
        paths = config.get("paths", {})
        email = config.get("email", {})

        return cls(
            credentials_file=paths["credentials_file"],
            token_file=paths["token_file"],
            sender=email["sender"],
            receiver=email["receiver"]
        )

    def _get_service(self):
        creds = None

        Path(self.credentials_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.token_file).parent.mkdir(parents=True, exist_ok=True)

        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(
                self.token_file,
                [self.GMAIL_SEND_SCOPE]
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file,
                    [self.GMAIL_SEND_SCOPE]
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    def send_email(self, subject: str, body: str) -> None:
        message = MIMEText(body, "plain", "utf-8")
        message["To"] = self.receiver
        message["From"] = self.sender
        message["Subject"] = subject

        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        self.service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()
