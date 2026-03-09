from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

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


class KisClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.kis_base_url
        self.app_key = settings.kis_app_key
        self.app_secret = settings.kis_app_secret
        self.timeout_seconds = settings.kis_api_timeout_seconds
        self.refresh_buffer_seconds = settings.kis_token_refresh_buffer_seconds
        self._token_state: KisTokenState | None = None
        self._token_lock = Lock()
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
            message = "토큰이 메모리에 캐시되어 있습니다."
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

        with self._token_lock:
            token_state = self._token_state
            if (
                not force_refresh
                and token_state is not None
                and not token_state.is_expiring_soon(self.refresh_buffer_seconds)
            ):
                return token_state.access_token
            self._token_state = self._issue_access_token()
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

        try:
            response = self._get_http_client().request(
                method=method,
                url=path,
                params=params,
                json=json_body,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise KisClientError(_build_http_error_message(error.response)) from error
        except httpx.HTTPError as error:
            raise KisClientError("한국투자증권 API 요청을 전송하지 못했습니다.") from error

        payload = response.json()
        if not isinstance(payload, dict):
            raise KisClientError("한국투자증권 API 응답 형식이 예상과 다릅니다.")
        return payload

    def _issue_access_token(self) -> KisTokenState:
        if not self.is_configured:
            raise KisClientError(
                "KIS 인증 정보가 부족합니다. base url, app key, app secret를 확인하세요."
            )

        issued_at = datetime.now()
        try:
            response = self._get_http_client().post(
                "/oauth2/tokenP",
                headers={"content-type": "application/json; charset=utf-8"},
                json={
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise KisClientError(_build_http_error_message(error.response)) from error
        except httpx.HTTPError as error:
            raise KisClientError("한국투자증권 토큰 발급 요청을 전송하지 못했습니다.") from error

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
