#!/usr/bin/env bash
# Build Thattan as a portable AppImage.
# Run from project root: ./build_appimage.sh
#
# Prerequisites (from project root):
#   pip install -r requirements.txt
#   pip install pyinstaller
# Then run: ./build_appimage.sh
# Output: Thattan-x86_64.AppImage (run with: ./Thattan-x86_64.AppImage)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="Thattan"
ARCH="x86_64"
# New appimagetool repo (AppImageKit is obsolete)
APPIMAGE_TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
OUTPUT_APPIMAGE="${APP_NAME}-${ARCH}.AppImage"

echo "==> Cleaning previous build..."
rm -rf build dist "AppDir"
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

echo "==> Downloading appimagetool (builder) if needed..."
# Use builder tool only (appimagetool), not appimageupdatetool. Save under a distinct name.
APPIMAGETOOL_BIN="appimagetool-build-${ARCH}.AppImage"
if [[ ! -f "$APPIMAGETOOL_BIN" ]] || ! file "$APPIMAGETOOL_BIN" | grep -qE "ELF|executable|AppImage"; then
  echo "    Fetching $APPIMAGE_TOOL_URL"
  curl -sL -o "$APPIMAGETOOL_BIN" "$APPIMAGE_TOOL_URL"
  if ! file "$APPIMAGETOOL_BIN" | grep -qE "ELF|executable|AppImage"; then
    echo "    ERROR: Download did not get a valid AppImage (got HTML or error page). Check the URL or network."
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
echo "    Or make executable and run: chmod +x $OUTPUT_APPIMAGE && ./$OUTPUT_APPIMAGE"
