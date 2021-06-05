#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from functools import partial

from kivy.event import EventDispatcher
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button

from electrum_zcash.i18n import _
from electrum_zcash.logging import Logger
from electrum_zcash.network import Network

from electrum_zcash.gui.kivy.uix.dialogs.question import Question

from .scan_over_gap import ScanOverGapPlugin


try:
    getattr(Factory, 'ScanOverGapPopup')
except:
    Builder.load_string('''
<WWLabel@Label>:
    text_size: self.width, None
    height: self.texture_size[1]
    size_hint: 1, None


<TableLabel@ButtonBehavior+Label>:
    text_size: self.width, None
    width: self.texture_size[0]
    height: self.texture_size[1]


<DataTitle@TableLabel>:
    halign: 'right'


<DataVal@TableLabel>:
    halign: 'left'


<TitleColumn@BoxLayout>:
    title: ''
    key: ''
    active: False
    disabled: False
    orientation: 'horizontal'
    size_hint: 0.4, 1
    on_active: root.change_active(self.active)
    canvas:
        Color:
            rgb: 1, 1, 1
        Line:
            width: 1
            rectangle: self.x, self.y, self.width, self.height
    CheckBox:
        id: cb
        size_hint: None, 1
        width: '48dp'
        disabled: root.disabled
        active: root.active
        on_active:
            if root.active != self.active: root.active = self.active
    TableLabel:
        id: lb
        text: root.title
        disabled: root.disabled
        on_release:
            if not root.disabled: cb.active = not cb.active


<DataColumn@GridLayout>:
    start_idx: ''
    start_idx_title: ''
    scanned_cnt: ''
    scanned_cnt_title: ''
    found_balance: ''
    found_balance_title: ''
    cols: 2
    spacing: 10
    padding: 10, 10
    size_hint: 0.6, None
    height: sum([max(t1.height, d1.height), \
                 max(t2.height, d2.height), \
                 max(t3.height, d3.height)]) + 10 * 4
    disabled: False
    canvas:
        Color:
            rgb: 1, 1, 1
        Line:
            width: 1
            rectangle: self.x, self.y, self.width, self.height
    DataTitle:
        id: t1
        text: root.start_idx_title
        size_hint: 0.4, None
        disabled: root.disabled
    DataVal:
        id: d1
        text: root.start_idx
        size_hint: 0.6, None
        disabled: root.disabled
    DataTitle:
        id: t2
        text: root.scanned_cnt_title
        size_hint: 0.4, None
        disabled: root.disabled
    DataVal:
        id: d2
        text: root.scanned_cnt
        size_hint: 0.6, None
        disabled: root.disabled
    DataTitle:
        id: t3
        text: root.found_balance_title
        size_hint: 0.4, None
        disabled: root.disabled
    DataVal:
        id: d3
        text: root.found_balance
        size_hint: 0.6, None
        disabled: root.disabled


<ScanList@ScrollView>:
    grid: grid
    GridLayout:
        id: grid
        cols: 2
        spacing: '10dp'
        size_hint: 1, None
        height: self.minimum_height


<DlgButton@Button>:
    size_hint: 1, None
    height: '48dp'


<ScanCnt@BoxLayout>:
    size_hint: 1, None
    height: '48dp'
    min: 20
    max: 100
    step: 20
    val: 20
    on_val:
        if self.val > self.max: self.val = self.max
        if self.val < self.min: self.val = self.min
    Button:
        id: scan_cnt_dec_btn
        text: '-'
        size: input.height, input.height
        size_hint: None, None
        on_release:
            root.val -= root.step
    TextInput:
        id: input
        multiline: False
        input_filter: 'int'
        halign: 'center'
        text: str(root.val)
        size_hint_y: None
        height: self.minimum_height
        on_text:
            if not self.text: self.text = str(root.min)
            if str(root.val) != self.text: root.val = int(self.text)
    Button:
        id: scan_cnt_inc_btn
        text: '+'
        size_hint: None, None
        size: input.height, input.height
        on_release:
            root.val += root.step


<ScanOverGapPopup@Popup>
    box: box
    do_scan_btn: do_scan_btn
    reset_scans_btn: reset_scans_btn
    add_found_btn: add_found_btn
    scan_count_msg: ''
    scan_cnt_sb: scan_cnt_sb
    scan_progress_msg: ''
    scan_progress_pb: scan_progress_pb
    progress: 0
    BoxLayout:
        spacing: '5dp'
        id: box
        orientation: 'vertical'
        padding: '10dp', '10dp'
        BoxLayout:
            orientation: 'horizontal'
            spacing: '5dp'
            size_hint: 1, None
            height: '48dp'
            Label:
                text: root.scan_count_msg
                size_hint: 0.4, None
                height: '48dp'
            ScanCnt:
                id: scan_cnt_sb
                min: 0
                max: 100
                step: 10
                val: 0
                size_hint: 0.6, None
                height: '48dp'
                on_val:
                    root.on_scan_cnt_value_changed(self.val)
        DlgButton:
            id: do_scan_btn
            text: ''
            on_release: root.do_scan(root.wallet)
        BoxLayout:
            orientation: 'horizontal'
            spacing: '5dp'
            size_hint: 1, None
            height: '48dp'
            Label:
                text: root.scan_progress_msg
                size_hint: 0.4, None
                height: '48dp'
            ProgressBar:
                id: scan_progress_pb
                height: '20dp'
                size_hint: 0.6, None
                max: 100
                value: root.progress
        DlgButton:
            id: add_found_btn
            text: ''
            on_release: root.add_found_coins(root.wallet)
        BoxLayout:
            orientation: 'horizontal'
            spacing: '5dp'
            size_hint: 1, None
            height: '48dp'
            DlgButton:
                id: reset_scans_btn
                text: ''
                on_release: root.reset_scans(root.wallet)
            DlgButton:
                text: _('Close')
                on_release:
                    root.dismiss()
''')


