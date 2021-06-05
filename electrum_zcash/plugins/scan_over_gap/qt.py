#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from functools import partial

from PyQt5.Qt import Qt
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (QGridLayout, QLabel, QSpinBox, QPushButton,
                             QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QProgressBar, QHBoxLayout)

from electrum_zcash.network import Network

from electrum_zcash.gui.qt.util import (EnterButton, WindowModalDialog, WWLabel,
                                       CloseButton)

from .scan_over_gap import ScanOverGapPlugin


class ProgressSignal(QObject):
    s = pyqtSignal(object, float)


class CompletedSignal(QObject):
    s = pyqtSignal(object)


class ErrorSignal(QObject):
    s = pyqtSignal(object, object)


class ScanListWidget(QTreeWidget):

    def __init__(self, parent):
        QTreeWidget.__init__(self)
        self.wallet = parent.wallet
        self.plugin = plugin = parent.plugin
        self.format_amount = plugin.format_amount
        self.setHeaderLabels(plugin.COLUMN_HEADERS)
        h = self.header()
        mode = QHeaderView.ResizeToContents
        h.setSectionResizeMode(plugin.Columns.KEY, mode)
        h.setSectionResizeMode(plugin.Columns.TITLE, mode)
        h.setSectionResizeMode(plugin.Columns.START_IDX, mode)
        h.setSectionResizeMode(plugin.Columns.SCANNED_CNT, mode)
        h.setSectionResizeMode(plugin.Columns.FOUND_BALANCE, mode)
        self.setColumnHidden(plugin.Columns.KEY, True)

    def update(self, *, items_enabled=True):
        ws = self.plugin.wallet_scans.get(self.wallet)
        if not ws or not ws.scans:
            return
        self.clear()
        scans = ws.scans
        for s in scans.values():
            scanned_cnt = s.next_idx - s.start_idx
            found_balance = self.format_amount(sum(s.balances.values()))
            scan_item = QTreeWidgetItem([s.key, s.title, str(s.start_idx),
                                         str(scanned_cnt), found_balance])
            check_state = Qt.Checked if s.active else Qt.Unchecked
            scan_item.setCheckState(self.plugin.Columns.TITLE, check_state)
            if not items_enabled:
                scan_item.setFlags(scan_item.flags() ^ Qt.ItemIsEnabled)
            self.addTopLevelItem(scan_item)
        super().update()


