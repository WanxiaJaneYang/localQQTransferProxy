import logging
import os
import select
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


LOGGER = logging.getLogger(__name__)


@dataclass
class ClaudeSession:
    session_key: str
    process: subprocess.Popen
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_used: float = field(default_factory=time.time)


class ClaudeAdapter:
    """Manages long-lived local Claude CLI sessions keyed by sender ID."""

    def __init__(
        self,
        command: Optional[List[str]] = None,
        idle_timeout_seconds: int = 900,
        cleanup_interval_seconds: int = 30,
    ) -> None:
        self._command = command or ["claude"]
        self._idle_timeout_seconds = idle_timeout_seconds
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._sessions: Dict[str, ClaudeSession] = {}
        self._sessions_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()

    def ask(self, session_key: str, prompt: str, timeout_seconds: int = 30) -> str:
        while True:
            session = self._get_or_create_session(session_key)
            with session.lock:
                if session.process.poll() is not None:
                    LOGGER.info("Claude process exited, recreating", extra={"session_key": session_key})
                    self._replace_session(session_key)
                    continue

                session.last_used = time.time()
                assert session.process.stdin is not None
                assert session.process.stdout is not None

                session.process.stdin.write(prompt + "\n")
                session.process.stdin.flush()
                output = self._read_response(session.process, timeout_seconds)
                session.last_used = time.time()
                return output.strip() or "(no response)"

    def close(self) -> None:
        self._shutdown_event.set()
        self._cleanup_thread.join(timeout=2)
        with self._sessions_lock:
            keys = list(self._sessions.keys())
        for key in keys:
            self._terminate_session(key)

    def _get_or_create_session(self, session_key: str) -> ClaudeSession:
        with self._sessions_lock:
            session = self._sessions.get(session_key)
            if session and session.process.poll() is None:
                return session
            if session:
                self._terminate_process(session.process)
            session = ClaudeSession(session_key=session_key, process=self._spawn_process())
            self._sessions[session_key] = session
            return session

    def _replace_session(self, session_key: str) -> ClaudeSession:
        with self._sessions_lock:
            existing = self._sessions.get(session_key)
            if existing:
                self._terminate_process(existing.process)
            session = ClaudeSession(session_key=session_key, process=self._spawn_process())
            self._sessions[session_key] = session
            return session

    def _spawn_process(self) -> subprocess.Popen:
        LOGGER.info("Starting Claude CLI process", extra={"command": self._command})
        return subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    def _read_response(self, process: subprocess.Popen, timeout_seconds: int) -> str:
        assert process.stdout is not None
        chunks: List[str] = []
        stdout_fd = process.stdout.fileno()
        deadline = time.time() + timeout_seconds
        quiet_window_seconds = 0.6

        while time.time() < deadline:
            remaining = max(0.05, deadline - time.time())
            ready, _, _ = select.select([stdout_fd], [], [], min(0.25, remaining))
            if not ready:
                if chunks:
                    break
                continue
            raw = os.read(stdout_fd, 4096)
            if not raw:
                break
            chunks.append(raw.decode("utf-8", errors="replace"))
            quiet_deadline = time.time() + quiet_window_seconds
            while time.time() < quiet_deadline:
                ready, _, _ = select.select([stdout_fd], [], [], 0.1)
                if not ready:
                    continue
                extra_raw = os.read(stdout_fd, 4096)
                if not extra_raw:
                    break
                chunks.append(extra_raw.decode("utf-8", errors="replace"))
        return "".join(chunks)

    def _cleanup_worker(self) -> None:
        while not self._shutdown_event.wait(self._cleanup_interval_seconds):
            now = time.time()
            stale: List[str] = []
            with self._sessions_lock:
                for session_key, session in self._sessions.items():
                    if (now - session.last_used) > self._idle_timeout_seconds:
                        stale.append(session_key)
            for session_key in stale:
                LOGGER.info("Cleaning up idle Claude session", extra={"session_key": session_key})
                self._terminate_session(session_key)

    def _terminate_session(self, session_key: str) -> None:
        with self._sessions_lock:
            session = self._sessions.pop(session_key, None)
        if session:
            self._terminate_process(session.process)

    @staticmethod
    def _terminate_process(process: subprocess.Popen) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
