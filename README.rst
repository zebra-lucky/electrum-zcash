Electrum-Zcash - Lightweight Zcash client
=====================================

::

  Licence: MIT Licence
  Author: Thomas Voegtlin
  Language: Python (>= 3.6)
  Homepage: https://github.com/zebra-lucky/electrum-zcash/


.. image:: https://travis-ci.org/akhavr/electrum-zcash.svg?branch=master
    :target: https://travis-ci.org/akhavr/electrum-zcash
    :alt: Build Status





Getting started
===============


Use PPA setup
-------------

On Ubuntu/Linux Mint you can try to install Electrum-Zcash with next commands::

    sudo add-apt-repository ppa:zebra-lucky/zcash-electrum
    sudo apt-get update
    sudo apt-get install electrum-zcash


Use source distribution
-----------------------

Electrum-Zcash is a pure python application. If you want to use the
Qt interface, install the Qt dependencies::

    sudo apt-get install python3-pyqt5

If you downloaded the official package (tar.gz), you can run
Electrum-Zcash from its root directory without installing it on your
system; all the python dependencies are included in the 'packages'
directory (except x11-hash).

To install x11-hash dependency in the 'packages' dir run once::

    python3 -m pip install -t packages x11-hash

To install precise tested versions of HW libs (trezor, ledeger, etc) run once::

    python3 -m pip install -t packages -r contrib/deterministic-build/requirements-hw.txt

To install precise tested version of pyqt5 run once::

    python3 -m pip install -t packages -r contrib/deterministic-build/requirements-binaries.txt

To run Electrum-Zcash from its root directory, just do::

    ./electrum-zcash

You can also install Electrum-Zcash on your system, by running this command::

    sudo apt-get install python3-setuptools
    python3 -m pip install .[fast]

This will download and install the Python dependencies used by
Electrum-Zcash instead of using the 'packages' directory.
The 'fast' extra contains some optional dependencies that we think
are often useful but they are not strictly needed.

If you cloned the git repository, you need to compile extra files
before you can run Electrum-Zcash. Read the next section, "Development
Version".


Using Tor proxy
===============

Starting from Electrum-Zcash release 3.2.3.1 automatic Tor Proxy
detection and use on wallet startup is added to
`Network <docs/tor/tor-proxy-on-startup.md>`_ preferences.

To use Tor Proxy on Ubuntu set it up with::

    sudo apt-get install tor
    sudo service tor start

Other platforms setup is described at `docs/tor.md <docs/tor.md>`_

Development version
===================

Check out the code from GitHub::

    git clone https://github.com/akhavr/electrum-zcash.git
    cd electrum-zcash

Run install (this should install dependencies)::

    python3 -m pip install .[fast]


Compile the protobuf description file::

    sudo apt-get install protobuf-compiler
    protoc --proto_path=electrum_zcash --python_out=electrum_zcash electrum_zcash/paymentrequest.proto

Create translations (optional)::

    sudo apt-get install python-requests gettext
    ./contrib/make_locale
