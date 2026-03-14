from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from threading import Lock, get_ident
import time
from typing import Any, Callable

import httpx

from research_bot.bootstrap.settings import Settings


class KisClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class KisTokenState:
    access_token: str
    token_type: str
    issued_at: datetime
    expires_at: datetime

    def is_expiring_soon(self, refresh_buffer_seconds: int) -> bool:
        return datetime.now() >= self.expires_at - timedelta(seconds=refresh_buffer_seconds)


@dataclass(frozen=True)
class KisTokenStatus:
    provider: str
    configured: bool
    authenticated: bool
    base_url: str | None
    token_expires_at: datetime | None
    message: str


logger = logging.getLogger(__name__)


class KisClient:
    def __init__(
        self,
        settings: Settings,
        on_token_issued: Callable[[], None] | None = None,
    ) -> None:
        self.base_url = settings.kis_base_url
        self.app_key = settings.kis_app_key
        self.app_secret = settings.kis_app_secret
        self.timeout_seconds = settings.kis_api_timeout_seconds
        self.refresh_buffer_seconds = settings.kis_token_refresh_buffer_seconds
        self.request_delay_seconds = max(0.0, settings.kis_request_delay_seconds)
        self.initial_request_stagger_seconds = max(0.0, settings.kis_initial_request_stagger_seconds)
        self.request_max_retries = max(0, settings.kis_request_max_retries)
        self.request_retry_backoff_seconds = max(0.0, settings.kis_request_retry_backoff_seconds)
        self.token_cache_path = settings.kis_token_cache_path
        self.on_token_issued = on_token_issued
        self._token_state: KisTokenState | None = self._load_token_state()
        self._token_lock = Lock()
        self._request_stagger_lock = Lock()
        self._thread_stagger_order: dict[int, int] = {}
        self._stagger_applied_threads: set[int] = set()
        self._http_client: httpx.Client | None = None

    def get_token_status(self) -> KisTokenStatus:
        configured = self.is_configured
        token_state = self._token_state
        authenticated = (
            token_state is not None
            and not token_state.is_expiring_soon(self.refresh_buffer_seconds)
        )
        if not configured:
            message = "KIS base url, app key, app secret가 모두 필요합니다."
        elif authenticated:
            message = "토큰이 메모리 또는 로컬 캐시에서 재사용되고 있습니다."
        else:
            message = "토큰이 아직 발급되지 않았습니다."
        return KisTokenStatus(
            provider="kis",
            configured=configured,
            authenticated=authenticated,
            base_url=self.base_url or None,
            token_expires_at=token_state.expires_at if token_state else None,
            message=message,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.app_key and self.app_secret)

    def authenticate(self, force_refresh: bool = False) -> KisTokenStatus:
        self.ensure_access_token(force_refresh=force_refresh)
        return self.get_token_status()

    def ensure_access_token(self, force_refresh: bool = False) -> str:
        token_state = self._token_state
        if (
            not force_refresh
            and token_state is not None
            and not token_state.is_expiring_soon(self.refresh_buffer_seconds)
        ):
            return token_state.access_token

        issued_new_token = False
        with self._token_lock:
            token_state = self._token_state
            if (
                not force_refresh
                and token_state is not None
                and not token_state.is_expiring_soon(self.refresh_buffer_seconds)
            ):
                return token_state.access_token
            self._token_state = self._issue_access_token()
            self._save_token_state(self._token_state)
            issued_new_token = True

        if issued_new_token and self.on_token_issued is not None:
            self.on_token_issued()
        return self._token_state.access_token

    def request(
        self,
        path: str,
        params: dict[str, str] | None = None,
        *,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
        tr_id: str | None = None,
        custtype: str = "P",
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        token = self.ensure_access_token()
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "custtype": custtype,
        }
        if tr_id:
            headers["tr_id"] = tr_id
        if json_body is not None:
            headers["content-type"] = "application/json; charset=utf-8"
        if extra_headers:
            headers.update(extra_headers)

        self._apply_initial_request_stagger()
        response = self._request_with_retries(
            method=method,
            path=path,
            params=params,
            json_body=json_body,
            headers=headers,
            error_prefix="한국투자증권 API 요청을 전송하지 못했습니다.",
        )

        payload = response.json()
        if not isinstance(payload, dict):
            raise KisClientError("한국투자증권 API 응답 형식이 예상과 다릅니다.")
        rt_cd = str(payload.get("rt_cd", "")).strip()
        if rt_cd and rt_cd != "0":
            code = str(payload.get("msg_cd", "")).strip()
            detail = str(payload.get("msg1", "")).strip()
            if code and detail:
                raise KisClientError(f"한국투자증권 API 오류입니다. msg_cd={code}, msg1={detail}")
            if detail:
                raise KisClientError(f"한국투자증권 API 오류입니다. msg1={detail}")
            raise KisClientError("한국투자증권 API가 실패 응답을 반환했습니다.")
        return payload

    def _issue_access_token(self) -> KisTokenState:
        if not self.is_configured:
            raise KisClientError(
                "KIS 인증 정보가 부족합니다. base url, app key, app secret를 확인하세요."
            )

        issued_at = datetime.now()
        response = self._request_with_retries(
            method="POST",
            path="/oauth2/tokenP",
            json_body={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            },
            headers={"content-type": "application/json; charset=utf-8"},
            error_prefix="한국투자증권 토큰 발급 요청을 전송하지 못했습니다.",
        )

        payload = response.json()
        if not isinstance(payload, dict):
            raise KisClientError("한국투자증권 토큰 응답 형식이 예상과 다릅니다.")

        access_token = str(payload.get("access_token", "")).strip()
        token_type = str(payload.get("token_type", "Bearer")).strip() or "Bearer"
        if not access_token:
            raise KisClientError("한국투자증권 토큰 응답에 access_token이 없습니다.")

        expires_at = _resolve_token_expiration(payload, issued_at)
        return KisTokenState(
            access_token=access_token,
            token_type=token_type,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            if not self.base_url:
                raise KisClientError("KIS base url이 비어 있습니다.")
            self._http_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
        return self._http_client

    def _apply_initial_request_stagger(self) -> None:
        if self.initial_request_stagger_seconds <= 0:
            return
        thread_id = get_ident()
        with self._request_stagger_lock:
            if thread_id in self._stagger_applied_threads:
                return
            order = self._thread_stagger_order.get(thread_id)
            if order is None:
                order = len(self._thread_stagger_order)
                self._thread_stagger_order[thread_id] = order
            self._stagger_applied_threads.add(thread_id)
        delay_seconds = order * self.initial_request_stagger_seconds
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    def _request_with_retries(
        self,
        *,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str],
        error_prefix: str,
    ) -> httpx.Response:
        max_attempts = self.request_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = self._get_http_client().request(
                    method=method,
                    url=path,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as error:
                last_error = error
                message = _build_http_error_message(error.response)
                if attempt >= max_attempts or not _is_retryable_http_status(error.response):
                    raise KisClientError(message) from error
                self._sleep_before_retry(
                    path=path,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    reason=message,
                )
            except httpx.HTTPError as error:
                last_error = error
                reason = f"{error.__class__.__name__}: {error}"
                if attempt >= max_attempts:
                    raise KisClientError(f"{error_prefix} ({reason})") from error
                self._sleep_before_retry(
                    path=path,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    reason=reason,
                )
            finally:
                if self.request_delay_seconds > 0:
                    time.sleep(self.request_delay_seconds)

        if last_error is not None:
            raise KisClientError(
                f"{error_prefix} ({last_error.__class__.__name__}: {last_error})"
            ) from last_error
        raise KisClientError(error_prefix)

    def _sleep_before_retry(
        self,
        *,
        path: str,
        attempt: int,
        max_attempts: int,
        reason: str,
    ) -> None:
        delay = self.request_retry_backoff_seconds * attempt
        logger.warning(
            "[RETRY] %s attempt=%s/%s wait=%.2fs reason=%s",
            path,
            attempt + 1,
            max_attempts,
            delay,
            reason,
        )
        if delay > 0:
            time.sleep(delay)

    def _load_token_state(self) -> KisTokenState | None:
        try:
            if not self.token_cache_path.exists():
                return None
            payload = json.loads(self.token_cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            access_token = str(payload.get("access_token", "")).strip()
            token_type = str(payload.get("token_type", "Bearer")).strip() or "Bearer"
            issued_at_text = str(payload.get("issued_at", "")).strip()
            expires_at_text = str(payload.get("expires_at", "")).strip()
            if not access_token or not issued_at_text or not expires_at_text:
                return None
            token_state = KisTokenState(
                access_token=access_token,
                token_type=token_type,
                issued_at=datetime.fromisoformat(issued_at_text),
                expires_at=datetime.fromisoformat(expires_at_text),
            )
            if token_state.is_expiring_soon(self.refresh_buffer_seconds):
                return None
            return token_state
        except Exception:
            return None

    def _save_token_state(self, token_state: KisTokenState) -> None:
        try:
            self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_cache_path.write_text(
                json.dumps(
                    {
                        "access_token": token_state.access_token,
                        "token_type": token_state.token_type,
                        "issued_at": token_state.issued_at.isoformat(),
                        "expires_at": token_state.expires_at.isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            return


def _resolve_token_expiration(payload: dict[str, Any], issued_at: datetime) -> datetime:
    expires_in = payload.get("expires_in")
    if expires_in is not None:
        try:
            return issued_at + timedelta(seconds=int(float(str(expires_in))))
        except (TypeError, ValueError):
            pass

    expires_at_text = str(payload.get("access_token_token_expired", "")).strip()
    if expires_at_text:
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return datetime.strptime(expires_at_text, pattern)
            except ValueError:
                continue

    return issued_at + timedelta(hours=24)


def _build_http_error_message(response: httpx.Response) -> str:
    message = f"한국투자증권 요청이 실패했습니다. status={response.status_code}"
    try:
        payload = response.json()
    except ValueError:
        return message
    if isinstance(payload, dict):
        code = str(payload.get("msg_cd", "")).strip()
        detail = str(payload.get("msg1", "")).strip()
        if code and detail:
            return f"{message}, msg_cd={code}, msg1={detail}"
        if detail:
            return f"{message}, msg1={detail}"
    return message


def _is_retryable_http_status(response: httpx.Response) -> bool:
    if response.status_code in {429, 500, 502, 503, 504}:
        return True
    try:
        payload = response.json()
    except ValueError:
        return False
    if not isinstance(payload, dict):
        return False
    detail = str(payload.get("msg1", "")).strip()
    return "초당 거래건수를 초과" in detail
