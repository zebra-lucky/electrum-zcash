# -*- coding: utf-8 -*-

import os
from copy import deepcopy

from PyQt5.QtCore import Qt, QRect, QPoint, QSize
from PyQt5.QtWidgets import (QTabBar, QTextEdit, QStylePainter,
                             QStyleOptionTab, QStyle, QPushButton,
                             QVBoxLayout, QHBoxLayout, QLabel, QApplication,
                             QCheckBox)

from electrum_zcash import constants
from electrum_zcash.i18n import _
from electrum_zcash.network import deserialize_proxy
from electrum_zcash.version import ELECTRUM_VERSION

from .util import WindowModalDialog


class TorWarnDialog(WindowModalDialog):

    def __init__(self, app, w_path):
        super(TorWarnDialog, self).__init__(None)
        self.app = app
        self.network = app.daemon.network
        self.config = app.config
        self.tor_detected = False
        self.setMinimumSize(600, 350)

        app_name = 'Zcash Electrum'
        if constants.net.TESTNET:
            app_name += ' Testnet'
        app_name += f' {ELECTRUM_VERSION}'
        w_basename = os.path.basename(w_path)
        self.setWindowTitle(f'{app_name}  -  {w_basename}')

        vbox = QVBoxLayout(self)
        vbox.setSpacing(10)
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)

        w_icon = QApplication.style().standardIcon(QStyle.SP_MessageBoxWarning)
        self.w_icn_lbl = QLabel()
        self.w_icn_lbl.setPixmap(w_icon.pixmap(36))
        self.w_lbl = QLabel(self.network.TOR_WARN_MSG_QT)
        self.w_lbl.setOpenExternalLinks(True)
        hbox.addWidget(self.w_icn_lbl)
        hbox.addWidget(self.w_lbl)
        hbox.setSpacing(10)
        hbox.addStretch(1)
        vbox.addStretch(1)

        self.tor_auto_on_cb = QCheckBox(self.network.TOR_AUTO_ON_MSG)
        self.tor_auto_on_cb.setChecked(self.config.get('tor_auto_on', True))
        vbox.addWidget(self.tor_auto_on_cb)

        def use_tor_auto_on(b):
            self.config.set_key('tor_auto_on', b, True)
            if not b:
                self.config.set_key('proxy', None, True)
        self.tor_auto_on_cb.clicked.connect(use_tor_auto_on)

        self.no_tor_btn = QPushButton(_('Continue without Tor'))
        self.no_tor_btn.clicked.connect(self.continue_without_tor)
        vbox.addWidget(self.no_tor_btn)

        self.detect_btn = QPushButton(_('Detect Tor again'))
        self.detect_btn.clicked.connect(self.detect_tor_again)
        vbox.addWidget(self.detect_btn)

        self.close_w_btn = QPushButton(_('Close wallet'))
        self.close_w_btn.clicked.connect(self.close_wallet)
        vbox.addWidget(self.close_w_btn)

        self.ok_btn = QPushButton(_('OK'))
        self.ok_btn.hide()
        self.ok_btn.clicked.connect(self.on_ok)
        vbox.addWidget(self.ok_btn)

    def keyPressEvent(self, event):
        if self.tor_detected:
            super(TorWarnDialog, self).keyPressEvent(event)
            return

        if event.key() == Qt.Key_Escape:
            event.ignore()
        else:
            super(TorWarnDialog, self).keyPressEvent(event)

    def closeEvent(self, event):
        if self.tor_detected:
            super(TorWarnDialog, self).closeEvent(event)
            return

        if self.question('Continue without Tor?'):
            self.continue_without_tor()
        else:
            self.done(-1)
        event.ignore()

    def continue_without_tor(self):
        net = self.network
        net_params = net.get_parameters()
        if net_params.proxy:
            host = net_params.proxy['host']
            port = net_params.proxy['port']
            if host == '127.0.0.1' and port in ['9050', '9150']:
                net_params = net_params._replace(proxy=None)
                coro = net.set_parameters(net_params)
                net.run_from_another_thread(coro)
        self.done(0)

    def detect_tor_again(self):
        net = self.network
        proxy_modifiable = self.config.is_modifiable('proxy')
        if not proxy_modifiable:
            return

        self.tor_detected = net.detect_tor_proxy()
        if not self.tor_detected:
            return

        net_params = net.get_parameters()
        proxy = deserialize_proxy(self.tor_detected)
        net_params = net_params._replace(proxy=proxy)
        coro = net.set_parameters(net_params)
        net.run_from_another_thread(coro)

        i_style = QStyle.SP_MessageBoxInformation
        i_icon = QApplication.style().standardIcon(i_style)
        self.w_icn_lbl.setPixmap(i_icon.pixmap(36))
        self.setWindowTitle(_('Information'))
        self.w_lbl.setText(_('Tor proxy detected'))
        self.no_tor_btn.hide()
        self.detect_btn.hide()
        self.close_w_btn.hide()
        self.ok_btn.show()
        self.tor_auto_on_cb.hide()
        self.setMinimumSize(self.minimumSizeHint())

    def close_wallet(self):
        self.done(-1)

    def on_ok(self):
        self.done(0)