class TitleColumn(BoxLayout):

    def __init__(self, scan_list, s, items_enabled):
        super(TitleColumn, self).__init__()
        self.plugin = scan_list.plugin
        self.wallet = scan_list.wallet
        self.title = s.title
        self.active = s.active
        self.key = s.key
        self.disabled = not items_enabled

    def change_active(self, active):
        ws = self.plugin.wallet_scans.get(self.wallet)
        if not ws:
            return
        scan = ws.scans.get(self.key)
        if scan:
            scan.active = active


class DataColumn(GridLayout):

    def __init__(self, scan_list, s, items_enabled):
        super(DataColumn, self).__init__()
        self.plugin = plugin = scan_list.plugin
        headers = plugin.COLUMN_HEADERS
        format_amount = plugin.format_amount
        cols = plugin.Columns
        self.start_idx_title = headers[cols.START_IDX] + ':'
        self.start_idx = str(s.start_idx)
        self.scanned_cnt_title = headers[cols.SCANNED_CNT] + ':'
        self.scanned_cnt = str(s.next_idx - s.start_idx)
        self.found_balance_title = headers[cols.FOUND_BALANCE] + ':'
        self.found_balance = format_amount(sum(s.balances.values()))
        self.disabled = not items_enabled


class ScanList(ScrollView):

    def __init__(self, plugin_popup):
        super(ScanList, self).__init__()
        self.plugin = plugin_popup.plugin
        self.wallet = plugin_popup.wallet

    def update(self, *, items_enabled=True):
        ws = self.plugin.wallet_scans.get(self.wallet)
        if not ws or not ws.scans:
            return
        self.grid.clear_widgets()
        for s in ws.scans.values():
            self.grid.add_widget(TitleColumn(self, s, items_enabled))
            self.grid.add_widget(DataColumn(self, s, items_enabled))


class ScanOverGapEventDispatcher(EventDispatcher):
    def __init__(self, **kwargs):
        self.register_event_type('on_completed')
        self.register_event_type('on_progress')
        self.register_event_type('on_error')
        super(ScanOverGapEventDispatcher, self).__init__(**kwargs)

    def on_completed(self, *args, **kwargs):
        pass

    def on_progress(self, *args, **kwargs):
        pass

    def on_error(self, *args, **kwargs):
        pass


ScanOverGapEvents = ScanOverGapEventDispatcher()


