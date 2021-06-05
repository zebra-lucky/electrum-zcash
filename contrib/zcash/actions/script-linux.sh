#!/bin/bash
set -ev

mkdir -p dist
docker run --rm \
    -v $(pwd):/opt \
    -w /opt/ \
    -t zebralucky/electrum-dash-winebuild:Linux40x \
    /opt/contrib/build-linux/sdist/build.sh


sudo find . -name '*.po' -delete
sudo find . -name '*.pot' -delete


docker run --rm \
    -v $(pwd):/opt \
    -w /opt/contrib/build-linux/appimage \
    -t zebralucky/electrum-dash-winebuild:AppImage40x ./build.sh


BUILD_DIR=/root/build
TOR_PROXY_VERSION=0.4.5.7
TOR_PROXY_PATH=https://github.com/zebra-lucky/tor-proxy/releases/download
TOR_DIST=dist/tor-proxy-setup.exe

TOR_FILE=${TOR_PROXY_VERSION}/tor-proxy-${TOR_PROXY_VERSION}-win32-setup.exe
wget -O ${TOR_DIST} ${TOR_PROXY_PATH}/${TOR_FILE}
TOR_SHA=233ee2c8f4cbab6ffff74479156d91929564e7af8f9ff614e793f59fb51ac0f3
echo "$TOR_SHA  $TOR_DIST" > sha256.txt
shasum -a256 -s -c sha256.txt


export WINEARCH=win32
export WINEPREFIX=/root/.wine-32
export PYHOME=$WINEPREFIX/drive_c/Python38


ZBARW_PATH=https://github.com/zebra-lucky/zbarw/releases/download/20180620
ZBARW_FILE=zbarw-zbarcam-0.10-win32.zip
ZBARW_SHA=eed1af99d68a1f9eab975843071bf088735cb79bf3188d511d06a3f1b4e10243
wget ${ZBARW_PATH}/${ZBARW_FILE}
echo "$ZBARW_SHA  $ZBARW_FILE" > sha256.txt
shasum -a256 -s -c sha256.txt
unzip ${ZBARW_FILE} && rm ${ZBARW_FILE} sha256.txt

X11_HASH_PATH=https://github.com/zebra-lucky/x11_hash/releases/download/1.4.1
X11_HASH_FILE=x11_hash-1.4.1-win32.zip
X11_HASH_SHA=66e7a97fc4afd8b0b95c771dd1f03d216cd5ca315dc3966714b8afe093405507
wget ${X11_HASH_PATH}/${X11_HASH_FILE}
echo "$X11_HASH_SHA  $X11_HASH_FILE" > sha256.txt
shasum -a256 -s -c sha256.txt
unzip ${X11_HASH_FILE} && rm ${X11_HASH_FILE} sha256.txt

LSECP256K1_PATH=https://github.com/zebra-lucky/secp256k1/releases/download/
LSECP256K1_VER=210521
LSECP256K1_PATH=${LSECP256K1_PATH}${LSECP256K1_VER}
LSECP256K1_FILE=libsecp256k1-${LSECP256K1_VER}-win32.zip
LSECP256K1_SHA=f3f52750b2b1f0821eccf3ffd296af929b6f5488659ec51f18fad9a85c9df331
wget ${LSECP256K1_PATH}/${LSECP256K1_FILE}
echo "$LSECP256K1_SHA  $LSECP256K1_FILE" > sha256.txt
shasum -a256 -s -c sha256.txt
unzip ${LSECP256K1_FILE} && rm ${LSECP256K1_FILE} sha256.txt

PINST_PATH=https://github.com/zebra-lucky/PyInstaller/releases/download/
PINST_PATH=${PINST_PATH}v4.2_build_wheels
PINST_FILE=pyinstaller-4.2-cp38-cp38-win32.whl
PINST_SHA=59a2334e7d28c22d2d3aaf9232976ad2b6b9d3aa944d5f83c6f517c2580e8681
wget -O dist/${PINST_FILE} ${PINST_PATH}/${PINST_FILE}
echo "$PINST_SHA  dist/$PINST_FILE" > sha256.txt
shasum -a256 -s -c sha256.txt
rm sha256.txt


