# logitux — Spec

## Goal

리눅스에서 로지텍 마우스 버튼을, 비기술자도 **마우스 도식을 보고 클릭만으로** 매핑할 수 있게 하는 사내 배포용 도구. Solaar(HID++ 매핑 엔진)를 백엔드로 감추고, 시각화 GUI + 쉬운 설치를 제공한다.

## Milestones

1. **마우스 감지·선택** — 연결된 로지텍 기기를 인식해 목록에서 선택. MX Master 3/4 우선.
2. **도식 시각화 + 매핑 편집** — 선택한 마우스의 SVG 도식 위에 버튼 위치를 선/라벨로 표시하고, 버튼 클릭 → 키조합 입력으로 매핑 편집.
3. **매핑 적용 + 배포** — Solaar 백엔드로 매핑을 영구 적용(autostart 포함)하고, 사내 누구나 원클릭 설치 가능한 패키지(AppImage/Flatpak) 제공.
   - ③-a **키 emit 적용** ✅ — "적용" 버튼 → `divert-keys` + `rules.yaml` 자동 생성 + 데몬 재시작 + 매핑 영구 저장/복원. (구현·실측 검증 완료)
   - ③-b **autostart 보장** ✅ — 적용 시 데몬 로그인 자동 실행을 보장. (`backend/autostart.py`)
   - ③-c 패키징(AppImage/Flatpak) — 미구현

### ③ 백엔드 레시피 (실측 검증됨, `backend/solaar_rules.py`)

매핑 적용 = 아래를 logitux가 자동화한다 (사용자는 그림+클릭만):
1. `~/.config/solaar/config.json`의 기기 `divert-keys`에서 매핑할 CID를 `1`로.
2. `~/.config/solaar/rules.yaml` 생성 — 매핑마다 `Key: [버튼이름, pressed]` → `KeyPress: [keysym…]`.
   - `Key`는 CID 숫자가 아니라 **Solaar 키 이름**(`special_keys.CONTROL[cid]`). 예 195→"Mouse Gesture Button".
   - **이름이 `unknown:*`인 버튼(MX4 액션버튼 CID 416)은 rules.yaml로 매핑 불가** → 적용 시 자동 skip. 별도 처리 과제로 남김.
   - `KeyPress`는 X11 keysym 이름. Qt `"Ctrl+Alt+S"` → `["Control_L","Alt_L","s"]` 변환은 `backend/keysyms.py`(공백="space", 기호="plus"/"slash" 등 X11 이름 규칙).
3. `solaar --window=hide` 데몬 상시 실행. **순서 주의**: 데몬 정지 → config/rules 기록 → 데몬 시작 (떠 있으면 종료 시 config.json을 덮어씀).
4. 매핑은 `~/.config/logitux/mappings.json`(기기 시리얼별)에 저장 → 다음 실행 시 복원.
5. **autostart 보장** (`backend/autostart.py`): 대부분 배포판은 solaar 패키지가 시스템
   autostart(`/etc/xdg/autostart/solaar.desktop`, `Exec=solaar --window=hide`)를 이미 제공.
   logitux는 이게 **꺼져 있거나 없을 때만** 사용자 autostart(`~/.config/autostart/solaar.desktop`,
   같은 파일명 → XDG 오버라이드)를 만들어 보장. 시스템 항목은 건드리지 않음.
   상태: `system`(시스템만) / `user`(사용자 활성) / `disabled`(사용자가 끔) / `missing`.

**함정**: 데몬을 셸 자식으로 띄우고 `pkill -f "solaar --window"` 하면 패턴이 자기 명령줄과 겹쳐 셸이 죽는다(exit 144). PID(`pgrep -f bin/solaar`) + `os.kill`, 시작은 `start_new_session=True`로 분리.

**한계**: Solaar `KeyPress`는 XTEST 기반 → Wayland에서 emit 안 될 수 있음. `display_server()`로 감지해 경고.

## Constraints

- 리눅스 대상 — X11 / Wayland 모두 지원 (디스플레이 서버 의존 코드는 분기).
- Solaar를 백엔드로 의존 (매핑 엔진 자체를 새로 만들지 않음).
- 비기술자 사용성 — Solaar 룰 편집 등 복잡한 과정을 사용자에게 노출하지 않음.
- 원클릭 설치 — 사내 배포가 목적이므로 설치 장벽을 최소화.
- MX 시리즈는 온보드 저장이 없어 매핑 변환 소프트웨어 상시 실행 전제.

## Domain

- **Solaar / HID++** — 로지텍 무선 기기 제어 프로토콜 및 리눅스 도구. 매핑 엔진의 기반.
- **libratbag / ratbagd** — 대안 마우스 설정 D-Bus 데몬 (참고).
- **evdev / uinput** — 입력 이벤트 감지 및 가상 입력 생성 (필요 시).
- **PySide6 / Qt** — GUI. `QGraphicsView`로 도식 + 핫스팟 오버레이.
- **SVG 도식 + 좌표 메타데이터** — 모델별 버튼 위치 데이터.

## Avoid

- **Solaar 룰 직접 편집을 UI에 노출** — 백엔드 디테일은 숨긴다.
- **MX 마우스 온보드 저장 가정** — MX Master는 온보드 메모리 없음 (G 게이밍 시리즈 전용 기능).
- **마우스 모델 하드코딩** — SVG+좌표 데이터로 외부화, 코드 수정 없이 모델 추가.
- **절대 경로 하드코딩** — `__file__`/환경변수/설정 파일 사용.
- **X11 전용 가정** — Wayland 사용자도 1급 대상.

## 결정 기록

- **언어/스택**: Python + PySide6 (기존 사내 도구와 일관, evdev/HID++ 라이브러리 풍부).
- **방식**: 처음부터 만들지 않고 Solaar 위에 시각화 GUI를 얹는 컴패니언 방식 (바퀴 재발명 회피, MX 특수버튼 커버).
- **계정/저장소**: glowElephant/logitux (public).