class ScanOverGapDialog(WindowModalDialog):

    def __init__(self, window, plugin):
        WindowModalDialog.__init__(self, window, plugin.MSG_TITLE)
        self.setMinimumSize(800, 400)

        self.wallet = w = window.parent().wallet
        self.plugin = plugin
        self.config = plugin.config
        self.network = Network.get_instance()
        coro = plugin.init_scans(w)
        fut = asyncio.run_coroutine_threadsafe(coro, self.network.asyncio_loop)
        fut.result()

        g = QGridLayout(self)

        g.addWidget(WWLabel(plugin.MSG_SCAN_TITLE), 0, 0, 1, -1)

        self.scan_list = ScanListWidget(self)
        self.scan_list.update()
        self.scan_list.itemChanged.connect(self.scan_list_item_changed)
        g.addWidget(self.scan_list, 1, 0, 1, -1)

        g.addWidget(QLabel(plugin.MSG_SCAN_COUNT), 2, 0)
        self.scan_cnt_sb = QSpinBox()
        self.scan_cnt_sb.setRange(plugin.MIN_SCAN_CNT, plugin.MAX_SCAN_CNT)
        self.scan_cnt_sb.setValue(plugin.DEF_SCAN_CNT)
        self.scan_cnt_sb.setSingleStep(plugin.DEF_SCAN_CNT)
        self.scan_cnt_sb.valueChanged.connect(self.on_scan_cnt_value_changed)
        g.addWidget(self.scan_cnt_sb, 2, 1)

        self.do_scan_btn = QPushButton()
        self.set_do_scan_btn_txt(plugin.DEF_SCAN_CNT)
        self.do_scan_btn.clicked.connect(partial(self.do_scan, w))
        g.addWidget(self.do_scan_btn, 2, 3)

        g.addWidget(QLabel(plugin.MSG_PROGRESS), 2, 4)
        self.scan_progress_pb = QProgressBar()
        self.scan_progress_pb.setValue(0)
        g.addWidget(self.scan_progress_pb , 2, 5)

        g.setRowStretch(10, 1)

        hbox = QHBoxLayout()
        self.reset_scans_btn = QPushButton(plugin.MSG_RESET)
        self.reset_scans_btn.clicked.connect(partial(self.reset_scans, w))
        hbox.addWidget(self.reset_scans_btn)
        hbox.addStretch(1)
        self.add_found_btn = QPushButton(plugin.MSG_ADD_FOUND)
        self.add_found_btn.clicked.connect(partial(self.add_found_coins, w))
        hbox.addWidget(self.add_found_btn)
        hbox.addWidget(CloseButton(self))
        g.addLayout(hbox, 11, 0, 1, -1)

        self.plugin.progress_sig.s.connect(self.on_progress_qt)
        self.plugin.completed_sig.s.connect(self.on_completed_qt)
        self.plugin.error_sig.s.connect(self.on_error_qt)
        self.cleaned_up = False

        ws = self.plugin.wallet_scans.get(w)
        self.scan_progress_pb.setValue(ws.progress)
        if ws.running:
            self.scan_cnt_sb.setEnabled(False)
            self.do_scan_btn.setEnabled(False)
            self.reset_scans_btn.setEnabled(False)
        self.set_add_found_bnt_state()

    def set_add_found_bnt_state(self):
        enabled = False
        ws = self.plugin.wallet_scans.get(self.wallet)
        if ws and not ws.running:
            for s in ws.scans.values():
                if sum(s.balances.values()):
                    enabled = True
                    break
        self.add_found_btn.setEnabled(enabled)

    def set_do_scan_btn_txt(self, cnt):
        self.do_scan_btn.setText(self.plugin.MSG_SCAN_NEXT.format(cnt))

    def on_scan_cnt_value_changed(self, value):
        self.set_do_scan_btn_txt(value)

    def scan_list_item_changed(self, item, col):
        ws = self.plugin.wallet_scans.get(self.wallet)
        if not ws:
            return
        if col != self.plugin.Columns.TITLE:
            return
        key = item.data(self.plugin.Columns.KEY, Qt.DisplayRole)
        scan = ws.scans.get(key)
        if scan:
            scan.active = (item.checkState(col) == Qt.Checked)

    def closeEvent(self, event):
        if self.cleaned_up:
            return
        self.plugin.progress_sig.s.disconnect(self.on_progress_qt)
        self.plugin.completed_sig.s.disconnect(self.on_completed_qt)
        self.plugin.error_sig.s.disconnect(self.on_error_qt)
        self.cleaned_up = True

    def do_scan(self, wallet):
        self.scan_cnt_sb.setEnabled(False)
        self.do_scan_btn.setEnabled(False)
        self.reset_scans_btn.setEnabled(False)
        self.add_found_btn.setEnabled(False)
        self.scan_list.update(items_enabled=False)
        self.scan_progress_pb.setValue(0)
        coro = self.plugin.do_scan(wallet, self.scan_cnt_sb.value())
        asyncio.run_coroutine_threadsafe(coro, self.network.asyncio_loop)

    def add_found_coins(self, wallet):
        self.scan_cnt_sb.setEnabled(False)
        self.do_scan_btn.setEnabled(False)
        self.reset_scans_btn.setEnabled(False)
        self.add_found_btn.setEnabled(False)
        self.scan_list.update(items_enabled=False)
        coro = self.plugin.add_found(wallet)
        asyncio.run_coroutine_threadsafe(coro, self.network.asyncio_loop)

    def reset_scans(self, wallet):
        if not self.question(self.plugin.MSG_Q_RESET):
            return
        self.scan_list.update(items_enabled=False)
        coro = self.plugin.init_scans(wallet, reset=True)
        fut = asyncio.run_coroutine_threadsafe(coro, self.network.asyncio_loop)
        fut.result()
        self.scan_list.update()

    def on_progress_qt(self, wallet, progress):
        if self.wallet != wallet:
            return
        self.scan_progress_pb.setValue(progress)

    def on_completed_qt(self, wallet):
        if self.wallet != wallet:
            return
        self.scan_cnt_sb.setEnabled(True)
        self.do_scan_btn.setEnabled(True)
        self.reset_scans_btn.setEnabled(True)
        self.set_add_found_bnt_state()
        self.scan_list.update()

    def on_error_qt(self, wallet, e):
        if self.wallet != wallet:
            return
        self.scan_cnt_sb.setEnabled(True)
        self.do_scan_btn.setEnabled(True)
        self.reset_scans_btn.setEnabled(True)
        self.set_add_found_bnt_state()
        self.scan_list.update()
        self.show_error(str(e))


class Plugin(ScanOverGapPlugin):

    def __init__(self, parent, config, name):
        super(Plugin, self).__init__(parent, config, name)
        self.progress_sig = ProgressSignal()
        self.completed_sig = CompletedSignal()
        self.error_sig = ErrorSignal()

    def on_close(self):
        super(Plugin, self).on_close()
        self.progress_sig = None
        self.completed_sig = None
        self.error_sig = None

    async def on_progress(self, wallet, progress):
        await super(Plugin, self).on_progress(wallet, progress)
        self.progress_sig.s.emit(wallet, progress)

    async def on_completed(self, wallet):
        await super(Plugin, self).on_completed(wallet)
        self.completed_sig.s.emit(wallet)

    async def on_error(self, wallet, e):
        await super(Plugin, self).on_error(wallet, e)
        self.error_sig.s.emit(wallet, e)

    def requires_settings(self) -> bool:
        return True

    def settings_widget(self, window):
        settings_dialog_partial = partial(self.settings_dialog, window)
        return EnterButton(self.MSG_SCAN, settings_dialog_partial)

    def settings_dialog(self, window):
        d = ScanOverGapDialog(window, self)
        d.exec_()