docker run --rm \
    -e WINEARCH=$WINEARCH \
    -e WINEPREFIX=$WINEPREFIX \
    -e PYHOME=$PYHOME \
    -e BUILD_DIR=$BUILD_DIR \
    -v $(pwd):$BUILD_DIR \
    -v $(pwd):$WINEPREFIX/drive_c/electrum-zcash \
    -w $BUILD_DIR \
    -t zebralucky/electrum-dash-winebuild:Wine41x \
    $BUILD_DIR/contrib/build-wine/build.sh


export WINEARCH=win64
export WINEPREFIX=/root/.wine-64
export PYHOME=$WINEPREFIX/drive_c/Python38


ZBARW_FILE=zbarw-zbarcam-0.10-win64.zip
ZBARW_SHA=7705dfd9a1c4b9d07c9ae11502dbe2dc305d08c884f0825b35d21b312316e162
wget ${ZBARW_PATH}/${ZBARW_FILE}
echo "$ZBARW_SHA  $ZBARW_FILE" > sha256.txt
shasum -a256 -s -c sha256.txt
unzip ${ZBARW_FILE} && rm ${ZBARW_FILE} sha256.txt

X11_HASH_FILE=x11_hash-1.4.1-win64.zip
X11_HASH_SHA=1b2b6e9ba41c9b090910f8f480ed372f16c09d4bdc590f086b3cae2d7a23946e
wget ${X11_HASH_PATH}/${X11_HASH_FILE}
echo "$X11_HASH_SHA  $X11_HASH_FILE" > sha256.txt
shasum -a256 -s -c sha256.txt
unzip ${X11_HASH_FILE} && rm ${X11_HASH_FILE} sha256.txt

LSECP256K1_FILE=libsecp256k1-${LSECP256K1_VER}-win64.zip
LSECP256K1_SHA=ea8722dcd35990f933bb0131de878013e6b6ce04783df4fb4b34dcc4628f2929
wget ${LSECP256K1_PATH}/${LSECP256K1_FILE}
echo "$LSECP256K1_SHA  $LSECP256K1_FILE" > sha256.txt
shasum -a256 -s -c sha256.txt
unzip ${LSECP256K1_FILE} && rm ${LSECP256K1_FILE} sha256.txt

rm ${TOR_DIST}
TOR_FILE=${TOR_PROXY_VERSION}/tor-proxy-${TOR_PROXY_VERSION}-win64-setup.exe
wget -O ${TOR_DIST} ${TOR_PROXY_PATH}/${TOR_FILE}
TOR_SHA=514387e3b45eccd9b98e95450ea201ced49886cc4f0980d4f0f6f7a4a51aebe9
echo "$TOR_SHA  $TOR_DIST" > sha256.txt
shasum -a256 -s -c sha256.txt
rm sha256.txt

PINST_FILE=pyinstaller-4.2-cp38-cp38-win_amd64.whl
PINST_SHA=1643595ef49936b8787fb32b68fece8c5f79b7dcc25e1c29bb3a6652d1bd55da
wget -O dist/${PINST_FILE} ${PINST_PATH}/${PINST_FILE}
echo "$PINST_SHA  dist/$PINST_FILE" > sha256.txt
shasum -a256 -s -c sha256.txt
rm sha256.txt


docker run --rm \
    -e WINEARCH=$WINEARCH \
    -e WINEPREFIX=$WINEPREFIX \
    -e PYHOME=$PYHOME \
    -e BUILD_DIR=$BUILD_DIR \
    -v $(pwd):$BUILD_DIR \
    -v $(pwd):$WINEPREFIX/drive_c/electrum-zcash \
    -w $BUILD_DIR \
    -t zebralucky/electrum-dash-winebuild:Wine41x \
    $BUILD_DIR/contrib/build-wine/build.sh
