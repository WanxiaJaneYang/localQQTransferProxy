import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


@dataclass(frozen=True)
class BridgeConfig:
    qq_app_id: str
    qq_app_secret: str
    qq_bot_token: str
    qq_callback_secret: str
    qq_api_base_url: str
    claude_cmd: List[str]
    session_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        load_dotenv()

        qq_app_id = (os.getenv("QQ_APP_ID") or os.getenv("QQ_BOT_APP_ID") or "").strip()
        qq_app_secret = (os.getenv("QQ_APP_SECRET") or "").strip()
        qq_bot_token = (os.getenv("QQ_BOT_TOKEN") or "").strip()
        qq_callback_secret = (os.getenv("QQ_CALLBACK_SECRET") or "").strip()
        qq_api_base_url = (os.getenv("QQ_API_BASE_URL") or "https://api.sgroup.qq.com").strip()

        claude_cmd_raw = (os.getenv("CLAUDE_CMD") or "claude").strip()
        claude_cmd = claude_cmd_raw.split()

        session_timeout_raw = (os.getenv("SESSION_TIMEOUT_SECONDS") or "1800").strip()

        errors: List[str] = []
        if not qq_app_id:
            errors.append("QQ_APP_ID is required.")
        if not qq_app_secret:
            errors.append("QQ_APP_SECRET is required.")
        if not qq_bot_token:
            errors.append("QQ_BOT_TOKEN is required when using Bot token mode.")
        if not qq_api_base_url:
            errors.append("QQ_API_BASE_URL cannot be empty.")
        if not claude_cmd:
            errors.append("CLAUDE_CMD must include a command to execute.")

        session_timeout_seconds = 0
        try:
            session_timeout_seconds = int(session_timeout_raw)
            if session_timeout_seconds <= 0:
                raise ValueError
        except ValueError:
            errors.append("SESSION_TIMEOUT_SECONDS must be a positive integer.")

        if errors:
            joined = "\n- ".join(errors)
            raise ValueError(f"Configuration validation failed:\n- {joined}")

        return cls(
            qq_app_id=qq_app_id,
            qq_app_secret=qq_app_secret,
            qq_bot_token=qq_bot_token,
            qq_callback_secret=qq_callback_secret,
            qq_api_base_url=qq_api_base_url,
            claude_cmd=claude_cmd,
            session_timeout_seconds=session_timeout_seconds,
        )
