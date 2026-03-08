# ORB 연구용 어댑터 프로토타입

국내 주식 오프닝 ORB 백테스트를 위한 연구용 프로토타입입니다.

## 범위

이 프로토타입은 `../../docs/research/02.백테스트프로그램정의.md`에 정리된
1차 진단용 백테스트를 기준으로 시작합니다.
현재 초점은 아래와 같습니다.

- 갭상승 세션 식별
- 여러 ORB 구간 계산
- 첫 ORB High 돌파 탐지
- 10:00까지 ORB High 위 유지 여부 측정
- 비교 가능한 결과 행 내보내기

## 구조

- `quant_trader/`: 백테스트 엔진, 설정 로더, 입출력, 콘솔 UI
- `configs/`: 실행 설정
- `docs/`: 구조 메모
- `../../data/input/`: 원본 CSV 입력
- `../../data/output/`: 결과 CSV 출력
- `tests/`: 단위 테스트

## 입력 형식

분봉 CSV 컬럼:

- `symbol`
- `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `prev_close`

선택적 틱 CSV 컬럼:

- `symbol`
- `timestamp`
- `price`
- `volume`

시각은 `2026-03-09T09:03:00` 같은 ISO 형식을 사용합니다.

## 실행

```bash
cd prototypes/orb-research-adapter
python -m quant_trader --config configs/orb_research.toml
```

기본 설정은 `../../data/input/minute_bars.csv`를 읽고
`../../data/output/orb_breakout_results.csv`로 결과를 저장합니다.
