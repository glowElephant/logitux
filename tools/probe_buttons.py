#!/usr/bin/env python3
"""버튼 누름 실측 진단 — 어떤 물리 버튼이 어떤 CID를 내는지 실시간 확인.

매핑 가능(divertable) 버튼을 잠시 divert하고 HID++ 누름 이벤트의 CID를 출력한다.
좌/우 클릭은 divertable이 아니라 건드리지 않으므로 마우스는 계속 사용 가능.
종료 시 divert를 원래대로 복구한다. (개발용 도구)

⚠️ WIP / 알려진 한계:
  divert 적용·복구는 정상 동작하지만, `base.read()` 단순 폴링으로는 divert
  누름 notification을 수신하지 못했다(빈손). Solaar는 전용 리스너 스레드
  (logitech_receiver의 EventsListener)로 notification을 받는 구조라,
  제대로 하려면 그 리스너를 띄워 콜백을 받아야 한다. 단순 base.read 폴링은
  receiver 핸들에서 notification을 못 가져온다. 다음에 이 도구를 고친다면
  EventsListener 기반으로 재작성할 것.
"""
import sys
import time

sys.path.insert(0, "/usr/share/solaar/lib")
import logging

logging.getLogger("logitech_receiver").setLevel(logging.CRITICAL)

from logitech_receiver import Receiver, base

CID_NAMES = {
    80: "좌클릭", 81: "우클릭", 82: "휠클릭", 83: "뒤로", 86: "앞으로",
    195: "제스처", 196: "휠모드전환", 215: "가상제스처", 416: "액션버튼(추정)",
}

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 25


def find_mouse():
    for info in base.receivers():
        r = Receiver.open(info)
        if not r:
            continue
        for d in r:
            if d and str(getattr(d, "kind", "")) == "mouse":
                return d
    return None


def main() -> int:
    dev = find_mouse()
    if not dev:
        print("마우스를 찾지 못했습니다.")
        return 1
    print(f"기기: {dev.codename}")

    # Bolt/Unifying 리시버 경유 기기는 리시버 핸들로 읽는다
    handle = getattr(dev, "handle", None)
    if not handle and getattr(dev, "receiver", None):
        handle = dev.receiver.handle
    if not handle:
        print("읽기 핸들을 얻지 못했습니다.")
        return 1

    diverted = []
    try:
        for k in dev.keys:
            if "divertable" in set(k.flags):
                try:
                    k.set_diverted(True)
                    diverted.append(k)
                except Exception as e:
                    print(f"  divert 실패 CID={int(k.key)}: {e}")
        print(f"{len(diverted)}개 버튼 divert 완료.")
        print("=" * 56)
        print(f"지금 마우스의 '액션 버튼'(엄지쪽 햅틱 패널)을 눌러보세요. ({SECONDS}초)")
        print("뒤로/앞으로/제스처/휠클릭 등 다른 버튼도 눌러 비교해보세요.")
        print("=" * 56)

        end = time.time() + SECONDS
        last = None
        while time.time() < end:
            reply = base.read(handle, 400)
            if not reply:
                continue
            try:
                _report_id, devnum, data = reply
            except Exception:
                continue
            if devnum != dev.number:
                continue
            b = bytes(data)
            if len(b) < 3:
                continue
            # 모든 notification raw 출력 (진단)
            print(f"  raw[{len(b)}] {b.hex()}")
            # CID 디코드 시도 (data[1:]을 2바이트씩)
            cids = []
            for i in range(1, min(len(b), 11), 2):
                if i + 1 >= len(b):
                    break
                cid = (b[i] << 8) | b[i + 1]
                if cid in CID_NAMES:
                    cids.append(cid)
            if cids:
                names = [f"CID {c}={CID_NAMES[c]}" for c in cids]
                print("     ▶ 추정 버튼:", ", ".join(names))
    finally:
        for k in diverted:
            try:
                k.set_diverted(False)
            except Exception:
                pass
        print("=" * 56)
        print("divert 복구 완료 — 마우스 버튼 정상화됨.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
