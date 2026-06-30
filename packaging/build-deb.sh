#!/usr/bin/env bash
# logitux .deb 패키지 빌드. fakeroot 없이 --root-owner-group 사용.
# 사용법: packaging/build-deb.sh [버전]   (기본 0.1.0)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
VERSION="${1:-0.1.0}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
PKG="$STAGE/logitux"

# 디렉토리 레이아웃
mkdir -p "$PKG/DEBIAN" \
         "$PKG/usr/share/logitux" \
         "$PKG/usr/bin" \
         "$PKG/usr/share/applications" \
         "$PKG/usr/share/icons/hicolor/scalable/apps"

# 앱 코드 (logitux 패키지 + main.py). __pycache__/.pyc 제외.
cp -r "$ROOT/logitux" "$PKG/usr/share/logitux/"
cp "$ROOT/main.py" "$PKG/usr/share/logitux/"
find "$PKG/usr/share/logitux" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$PKG/usr/share/logitux" -type f -name '*.pyc' -delete 2>/dev/null || true

# 실행 래퍼 / desktop / 아이콘
install -m 755 "$HERE/logitux"          "$PKG/usr/bin/logitux"
install -m 644 "$HERE/logitux.desktop"  "$PKG/usr/share/applications/logitux.desktop"
install -m 644 "$HERE/logitux.svg"      "$PKG/usr/share/icons/hicolor/scalable/apps/logitux.svg"

# control (Installed-Size = KB)
SIZE="$(du -sk "$PKG/usr" | cut -f1)"
cat > "$PKG/DEBIAN/control" <<EOF
Package: logitux
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: solaar, python3 (>= 3.10), python3-pip
Installed-Size: $SIZE
Maintainer: glowElephant <gksdk1029@gmail.com>
Homepage: https://github.com/glowElephant/logitux
Description: 리눅스용 로지텍 마우스 버튼 매퍼 (Logi Options+ 대안)
 마우스 도식을 보고 클릭만으로 버튼에 단축키를 매핑한다.
 Solaar(HID++)를 백엔드로 활용하며 MX Master 3/4를 지원한다.
 GUI 라이브러리(PySide6)는 설치 후 pip로 자동 설치된다.
EOF

# postinst
install -m 755 "$HERE/postinst" "$PKG/DEBIAN/postinst"

# 빌드
mkdir -p "$ROOT/dist"
OUT="$ROOT/dist/logitux_${VERSION}_all.deb"
dpkg-deb --root-owner-group --build "$PKG" "$OUT"
echo "빌드 완료: $OUT"
