#!/bin/bash

VERSION_STRING=(`grep ELECTRUM_VERSION electrum_zcash/version.py`)
ZCASH_ELECTRUM_VERSION=${VERSION_STRING[2]}
ZCASH_ELECTRUM_VERSION=${ZCASH_ELECTRUM_VERSION#\'}
ZCASH_ELECTRUM_VERSION=${ZCASH_ELECTRUM_VERSION%\'}
export ZCASH_ELECTRUM_VERSION

APK_VERSION_STRING=(`grep APK_VERSION electrum_zcash/version.py`)
ZCASH_ELECTRUM_APK_VERSION=${APK_VERSION_STRING[2]}
ZCASH_ELECTRUM_APK_VERSION=${ZCASH_ELECTRUM_APK_VERSION#\'}
ZCASH_ELECTRUM_APK_VERSION=${ZCASH_ELECTRUM_APK_VERSION%\'}
export ZCASH_ELECTRUM_APK_VERSION

APK_VERSION_CODE_SCRIPT='./contrib/zcash/calc_version_code.py'
export ZCASH_ELECTRUM_VERSION_CODE=`$APK_VERSION_CODE_SCRIPT`

# Check is release
SIMPLIFIED_VERSION_PATTERN="^([^A-Za-z]+).*"
if [[ ${ZCASH_ELECTRUM_VERSION} =~ ${SIMPLIFIED_VERSION_PATTERN} ]]; then
    if [[ ${BASH_REMATCH[1]} == ${ZCASH_ELECTRUM_VERSION} ]]; then
        export IS_RELEASE=y
    fi
fi