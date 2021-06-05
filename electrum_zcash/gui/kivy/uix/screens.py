import asyncio
from weakref import ref
from decimal import Decimal
import re
import copy
import threading
import traceback, sys
from typing import TYPE_CHECKING, List, Optional, Dict, Any

from kivy.app import App
from kivy.cache import Cache
from kivy.clock import Clock
from kivy.compat import string_types
from kivy.properties import (ObjectProperty, DictProperty, NumericProperty,
                             ListProperty, StringProperty, BooleanProperty)

from kivy.uix.recycleview import RecycleView
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.image import Image

from kivy.lang import Builder
from kivy.factory import Factory
from kivy.utils import platform

from electrum_zcash.util import profiler, parse_URI, format_time, InvalidPassword, NotEnoughFunds, Fiat
from electrum_zcash.invoices import (PR_TYPE_ONCHAIN, PR_DEFAULT_EXPIRATION_WHEN_CREATING,
                                    PR_PAID, PR_UNKNOWN, PR_EXPIRED, PR_INFLIGHT,
                                    pr_expiration_values, Invoice, OnchainInvoice)
from electrum_zcash import bitcoin, constants
from electrum_zcash.transaction import Transaction, tx_from_any, PartialTransaction, PartialTxOutput
from electrum_zcash.util import parse_URI, InvalidBitcoinURI, TxMinedInfo
from electrum_zcash.wallet import InternalAddressCorruption
from electrum_zcash import simple_config
from electrum_zcash.logging import Logger

from .dialogs.question import Question
from .dialogs.confirm_tx_dialog import ConfirmTxDialog
from .context_menu import ContextMenu

from electrum_zcash.gui.kivy import KIVY_GUI_PATH
from electrum_zcash.gui.kivy.i18n import _

if TYPE_CHECKING:
    from electrum_zcash.gui.kivy.main_window import ElectrumWindow
    from electrum_zcash.paymentrequest import PaymentRequest


