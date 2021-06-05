#!/bin/bash
set -ev

export MACOSX_DEPLOYMENT_TARGET=10.12

export PY37BINDIR=/Library/Frameworks/Python.framework/Versions/3.7/bin/
export PATH=$PATH:$PY37BINDIR
echo osx build version is $ZCASH_ELECTRUM_VERSION


if [[ -n $GITHUB_REF ]]; then
    PIP_CMD="sudo python3 -m pip"
else
    python3 -m virtualenv env
    source env/bin/activate
    PIP_CMD="pip"
fi


if [[ -n $GITHUB_REF ]]; then
    git submodule init
    git submodule update

    echo "Building CalinsQRReader..."
    d=contrib/CalinsQRReader
    pushd $d
    rm -fr build
    xcodebuild || fail "Could not build CalinsQRReader"
    popd
fi


$PIP_CMD install --no-dependencies --no-warn-script-location -I \
    -r contrib/deterministic-build/requirements.txt
$PIP_CMD install --no-dependencies --no-warn-script-location -I \
    -r contrib/deterministic-build/requirements-hw.txt
$PIP_CMD install --no-dependencies --no-warn-script-location -I \
    -r contrib/deterministic-build/requirements-binaries-mac.txt
$PIP_CMD install --no-dependencies --no-warn-script-location -I x11_hash>=1.4

$PIP_CMD install --no-dependencies --no-warn-script-location -I \
    -r contrib/deterministic-build/requirements-build-mac.txt

export PATH="/usr/local/opt/gettext/bin:$PATH"
./contrib/make_locale
find . -name '*.po' -delete
find . -name '*.pot' -delete

cp contrib/osx/osx_actions.spec osx.spec
cp contrib/zcash/pyi_runtimehook.py .
cp contrib/zcash/pyi_tctl_runtimehook.py .

pyinstaller --clean \
    -y \
    --name electrum-zcash-$ZCASH_ELECTRUM_VERSION.bin \
    osx.spec

sudo hdiutil create -fs HFS+ -volname "Zcash Electrum" \
    -srcfolder dist/Zcash\ Electrum.app \
    dist/Zcash-Electrum-$ZCASH_ELECTRUM_VERSION-macosx.dmg
