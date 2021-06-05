#!/bin/bash
set -ev

docker pull zebralucky/electrum-dash-winebuild:Linux40x

docker pull zebralucky/electrum-dash-winebuild:AppImage40x

docker pull zebralucky/electrum-dash-winebuild:Wine41x
