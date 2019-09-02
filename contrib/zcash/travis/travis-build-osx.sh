#!/bin/bash
set -ev

if [[ -z $TRAVIS_TAG ]]; then
  echo TRAVIS_TAG unset, exiting
  exit 1
fi

BUILD_REPO_URL=https://github.com/zebra-lucky/electrum-zcash.git

cd build

git clone --branch $TRAVIS_TAG $BUILD_REPO_URL electrum-zcash

cd electrum-zcash

export PY36BINDIR=/Library/Frameworks/Python.framework/Versions/3.6/bin/
export PATH=$PATH:$PY36BINDIR
source ./contrib/zcash/travis/electrum_zcash_version_env.sh;
echo osx build version is $ELECTRUM_ZCASH_VERSION


git submodule init
git submodule update

echo "Building CalinsQRReader..."
d=contrib/CalinsQRReader
pushd $d
rm -fr build
xcodebuild || fail "Could not build CalinsQRReader"
popd

sudo pip3 install --no-warn-script-location -r contrib/deterministic-build/requirements.txt
sudo pip3 install --no-warn-script-location -r contrib/deterministic-build/requirements-hw.txt
sudo pip3 install --no-warn-script-location -r contrib/deterministic-build/requirements-binaries.txt
sudo pip3 install --no-warn-script-location PyInstaller==3.4 --no-use-pep517

export PATH="/usr/local/opt/gettext/bin:$PATH"
./contrib/make_locale
find . -name '*.po' -delete
find . -name '*.pot' -delete

cp contrib/zcash/osx.spec .
cp contrib/zcash/pyi_runtimehook.py .
cp contrib/zcash/pyi_tctl_runtimehook.py .

pyinstaller \
    -y \
    --name electrum-zcash-$ELECTRUM_ZCASH_VERSION.bin \
    osx.spec

sudo hdiutil create -fs HFS+ -volname "Electrum-Zcash" \
    -srcfolder dist/Electrum-Zcash.app \
    dist/Electrum-Zcash-$ELECTRUM_ZCASH_VERSION-macosx.dmg
