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

🚧 **마일스톤 ①–② + ③-a 구현 완료**
- ① 마우스 감지 + 선택 GUI
- ② 도식 시각화 + 클릭 매핑 — 마우스 도식 위 버튼 핫스팟·연결선·라벨, 버튼 클릭 → 단축키 지정
- ③-a **키 emit 적용** — "적용" 버튼을 누르면 매핑이 Solaar 백엔드(`divert-keys` + `rules.yaml`)로 변환되어 **실제로 키가 입력**됩니다. 매핑은 기기별로 저장돼 다음 실행 시 복원됩니다. (실측 검증 완료)
- ③-b **autostart 보장** — 적용 시 데몬이 로그인할 때마다 자동 실행되도록 보장합니다. 대부분 solaar 설치만으로 시스템 autostart가 켜지며, 꺼져 있거나 없는 PC에서만 logitux가 사용자 autostart를 추가합니다.

다음: ③-c 패키징(AppImage/Flatpak). 계획·백엔드 레시피는 [`docs/spec.md`](docs/spec.md) 참조.

> **제약**: 실제 키 입력은 X11에서 동작합니다(Solaar `KeyPress`가 XTEST 기반). Wayland 세션에선 적용 시 경고가 표시됩니다.
> MX Master 4의 **액션 버튼(CID 416)**은 Solaar가 이름을 몰라(`unknown:01A0`) 현재 매핑에서 자동 제외됩니다 — 별도 처리 예정.

#### MX Master 4 버튼 메모

MX Master 4는 재할당 가능 버튼이 7개입니다(좌/우 클릭은 고정):
휠 클릭, 휠 모드 전환, 뒤로, 앞으로, 제스처 버튼, 그리고 **액션 버튼(CID 416)**.
액션 버튼은 엄지쪽 Haptic Sense Panel을 눌러 Actions Ring을 여는 신규 버튼으로,
Solaar가 아직 이름을 모르지만(`unknown:01A0`) 소거법 + 공식 문서로 확정했습니다.
실측 도구(`tools/probe_buttons.py`)는 WIP — 한계는 해당 파일 docstring 참조.

### 도식 이미지

- **MX Master 4 / 3S / 3** — 로지텍 공식 실물 이미지를 사용합니다. 저작권 때문에
  저장소에 번들하지 않고, **첫 실행 시 로지텍 CDN에서 다운로드**해
  `~/.cache/logitux/images/`에 캐시합니다.
- **그 외 모델** — 번들된 일반 마우스 벡터 도식(`mouse-generic.svg`)으로 표시합니다.
  이미지 다운로드 실패(오프라인 등) 시에도 이 도식으로 폴백합니다.

### 구조

```
logitux/
  backend/
    solaar_env.py    # Solaar(logitech_receiver) 라이브러리 경로 탐색
    detect.py        # 연결된 마우스 감지·열거
    buttons.py       # 재할당 가능 버튼(REPROG CONTROLS) 추출
    assets.py        # 모델 이미지 다운로드·캐시
    models.py        # 모델 도식 데이터 로드 + 기기 매칭
    keysyms.py       # Qt 키시퀀스 → X11 keysym 이름 변환 (③)
    solaar_rules.py  # 매핑 → divert-keys + rules.yaml 적용 + 데몬 관리 (③)
    autostart.py     # 데몬 로그인 자동 실행 보장 (③-b)
  data/mice/
    mx-master-4.json   # MX4 실물 이미지 URL + 버튼 좌표
    mx-master-3s.json  # MX3S/3 실물 이미지 URL + 버튼 좌표
    _generic.json      # 폴백 모델 (일반 도식)
    mouse-generic.svg  # 폴백 벡터 도식
  gui/
    select_window.py  # 마우스 선택 화면
    mapping_window.py # 도식 매핑 화면 (QGraphicsView)
    key_capture.py    # 단축키 입력 다이얼로그
main.py              # 진입점
```

### 새 마우스 모델 추가

`data/mice/` 에 `<model>.json`을 추가하면 코드 수정 없이 인식됩니다.
- 실물 이미지: `image_url`(원격) + `canvas`(이미지 크기) + 버튼 좌표
- 번들 도식: `svg` 파일명 + `canvas`(viewBox 크기) + 버튼 좌표
- 매칭: `match`의 `wpid` 또는 `codename`(문자열 또는 리스트)

## 라이선스

추후 결정.
