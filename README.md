# logitux

> 리눅스에서 로지텍 마우스 버튼을, 마우스 그림 보고 클릭만으로 매핑하기.

Logi Options+의 리눅스 대안. 복잡한 설정 없이, 마우스 도식에서 버튼을 클릭해 원하는 키조합(예: `Ctrl+Alt+S`)을 등록합니다.

## 목표

사내 리눅스 사용자 누구나 쉽게 로지텍 마우스 버튼을 커스터마이징할 수 있게 한다.

## 특징 (계획)

- 🖱️ **마우스 도식 시각화** — 연결된 마우스를 그림으로 보여주고, 버튼 위치를 선으로 표시
- 🎯 **클릭 매핑** — 버튼 클릭 → 키조합 입력 → 끝. CLI/룰 편집 불필요
- 🔌 **Solaar 백엔드** — 검증된 HID++ 매핑 엔진을 뒤에 숨겨 활용
- 📦 **쉬운 배포** — 사내 누구나 원클릭 설치 (AppImage/Flatpak 예정)
- ➕ **모델 확장** — MX Master 3/4부터, 데이터 추가만으로 새 모델 지원

## 지원 모델

| 모델 | 상태 |
|------|------|
| MX Master 4 | 🚧 개발 중 |
| MX Master 3 / 3S | 🚧 개발 중 |
| 그 외 로지텍 | 📋 데이터 추가로 확장 예정 |

## 빠른 시작

### 1. 의존성 설치

```bash
sudo apt install solaar          # 백엔드 매핑 엔진 + udev 권한 룰
pip install -r requirements.txt  # PySide6 GUI
```

> Solaar 설치 직후엔 udev 권한(uaccess)이 기존 연결 기기에 적용되지 않을 수 있습니다.
> 마우스를 다시 연결하거나 재로그인하면 됩니다.

### 2. 실행

```bash
python3 main.py
```

연결된 로지텍 마우스가 카드로 표시되며, 선택하면 다음 단계(도식 매핑)로 넘어갑니다.

## 상태

🚧 **마일스톤 ① 구현 완료** — 마우스 감지 + 선택 GUI 동작.
다음: ② 마우스 도식 시각화 + 클릭 매핑. 자세한 계획은 [`docs/spec.md`](docs/spec.md) 참조.

### 구조

```
logitux/
  backend/
    solaar_env.py   # Solaar(logitech_receiver) 라이브러리 경로 탐색
    detect.py       # 연결된 마우스 감지·열거
  gui/
    select_window.py # 마우스 선택 화면 (PySide6)
main.py             # 진입점
```

## 라이선스

추후 결정.