class HistoryItem(RecycleDataViewBehavior, BoxLayout):
    index = None
    selected = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super(HistoryItem, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if super(HistoryItem, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        self.selected = is_selected


class HistBoxLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    def select_node(self, node):
        super(HistBoxLayout, self).select_node(node)
        rv = self.recycleview
        data = rv.data[node]
        rv.hist_screen.on_select_node(node, data)

    def deselect_node(self, node):
        super(HistBoxLayout, self).deselect_node(node)
        rv = self.recycleview
        rv.hist_screen.on_deselect_node()


class RequestRecycleView(RecycleView):
    pass


class PaymentRecycleView(RecycleView):
    pass


class CScreen(Factory.Screen):
    __events__ = ('on_activate', 'on_deactivate', 'on_enter', 'on_leave')
    action_view = ObjectProperty(None)
    kvname = None
    app = App.get_running_app()  # type: ElectrumWindow

    def on_enter(self):
        # FIXME: use a proper event don't use animation time of screen
        Clock.schedule_once(lambda dt: self.dispatch('on_activate'), .25)
        pass

    def update(self):
        pass

    def on_activate(self):
        setattr(self.app, self.kvname + '_screen', self)
        self.update()

    def on_leave(self):
        self.dispatch('on_deactivate')

    def on_deactivate(self):
        pass


# note: this list needs to be kept in sync with another in qt
TX_ICONS = [
    "unconfirmed",
    "close",
    "unconfirmed",
    "close",
    "clock1",
    "clock2",
    "clock3",
    "clock4",
    "clock5",
    "confirmed",
]


Builder.load_file(KIVY_GUI_PATH + '/uix/ui_screens/history.kv')
Builder.load_file(KIVY_GUI_PATH + '/uix/ui_screens/send.kv')
Builder.load_file(KIVY_GUI_PATH + '/uix/ui_screens/receive.kv')


class GetHistoryDataThread(threading.Thread):

    def __init__(self, screen):
        super(GetHistoryDataThread, self).__init__()
        self.screen = screen
        self.need_update = threading.Event()
        self.res = []
        self._stopped = False

    def run(self):
        app = self.screen.app
        while True:
            try:
                self.need_update.wait()
                self.need_update.clear()
                if self._stopped:
                    return
                group_ps = False
                res = app.wallet.get_full_history(app.fx,
                                                  group_ps=group_ps)
                Clock.schedule_once(lambda dt: self.screen.update_data(res))
            except Exception as e:
                Logger.info(f'GetHistoryDataThread error: {str(e)}')

    def stop(self):
        self._stopped = True
        self.need_update.set()


class HistoryScreen(CScreen):

    tab = ObjectProperty(None)
    kvname = 'history'
    cards = {}

    def __init__(self, **kwargs):
        self.ra_dialog = None
        super(HistoryScreen, self).__init__(**kwargs)
        atlas_path = f'atlas://{KIVY_GUI_PATH}/theming/light/'
        self.atlas_path = atlas_path
        self.group_icn_empty = atlas_path + 'kv_tx_group_empty'
        self.group_icn_head = atlas_path + 'kv_tx_group_head'
        self.group_icn_tail = atlas_path + 'kv_tx_group_tail'
        self.group_icn_mid = atlas_path + 'kv_tx_group_mid'
        self.group_icn_all = atlas_path + 'kv_tx_group_all'
        self.expanded_groups = set()
        self.history = []
        self.selected_txid = ''
        self.get_data_thread = None
        self.context_menu = None

    def on_deactivate(self):
        self.hide_menu()

    def hide_menu(self):
        if self.context_menu is not None:
            self.cmbox.remove_widget(self.context_menu)
            self.context_menu = None

    def stop_get_data_thread(self):
        if self.get_data_thread is not None:
            self.get_data_thread.stop()

    def show_item(self, obj):
        key = obj['key']
        tx = self.app.wallet.db.get_transaction(key)
        if not tx:
            return
        self.app.tx_dialog(tx)

    def expand_tx_group(self, data):
        group_txid = data['group_txid']
        if group_txid and group_txid not in self.expanded_groups:
            self.expanded_groups.add(group_txid)
            self.update(reload_history=False)

    def collapse_tx_group(self, data):
        group_txid = data['group_txid']
        if group_txid and group_txid in self.expanded_groups:
            self.expanded_groups.remove(group_txid)
            self.update(reload_history=False)

    def on_deselect_node(self):
        self.hide_menu()
        self.selected_txid = ''

    def clear_selection(self):
        self.hide_menu()
        container = self.ids.history_container
        container.layout_manager.clear_selection()

    def on_select_node(self, node, data):
        menu_actions = []
        self.selected_txid = data['key']
        group_txid = data['group_txid']
        if group_txid and group_txid not in self.expanded_groups:
            menu_actions.append(('Expand Tx Group', self.expand_tx_group))
        elif group_txid and group_txid in self.expanded_groups:
            menu_actions.append(('Collapse Tx Group', self.collapse_tx_group))
        menu_actions.append(('Details', self.show_item))
        self.hide_menu()
        self.context_menu = ContextMenu(data, menu_actions)
        self.cmbox.add_widget(self.context_menu)

    def get_card(self, tx_item):
        timestamp = tx_item['timestamp']
        key = tx_item.get('txid')
        tx_hash = tx_item['txid']
        conf = tx_item['confirmations']
        tx_mined_info = TxMinedInfo(height=tx_item['height'],
                                    conf=conf, timestamp=timestamp)
        status, status_str = self.app.wallet.get_tx_status(tx_hash,
                                                           tx_mined_info)
        icon = self.atlas_path + TX_ICONS[status]
        message = tx_item['label'] or tx_hash
        fee = tx_item['fee_sat']
        fee_text = '' if fee is None else 'fee: %d sat'%fee
        ri = {}
        ri['screen'] = self
        ri['key'] = key
        ri['icon'] = icon
        ri['group_icn'] = tx_item['group_icon']
        ri['group_txid'] = tx_item['group_txid']
        ri['date'] = status_str
        ri['message'] = message
        ri['fee_text'] = fee_text
        value = tx_item['value'].value
        if value is not None:
            ri['is_mine'] = value <= 0
            ri['amount'] = self.app.format_amount(value, is_diff = True)
            if 'fiat_value' in tx_item:
                ri['quote_text'] = str(tx_item['fiat_value'])
        return ri

    def process_tx_groups(self, history):
        txs = []
        group_txs = []
        expanded_groups = set()
        selected_node = None
        selected_txid = self.selected_txid
        for hist_dict in history.values():
            h = copy.deepcopy(dict(hist_dict))
            txid = h['txid']
            group_txid = h['group_txid']
            group_data = h['group_data']
            if group_txid is None and not group_data:
                h['group_icon'] = self.group_icn_empty
                txs.append(h)
                if selected_txid and selected_txid == txid:
                    selected_node = len(txs) - 1
            elif group_txid:
                if not group_txs:
                    h['group_icon'] = self.group_icn_tail
                else:
                    h['group_icon'] = self.group_icn_mid
                group_txs.append(h)
            else:
                value, balance, group_txids = group_data
                h['value'] = value
                h['balance'] = balance
                h['group_icon'] = self.group_icn_head
                h['group_txid'] = txid
                for expanded_txid in self.expanded_groups:
                    if expanded_txid in group_txids:
                        expanded_groups.add(txid)
                if txid in expanded_groups:
                    txs.extend(group_txs)
                    h['group_icon'] = self.group_icn_head
                    txs.append(h)
                    if selected_txid and selected_txid in group_txids:
                        idx = group_txids.index(selected_txid)
                        selected_node = len(txs) - 1 - idx
                else:
                    h['label'] = _('Group of {} Txs').format(len(group_txids))
                    h['group_icon'] = self.group_icn_all
                    txs.append(h)
                    if selected_txid and selected_txid in group_txids:
                        selected_node = len(txs) - 1
                        self.selected_txid = selected_txid = txid
                group_txs = []
        if selected_node is None:
            self.selected_txid = ''
        self.expanded_groups = expanded_groups
        return selected_node, txs

    @profiler
    def update(self, reload_history=True):
        if self.app.wallet is None:
            return
        if self.get_data_thread is None:
            self.get_data_thread = GetHistoryDataThread(self)
            self.get_data_thread.start()
        if reload_history:
            self.get_data_thread.need_update.set()
        else:
            self.update_data(self.history)

    @profiler
    def update_data(self, history):
        self.history = history
        selected_txid = self.selected_txid
        self.clear_selection()
        self.selected_txid = selected_txid
        selected_node, history = self.process_tx_groups(self.history)
        if selected_node is not None:
            selected_node = len(history) - 1 - selected_node
        history = reversed(history)
        history_card = self.ids.history_container
        config = self.app.electrum_config
        history_card.data = [self.get_card(item) for item in history]
        if selected_node is not None:
            history_card.layout_manager.select_node(selected_node)


class SendScreen(CScreen, Logger):

    kvname = 'send'
    payment_request = None  # type: Optional[PaymentRequest]
    parsed_URI = None

    def __init__(self, **kwargs):
        CScreen.__init__(self, **kwargs)
        Logger.__init__(self)
        self.is_max = False

    def set_URI(self, text: str):
        if not self.app.wallet:
            return
        try:
            uri = parse_URI(text, self.app.on_pr, loop=self.app.asyncio_loop)
        except InvalidBitcoinURI as e:
            self.app.show_info(_("Error parsing URI") + f":\n{e}")
            return
        self.parsed_URI = uri
        amount = uri.get('amount')
        self.address = uri.get('address', '')
        self.message = uri.get('message', '')
        self.amount = self.app.format_amount_and_units(amount) if amount else ''
        self.is_max = False
        self.payment_request = None

    def update(self):
        if self.app.wallet is None:
            return
        _list = self.app.wallet.get_unpaid_invoices()
        _list.reverse()
        payments_container = self.ids.payments_container
        payments_container.data = [self.get_card(invoice) for invoice in _list]

    def update_item(self, key, invoice):
        payments_container = self.ids.payments_container
        data = payments_container.data
        for item in data:
            if item['key'] == key:
                item.update(self.get_card(invoice))
        payments_container.data = data
        payments_container.refresh_from_data()

    def show_item(self, obj):
        self.app.show_invoice(obj.key)

    def get_card(self, item: Invoice) -> Dict[str, Any]:
        status = self.app.wallet.get_invoice_status(item)
        status_str = item.get_status_str(status)
        key = self.app.wallet.get_key_for_outgoing_invoice(item)
        assert isinstance(item, OnchainInvoice)
        address = item.get_address()
        is_bip70 = bool(item.bip70)
        amount_str = self.app.format_amount_and_units(item.get_amount_sat()
                                                      or 0)
        return {
            'is_bip70': is_bip70,
            'screen': self,
            'status': status,
            'status_str': status_str,
            'key': key,
            'memo': item.message or _('No Description'),
            'address': address,
            'amount': amount_str,
        }

    def do_clear(self):
        self.amount = ''
        self.message = ''
        self.address = ''
        self.payment_request = None
        self.is_bip70 = False
        self.parsed_URI = None
        self.is_max = False

    def set_request(self, pr: 'PaymentRequest'):
        self.address = pr.get_requestor()
        amount = pr.get_amount()
        self.amount = self.app.format_amount_and_units(amount) if amount else ''
        self.message = pr.get_memo()
        self.locked = True
        self.payment_request = pr

    def do_paste(self):
        data = self.app._clipboard.paste().strip()
        if not data:
            self.app.show_info(_("Clipboard is empty"))
            return
        # try to decode as transaction
        try:
            tx = tx_from_any(data)
            tx.deserialize()
        except:
            tx = None
        if tx:
            self.app.tx_dialog(tx)
            return
        # try to decode as URI/address
        self.set_URI(data)

    def read_invoice(self):
        address = str(self.address)
        if not address:
            self.app.show_error(_('Recipient not specified.') + ' ' + _('Please scan a Zcash address or a payment request'))
            return
        if not self.amount:
            self.app.show_error(_('Please enter an amount'))
            return
        if self.is_max:
            amount = '!'
        else:
            try:
                amount = self.app.get_amount(self.amount)
            except:
                self.app.show_error(_('Invalid amount') + ':\n' + self.amount)
                return
        message = self.message
        if self.payment_request:
            outputs = self.payment_request.get_outputs()
        else:
            if not bitcoin.is_address(address):
                self.app.show_error(_('Invalid Zcash Address') + ':\n' + address)
                return
            outputs = [PartialTxOutput.from_address_and_value(address, amount)]
        return self.app.wallet.create_invoice(
            outputs=outputs,
            message=message,
            pr=self.payment_request,
            URI=self.parsed_URI)

    def do_save(self):
        invoice = self.read_invoice()
        if not invoice:
            return
        self.save_invoice(invoice)

    def save_invoice(self, invoice):
        self.app.wallet.save_invoice(invoice)
        self.do_clear()
        self.update()

    def do_pay(self):
        invoice = self.read_invoice()
        if not invoice:
            return
        self.do_pay_invoice(invoice)

    def do_pay_invoice(self, invoice):
        self._do_pay_onchain(invoice)

    def _do_pay_onchain(self, invoice: OnchainInvoice) -> None:
        outputs = invoice.outputs
        amount = sum(map(lambda x: x.value, outputs)) if '!' not in [x.value for x in outputs] else '!'
        wallet = self.app.wallet
        coins = wallet.get_spendable_coins(None)
        make_tx = lambda: self.app.wallet.make_unsigned_transaction(coins=coins, outputs=outputs)
        on_pay = lambda tx: self.app.protected(_('Send payment?'), self.send_tx, (tx, invoice))
        d = ConfirmTxDialog(self.app, amount=amount, make_tx=make_tx, on_pay=on_pay)
        d.open()

    def send_tx(self, tx, invoice, password):
        if self.app.wallet.has_password() and password is None:
            return
        pr = self.payment_request
        self.save_invoice(invoice)
        def on_success(tx):
            if tx.is_complete():
                self.app.broadcast(tx, pr)
            else:
                self.app.tx_dialog(tx, pr)
        def on_failure(error):
            self.app.show_error(error)
        if self.app.wallet.can_sign(tx):
            self.app.show_info("Signing...")
            self.app.sign_tx(tx, password, on_success, on_failure)
        else:
            self.app.tx_dialog(tx, pr)


class ReceiveScreen(CScreen):

    kvname = 'receive'

    def __init__(self, **kwargs):
        super(ReceiveScreen, self).__init__(**kwargs)
        Clock.schedule_interval(lambda dt: self.update(), 5)
        self.is_max = False # not used for receiving (see app.amount_dialog)

    def expiry(self):
        return self.app.electrum_config.get('request_expiry', PR_DEFAULT_EXPIRATION_WHEN_CREATING)

    def clear(self):
        self.address = ''
        self.amount = ''
        self.message = ''

    def set_address(self, addr):
        self.address = addr

    def on_address(self, addr):
        req = self.app.wallet.get_request(addr)
        self.status = ''
        if req:
            self.message = req.get('memo', '')
            amount = req.get('amount')
            self.amount = self.app.format_amount_and_units(amount) if amount else ''
            status = req.get('status', PR_UNKNOWN)
            self.status = _('Payment received') if status == PR_PAID else ''

    def get_URI(self):
        from electrum_zcash.util import create_bip21_uri
        amount = self.amount
        if amount:
            a, u = self.amount.split()
            assert u == self.app.base_unit
            amount = Decimal(a) * pow(10, self.app.decimal_point())
        return create_bip21_uri(self.address, amount, self.message)

    def do_copy(self):
        uri = self.get_URI()
        self.app._clipboard.copy(uri)
        self.app.show_info(_('Request copied to clipboard'))

    def new_request(self):
        amount = self.amount
        amount = self.app.get_amount(amount) if amount else 0
        message = self.message
        addr = self.address or self.app.wallet.get_unused_address()
        if not addr:
            if not self.app.wallet.is_deterministic():
                addr = self.app.wallet.get_receiving_address()
            else:
                self.app.show_info(_('No address available. Please remove some of your pending requests.'))
                return
        self.address = addr
        req = self.app.wallet.make_payment_request(addr, amount, message, self.expiry())
        self.app.wallet.add_payment_request(req)
        key = addr
        self.clear()
        self.update()
        self.app.show_request(key)

    def get_card(self, req: Invoice) -> Dict[str, Any]:
        assert isinstance(req, OnchainInvoice)
        address = req.get_address()
        key = self.app.wallet.get_key_for_receive_request(req)
        amount = req.get_amount_sat()
        description = req.message
        status = self.app.wallet.get_request_status(key)
        status_str = req.get_status_str(status)
        ci = {}
        ci['screen'] = self
        ci['address'] = address
        ci['key'] = key
        ci['amount'] = self.app.format_amount_and_units(amount) if amount else ''
        ci['memo'] = description or _('No Description')
        ci['status'] = status
        ci['status_str'] = status_str
        return ci

    def update(self):
        if self.app.wallet is None:
            return
        _list = self.app.wallet.get_unpaid_requests()
        _list.reverse()
        requests_container = self.ids.requests_container
        requests_container.data = [self.get_card(item) for item in _list]

    def update_item(self, key, request):
        payments_container = self.ids.requests_container
        data = payments_container.data
        for item in data:
            if item['key'] == key:
                status = self.app.wallet.get_request_status(key)
                status_str = request.get_status_str(status)
                item['status'] = status
                item['status_str'] = status_str
        payments_container.data = data # needed?
        payments_container.refresh_from_data()

    def show_item(self, obj):
        self.app.show_request(obj.key)

    def expiration_dialog(self, obj):
        from .dialogs.choice_dialog import ChoiceDialog
        def callback(c):
            self.app.electrum_config.set_key('request_expiry', c)
        d = ChoiceDialog(_('Expiration date'), pr_expiration_values, self.expiry(), callback)
        d.open()


class TabbedCarousel(Factory.TabbedPanel):
    '''Custom TabbedPanel using a carousel used in the Main Screen
    '''

    carousel = ObjectProperty(None)

    def animate_tab_to_center(self, value):
        scrlv = self._tab_strip.parent
        if not scrlv:
            return
        idx = self.tab_list.index(value)
        n = len(self.tab_list)
        if idx in [0, 1]:
            scroll_x = 1
        elif idx in [n-1, n-2]:
            scroll_x = 0
        else:
            scroll_x = 1. * (n - idx - 1) / (n - 1)
        mation = Factory.Animation(scroll_x=scroll_x, d=.25)
        mation.cancel_all(scrlv)
        mation.start(scrlv)

    def on_current_tab(self, instance, value):
        self.animate_tab_to_center(value)

    def on_index(self, instance, value):
        current_slide = instance.current_slide
        if not hasattr(current_slide, 'tab'):
            return
        tab = current_slide.tab
        ct = self.current_tab
        try:
            if ct.text != tab.text:
                carousel = self.carousel
                carousel.slides[ct.slide].dispatch('on_leave')
                self.switch_to(tab)
                carousel.slides[tab.slide].dispatch('on_enter')
        except AttributeError:
            current_slide.dispatch('on_enter')

    def switch_to(self, header):
        # we have to replace the functionality of the original switch_to
        if not header:
            return
        if not hasattr(header, 'slide'):
            header.content = self.carousel
            super(TabbedCarousel, self).switch_to(header)
            try:
                tab = self.tab_list[-1]
            except IndexError:
                return
            self._current_tab = tab
            tab.state = 'down'
            return

        carousel = self.carousel
        self.current_tab.state = "normal"
        header.state = 'down'
        self._current_tab = header
        # set the carousel to load the appropriate slide
        # saved in the screen attribute of the tab head
        slide = carousel.slides[header.slide]
        if carousel.current_slide != slide:
            carousel.current_slide.dispatch('on_leave')
            carousel.load_slide(slide)
            slide.dispatch('on_enter')

    def add_widget(self, widget, index=0):
        if isinstance(widget, Factory.CScreen):
            self.carousel.add_widget(widget)
            return
        super(TabbedCarousel, self).add_widget(widget, index=index)