class ScanOverGapPopup(Factory.Popup, Logger):

    def __init__(self, app, plugin):
        super(ScanOverGapPopup, self).__init__()
        self.app = app
        self.wallet = w = app.wallet
        self.plugin = p = plugin
        self.title = plugin.MSG_TITLE
        self.network = Network.get_instance()
        coro = plugin.init_scans(w)
        fut = asyncio.run_coroutine_threadsafe(coro, self.network.asyncio_loop)
        fut.result()
        box = self.box
        box.add_widget(Factory.WWLabel(text=p.MSG_SCAN_TITLE),
                       len(box.children))
        self.scan_list = ScanList(self)
        self.scan_list.update()
        box.add_widget(self.scan_list, len(box.children)-1)
        self.set_do_scan_btn_txt(p.DEF_SCAN_CNT)
        self.reset_scans_btn.text = p.MSG_RESET
        self.add_found_btn.text = p.MSG_ADD_FOUND
        self.scan_count_msg = p.MSG_SCAN_COUNT
        self.scan_cnt_sb.min = p.MIN_SCAN_CNT
        self.scan_cnt_sb.max = p.MAX_SCAN_CNT
        self.scan_cnt_sb.step = p.DEF_SCAN_CNT
        self.scan_cnt_sb.val = p.DEF_SCAN_CNT
        self.scan_progress_msg = p.MSG_PROGRESS

        ws = self.plugin.wallet_scans.get(w)
        self.scan_progress_pb.value = ws.progress
        if ws.running:
            self.scan_cnt_sb.disabled = True
            self.do_scan_btn.disabled = True
            self.reset_scans_btn.disabled = True
        self.set_add_found_bnt_state()
        ScanOverGapEvents.bind(on_completed=self.on_completed_kivy)
        ScanOverGapEvents.bind(on_progress=self.on_progress_kivy)
        ScanOverGapEvents.bind(on_error=self.on_error_kivy)

    def dismiss(self):
        super(ScanOverGapPopup, self).dismiss()
        ScanOverGapEvents.unbind(on_completed=self.on_completed_kivy)
        ScanOverGapEvents.unbind(on_progress=self.on_progress_kivy)
        ScanOverGapEvents.unbind(on_error=self.on_error_kivy)

    def set_add_found_bnt_state(self):
        disabled = True
        ws = self.plugin.wallet_scans.get(self.wallet)
        if ws and not ws.running:
            for s in ws.scans.values():
                if sum(s.balances.values()):
                    disabled = False
                    break
        self.add_found_btn.disabled = disabled

    def set_do_scan_btn_txt(self, cnt):
        self.do_scan_btn.text = self.plugin.MSG_SCAN_NEXT.format(cnt)

    def on_scan_cnt_value_changed(self, value, *args, **kwargs):
        self.set_do_scan_btn_txt(value)

    def do_scan(self, wallet):
        self.scan_cnt_sb.disabled = True
        self.do_scan_btn.disabled = True
        self.reset_scans_btn.disabled = True
        self.add_found_btn.disabled = True
        self.scan_list.update(items_enabled=False)
        self.scan_progress_pb.value = 0
        coro = self.plugin.do_scan(wallet, self.scan_cnt_sb.val)
        asyncio.run_coroutine_threadsafe(coro, self.network.asyncio_loop)

    def add_found_coins(self, wallet):
        self.scan_cnt_sb.disabled = True
        self.do_scan_btn.disabled = True
        self.reset_scans_btn.disabled = True
        self.add_found_btn.disabled = True
        self.scan_list.update(items_enabled=False)
        coro = self.plugin.add_found(wallet)
        asyncio.run_coroutine_threadsafe(coro, self.network.asyncio_loop)

    def reset_scans(self, wallet):
        d = Question(self.plugin.MSG_Q_RESET, self.do_reset_scans)
        d.open()

    def do_reset_scans(self, b):
        if not b:
            return
        self.scan_list.update(items_enabled=False)
        loop = self.network.asyncio_loop
        coro = self.plugin.init_scans(self.wallet, reset=True)
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        fut.result()
        self.scan_list.update()

    def on_progress_kivy(self, event_dispatcher, wallet, progress):
        if self.wallet != wallet:
            return
        self.scan_progress_pb.value = progress

    def on_completed_kivy(self, event_dispatcher, wallet):
        if self.wallet != wallet:
            return
        self.scan_cnt_sb.disabled = False
        self.do_scan_btn.disabled = False
        self.reset_scans_btn.disabled = False
        self.set_add_found_bnt_state()
        self.scan_list.update()

    def on_error_kivy(self, event_dispatcher, wallet, e):
        if self.wallet != wallet:
            return
        self.scan_cnt_sb.disabled = False
        self.do_scan_btn.disabled = False
        self.reset_scans_btn.disabled = False
        self.set_add_found_bnt_state()
        self.scan_list.update()
        self.app.show_error(error=str(e))


class Plugin(ScanOverGapPlugin):

    def __init__(self, parent, config, name):
        super(Plugin, self).__init__(parent, config, name)

    def on_close(self):
        super(Plugin, self).on_close()

    async def on_progress(self, wallet, progress):
        await super(Plugin, self).on_progress(wallet, progress)
        ScanOverGapEvents.dispatch('on_progress', wallet, progress)

    async def on_completed(self, wallet):
        await super(Plugin, self).on_completed(wallet)
        ScanOverGapEvents.dispatch('on_completed', wallet)

    async def on_error(self, wallet, e):
        await super(Plugin, self).on_error(wallet, e)
        ScanOverGapEvents.dispatch('on_error', wallet, e)

    def requires_settings(self) -> bool:
        return True

    def settings_widget(self, window):
        return Button(text=_('Scan'),
                      on_release=partial(self.settings_dialog, window))

    def settings_dialog(self, window, scan_button):
        d = ScanOverGapPopup(window, self)
        d.open()
