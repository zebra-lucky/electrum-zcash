#!/bin/bash

VERSION_STRING=(`grep ELECTRUM_VERSION lib/version.py`)
ELECTRUM_ZCASH_VERSION=${VERSION_STRING[2]}
ELECTRUM_ZCASH_VERSION=${ELECTRUM_ZCASH_VERSION#\'}
ELECTRUM_ZCASH_VERSION=${ELECTRUM_ZCASH_VERSION%\'}
DOTS=`echo $ELECTRUM_ZCASH_VERSION |  grep -o "\." | wc -l`
if [[ $DOTS -lt 3 ]]; then
    ELECTRUM_ZCASH_APK_VERSION=$ELECTRUM_ZCASH_VERSION.0
else
    ELECTRUM_ZCASH_APK_VERSION=$ELECTRUM_ZCASH_VERSION
fi
export ELECTRUM_ZCASH_VERSION
export ELECTRUM_ZCASH_APK_VERSION
