#!/bin/bash

set -ev

./contrib/make_locale
./contrib/make_packages
python3 setup.py sdist --format=zip,gztar
