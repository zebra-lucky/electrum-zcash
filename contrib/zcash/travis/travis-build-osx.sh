#!/bin/bash
set -ev

export PY36BINDIR=/Library/Frameworks/Python.framework/Versions/3.6/bin/
export PATH=$PATH:$PY36BINDIR
source ./contrib/zcash/travis/electrum_zcash_version_env.sh;
echo osx build version is $ELECTRUM_ZCASH_VERSION


cd build
if [[ -n $TRAVIS_TAG ]]; then
    BUILD_REPO_URL=https://github.com/akhavr/electrum-zcash.git
    git clone --branch $TRAVIS_TAG $BUILD_REPO_URL electrum-zcash
    PIP_CMD="sudo python3 -m pip"
else
    git clone .. electrum-zcash
    python3 -m virtualenv env
    source env/bin/activate
    PIP_CMD="pip"
fi
cd electrum-zcash


if [[ -n $TRAVIS_TAG ]]; then
    git submodule init
    git submodule update

    echo "Building CalinsQRReader..."
    d=contrib/CalinsQRReader
    pushd $d
    rm -fr build
    xcodebuild || fail "Could not build CalinsQRReader"
    popd
fi


$PIP_CMD install --no-warn-script-location \
    -r contrib/deterministic-build/requirements.txt
$PIP_CMD install --no-warn-script-location \
    -r contrib/deterministic-build/requirements-hw.txt
$PIP_CMD install --no-warn-script-location \
    -r contrib/deterministic-build/requirements-binaries.txt
$PIP_CMD install --no-warn-script-location x11_hash>=1.4
$PIP_CMD install --no-warn-script-location PyInstaller==3.6 --no-use-pep517

export PATH="/usr/local/opt/gettext/bin:$PATH"
./contrib/make_locale
find . -name '*.po' -delete
find . -name '*.pot' -delete

cp contrib/zcash/osx.spec .
cp contrib/zcash/pyi_runtimehook.py .
cp contrib/zcash/pyi_tctl_runtimehook.py .

pyinstaller --clean \
    -y \
    --name electrum-zcash-$ELECTRUM_ZCASH_VERSION.bin \
    osx.spec

sudo hdiutil create -fs HFS+ -volname "Electrum-Zcash" \
    -srcfolder dist/Electrum-Zcash.app \
    dist/Electrum-Zcash-$ELECTRUM_ZCASH_VERSION-macosx.dmg
