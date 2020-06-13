#!/bin/bash
set -ev

docker pull zebralucky/electrum-zcash-winebuild:LinuxPy36

docker pull zebralucky/electrum-zcash-winebuild:LinuxAppImage

docker pull zebralucky/electrum-zcash-winebuild:WinePy36
