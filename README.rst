Electrum-Zcash - Lightweight Zcash client
=====================================

::

  Licence: MIT Licence
  Author: Thomas Voegtlin
  Language: Python (>= 3.6)
  Homepage: https://github.com/zebra-lucky/electrum-zcash


.. image:: https://travis-ci.org/zebra-lucky/electrum-zcash.svg?branch=master
    :target: https://travis-ci.org/zebra-lucky/electrum-zcash
    :alt: Build Status





Getting started
===============

Electrum-Zcash is a pure python application. If you want to use the
Qt interface, install the Qt dependencies::

    sudo apt-get install python3-pyqt5

If you downloaded the official package (tar.gz), you can run
Electrum-Zcash from its root directory without installing it on your
system; all the python dependencies are included in the 'packages'
directory. To run Electrum-Zcash from its root directory, just do::

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



Development version
===================

Check out the code from GitHub::

    git clone git://github.com/zebra-lucky/electrum-zcash.git
    cd electrum-zcash

Run install (this should install dependencies)::

    python3 -m pip install .[fast]


Compile the protobuf description file::

    sudo apt-get install protobuf-compiler
    protoc --proto_path=electrum_zcash --python_out=electrum_zcash electrum_zcash/paymentrequest.proto

Create translations (optional)::

    sudo apt-get install python-requests gettext
    ./contrib/make_locale
