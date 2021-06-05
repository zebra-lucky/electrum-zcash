#!/bin/bash

source ./contrib/zcash/electrum_zcash_version_env.sh;
echo wine build version is $ZCASH_ELECTRUM_VERSION

mv $BUILD_DIR/zbarw $WINEPREFIX/drive_c/

mv $BUILD_DIR/x11_hash $WINEPREFIX/drive_c/

mv $BUILD_DIR/libsecp256k1 $WINEPREFIX/drive_c/

cd $WINEPREFIX/drive_c/electrum-zcash

rm -rf build
rm -rf dist/electrum-zcash

cp contrib/build-wine/deterministic.spec .
cp contrib/zcash/pyi_runtimehook.py .
cp contrib/zcash/pyi_tctl_runtimehook.py .

wine python -m pip install --no-warn-script-location dist/pyinstaller*.whl
rm dist/pyinstaller*.whl

wine python -m pip install --no-dependencies --no-warn-script-location \
    -r contrib/deterministic-build/requirements.txt
wine python -m pip install --no-dependencies --no-warn-script-location \
    -r contrib/deterministic-build/requirements-hw.txt
wine python -m pip install --no-dependencies --no-warn-script-location \
    -r contrib/deterministic-build/requirements-binaries.txt
wine python -m pip install --no-dependencies --no-warn-script-location \
    -r contrib/deterministic-build/requirements-build-wine.txt

wine pyinstaller --clean -y \
    --name electrum-zcash-$ZCASH_ELECTRUM_VERSION.exe \
    deterministic.spec

if [[ $WINEARCH == win32 ]]; then
    NSIS_EXE="$WINEPREFIX/drive_c/Program Files/NSIS/makensis.exe"
else
    NSIS_EXE="$WINEPREFIX/drive_c/Program Files (x86)/NSIS/makensis.exe"
fi

wine "$NSIS_EXE" /NOCD -V3 \
    /DPRODUCT_VERSION=$ZCASH_ELECTRUM_VERSION \
    /DWINEARCH=$WINEARCH \
    contrib/build-wine/electrum-zcash.nsi
