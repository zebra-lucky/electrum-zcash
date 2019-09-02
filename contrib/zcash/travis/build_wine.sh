#!/bin/bash

source ./contrib/zcash/travis/electrum_zcash_version_env.sh;
echo wine build version is $ELECTRUM_ZCASH_VERSION

mv /opt/zbarw $WINEPREFIX/drive_c/

mv /opt/libsecp256k1/libsecp256k1-0.dll \
   /opt/libsecp256k1/libsecp256k1.dll
mv /opt/libsecp256k1 $WINEPREFIX/drive_c/

cd $WINEPREFIX/drive_c/electrum-zcash

rm -rf build
rm -rf dist/electrum-zcash

cp contrib/zcash/deterministic.spec .
cp contrib/zcash/pyi_runtimehook.py .
cp contrib/zcash/pyi_tctl_runtimehook.py .

wine python -m pip install --no-warn-script-location -r contrib/deterministic-build/requirements.txt
wine python -m pip install --no-warn-script-location -r contrib/deterministic-build/requirements-hw.txt
wine python -m pip install --no-warn-script-location -r contrib/deterministic-build/requirements-binaries.txt
wine python -m pip install --no-warn-script-location PyInstaller==3.4 --no-use-pep517

wine pyinstaller -y \
    --name electrum-zcash-$ELECTRUM_ZCASH_VERSION.exe \
    deterministic.spec

if [[ $WINEARCH == win32 ]]; then
    NSIS_EXE="$WINEPREFIX/drive_c/Program Files/NSIS/makensis.exe"
else
    NSIS_EXE="$WINEPREFIX/drive_c/Program Files (x86)/NSIS/makensis.exe"
fi

wine "$NSIS_EXE" /NOCD -V3 \
    /DPRODUCT_VERSION=$ELECTRUM_ZCASH_VERSION \
    /DWINEARCH=$WINEARCH \
    contrib/zcash/electrum-zcash.nsi
