# research bot

연구용 백엔드 애플리케이션입니다.

현재 포함 기능:

- 과거 1분봉 적재 API
- 세션 기준값(`prev_close`, `session_open`, `gap_pct`) 적재 API
- 오프닝 1시간 1분봉 생성 API
- ORB 계산 및 ORB High 돌파 탐지 API
- DuckDB 기반 로컬 저장
- 한국투자증권 access token 자동 발급 클라이언트와 모의 데이터 공급자

기본 공급자는 `mock`입니다.
한국투자증권을 쓸 때는 `.env`에 `base url`, `app key`, `app secret`만 넣으면 되고,
access token은 backend가 `/oauth2/tokenP`로 자동 발급받습니다.
웹 UI 개발 서버와 연결되도록 기본 CORS origin은 `127.0.0.1:5173`, `localhost:5173`으로 열어뒀습니다.

실행 예시:

```bash
uvicorn research_bot.main:app --reload --host 127.0.0.1 --port 8000
```
