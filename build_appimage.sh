#!/usr/bin/env bash
# Build Thattan as a portable AppImage.
# Run from project root: ./build_appimage.sh
#
# Prerequisites (from project root):
#   pip install -r requirements.txt
#   pip install pyinstaller
# Then run: ./build_appimage.sh
# Output: release/Thattan-x86_64.AppImage

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="Thattan"
ARCH="x86_64"

# Pinned appimagetool release (commit 8c8c91f, 2025-12-04)
# https://github.com/AppImage/appimagetool/releases/tag/continuous
APPIMAGETOOL_VERSION="1.9.1"  # pinned to known-good build below
APPIMAGE_TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-${ARCH}.AppImage"
APPIMAGE_TOOL_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
RELEASE_DIR="release"
OUTPUT_APPIMAGE="${RELEASE_DIR}/${APP_NAME}-${ARCH}.AppImage"

echo "==> Cleaning previous build..."
rm -rf build dist "AppDir"
mkdir -p "$RELEASE_DIR"
mkdir -p AppDir

echo "==> Building with PyInstaller (one-dir for AppImage)..."
pyinstaller --noconfirm --clean thattan.spec

echo "==> Creating AppDir layout..."
# PyInstaller one-dir output goes to dist/Thattan/
INSTALL_DIR="AppDir/usr/share/${APP_NAME,,}"
mkdir -p "$INSTALL_DIR"
cp -a "dist/${APP_NAME}"/* "$INSTALL_DIR/"

# AppRun: run the bundled executable
cat > AppDir/AppRun << 'APPRUN'
#!/usr/bin/env bash
set -e
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/share/thattan/Thattan" "$@"
APPRUN
chmod +x AppDir/AppRun

# .desktop file at AppDir root (for appimagetool) and in usr/share/applications (for desktop integration)
DESKTOP_CONTENT="[Desktop Entry]
Type=Application
Name=Thattan
GenericName=Tamil99 Typing Tool
Comment=Tamil99 Typing Learning Assistant
Exec=Thattan
Icon=thattan
Terminal=false
Categories=Utility;Education;
StartupWMClass=Thattan
"
echo "$DESKTOP_CONTENT" > "AppDir/${APP_NAME}.desktop"
mkdir -p AppDir/usr/share/applications
echo "$DESKTOP_CONTENT" > "AppDir/usr/share/applications/${APP_NAME}.desktop"

# Copy icon for .desktop (use PNG for compatibility)
ICON_SRC="thattan/assets/logo/logo_256.png"
if [[ -f "$ICON_SRC" ]]; then
  mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps
  cp "$ICON_SRC" "AppDir/usr/share/icons/hicolor/256x256/apps/thattan.png"
  cp "$ICON_SRC" "AppDir/thattan.png"
fi

echo "==> Verifying appimagetool (builder)..."
APPIMAGETOOL_BIN="appimagetool-${ARCH}.AppImage"

verify_checksum() {
  local file="$1"
  local expected="$2"
  local actual
  actual="$(sha256sum "$file" | cut -d' ' -f1)"
  if [[ "$actual" != "$expected" ]]; then
    echo "    CHECKSUM MISMATCH for $file"
    echo "    Expected: $expected"
    echo "    Got:      $actual"
    echo "    Delete $file and check the URL or update the pinned hash."
    return 1
  fi
  echo "    Checksum OK ($actual)"
  return 0
}

if [[ -f "$APPIMAGETOOL_BIN" ]] && verify_checksum "$APPIMAGETOOL_BIN" "$APPIMAGE_TOOL_SHA256"; then
  echo "    Using cached $APPIMAGETOOL_BIN"
else
  echo "    Downloading $APPIMAGE_TOOL_URL"
  curl -sL -o "$APPIMAGETOOL_BIN" "$APPIMAGE_TOOL_URL"
  if ! verify_checksum "$APPIMAGETOOL_BIN" "$APPIMAGE_TOOL_SHA256"; then
    echo "    ERROR: Downloaded file does not match pinned SHA-256. Aborting."
    rm -f "$APPIMAGETOOL_BIN"
    exit 1
  fi
  chmod +x "$APPIMAGETOOL_BIN"
fi
APPIMAGETOOL="./$APPIMAGETOOL_BIN"

echo "==> Building AppImage..."
# ARCH is required so appimagetool picks the right runtime for the AppDir
export ARCH=x86_64
"$APPIMAGETOOL" AppDir "$OUTPUT_APPIMAGE"

echo ""
echo "==> Done: $OUTPUT_APPIMAGE"
echo "    Run: ./$OUTPUT_APPIMAGE"
