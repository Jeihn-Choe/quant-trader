# QuantTrader 작업공간

이 저장소는 단일 프로젝트가 아니라 작업공간 형태로 정리되어 있습니다.

## 최상위 구조

- `apps/research/`: 연구용 애플리케이션 묶음
- `apps/research/bot/`: 연구용 백엔드 봇 프로젝트 영역
- `apps/research/web_ui/`: 연구용 웹 UI 프로젝트 영역
- `apps/trading/`: 실거래용 애플리케이션 묶음
- `apps/trading/engine/`: 실거래 엔진 프로젝트 영역
- `apps/trading/web_ui/`: 실거래 웹 UI 프로젝트 영역
- `prototypes/orb-research-adapter/`: 1차 ORB 백테스트 스캐폴드 프로토타입
- `docs/research/`: 전략, 백테스트, 트레이딩 연구 문서
- `docs/context/`: 인수인계나 세션 컨텍스트 문서
- `data/`: 공용 입력 및 출력 데이터 영역

## 현재 의도

`apps` 아래에서 `research`와 `trading`을 각각 별도 컨텍스트로 나눴습니다.
현재는 연구용 프로젝트만 실제로 존재하고, 실거래 쪽은 이후 확장을 위한 자리만 먼저 잡아둔 상태입니다.
