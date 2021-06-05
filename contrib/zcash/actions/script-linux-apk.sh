#!/bin/bash
set -ev

./contrib/make_locale
find . -name '*.po' -delete
find . -name '*.pot' -delete

# patch buildozer to support APK_VERSION_CODE env
VERCODE_PATCH_PATH=/home/buildozer/build/contrib/zcash
VERCODE_PATCH="$VERCODE_PATCH_PATH/read_apk_version_code.patch"

DOCKER_CMD="pushd /opt/buildozer"
# commit: from branch sombernight/202104_android_adaptiveicon
DOCKER_CMD="$DOCKER_CMD && git fetch --all"
DOCKER_CMD="$DOCKER_CMD && git checkout 'c17ac3618334c9936253e8f5b88dce43dc4da75b^{commit}'"
DOCKER_CMD="$DOCKER_CMD && patch -p0 < $VERCODE_PATCH && popd"
DOCKER_CMD="$DOCKER_CMD && pushd /opt/python-for-android"
DOCKER_CMD="$DOCKER_CMD && git fetch --all"
# commit: android: add support for adaptive icon/launcher
DOCKER_CMD="$DOCKER_CMD && git checkout '5356bc7838b03c8c174c91fe01539c91d1b40b9f^{commit}'"
DOCKER_CMD="$DOCKER_CMD && git revert --no-edit '257cfacbdd523af0b5b6bb5b2ba64ab7a5c82d58'"
DOCKER_CMD="$DOCKER_CMD && popd"
DOCKER_CMD="$DOCKER_CMD && rm -rf packages"
DOCKER_CMD="$DOCKER_CMD && ./contrib/make_packages"
DOCKER_CMD="$DOCKER_CMD && rm -rf packages/bls_py"
DOCKER_CMD="$DOCKER_CMD && rm -rf packages/python_bls*"
DOCKER_CMD="$DOCKER_CMD && ./contrib/android/make_apk"

if [[ $ELECTRUM_MAINNET == "false" ]]; then
    DOCKER_CMD="$DOCKER_CMD release-testnet"
fi

sudo chown -R 1000 .
docker run --rm \
    --env APP_ANDROID_ARCH=$APP_ANDROID_ARCH \
    --env APK_VERSION_CODE=$ZCASH_ELECTRUM_VERSION_CODE \
    -v $(pwd):/home/buildozer/build \
    -t zebralucky/electrum-dash-winebuild:Kivy40x bash -c \
    "$DOCKER_CMD"
