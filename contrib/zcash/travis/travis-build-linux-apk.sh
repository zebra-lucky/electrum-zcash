#!/bin/bash
set -ev

if [[ $ELECTRUM_MAINNET == "true" ]] && [[ -z $IS_RELEASE ]]; then
    # do not build mainnet apk if is not release
    exit 0
fi

cd build
if [[ -n $TRAVIS_TAG ]]; then
    BUILD_REPO_URL=https://github.com/akhavr/electrum-zcash.git
    git clone --branch $TRAVIS_TAG $BUILD_REPO_URL electrum-zcash
else
    git clone .. electrum-zcash
fi


pushd electrum-zcash
./contrib/make_locale
find . -name '*.po' -delete
find . -name '*.pot' -delete
popd

# patch buildozer to support APK_VERSION_CODE env
VERCODE_PATCH_PATH=/home/buildozer/build/contrib/zcash/travis
VERCODE_PATCH="$VERCODE_PATCH_PATH/read_apk_version_code.patch"

DOCKER_CMD="pushd /opt/buildozer"
DOCKER_CMD="$DOCKER_CMD && patch -p0 < $VERCODE_PATCH && popd"
DOCKER_CMD="$DOCKER_CMD && rm -rf packages"
DOCKER_CMD="$DOCKER_CMD && ./contrib/make_packages"
DOCKER_CMD="$DOCKER_CMD && rm -rf packages/bls_py"
DOCKER_CMD="$DOCKER_CMD && rm -rf packages/python_bls*"
DOCKER_CMD="$DOCKER_CMD && ./contrib/make_apk"

if [[ $ELECTRUM_MAINNET == "false" ]]; then
    DOCKER_CMD="$DOCKER_CMD release-testnet"
fi

sudo chown -R 1000 electrum-zcash
docker run --rm \
    --env APP_ANDROID_ARCH=$APP_ANDROID_ARCH \
    --env APK_VERSION_CODE=$ELECTRUM_ZCASH_VERSION_CODE \
    -v $(pwd)/electrum-zcash:/home/buildozer/build \
    -t zebralucky/electrum-zcash-winebuild:Kivy33x bash -c \
    "$DOCKER_CMD"

FNAME_TAIL=release-unsigned.apk
if [[ $ELECTRUM_MAINNET == "false" ]]; then
  PATHNAME_START=electrum-zcash/bin/Electrum_Zcash_Testnet
else
  PATHNAME_START=electrum-zcash/bin/Electrum_Zcash
fi

sudo mv $PATHNAME_START-$ELECTRUM_ZCASH_APK_VERSION-$FNAME_TAIL \
  $PATHNAME_START-$ELECTRUM_ZCASH_APK_VERSION-$APP_ANDROID_ARCH-$FNAME_TAIL
