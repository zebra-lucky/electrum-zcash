from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior

from electrum_zcash.gui.kivy.i18n import _
from electrum_zcash.gui.kivy.uix.context_menu import ContextMenu


Builder.load_string('''
<AddressButton@Button>:
    background_color: 1, .585, .878, 0
    halign: 'center'
    text_size: (self.width, None)
    shorten: True
    size_hint: 0.5, None
    default_text: ''
    text: self.default_text
    padding: '5dp', '5dp'
    height: '40dp'
    text_color: self.foreground_color
    disabled_color: 1, 1, 1, 1
    foreground_color: 1, 1, 1, 1
    canvas.before:
        Color:
            rgba: (0.9, .498, 0.745, 1) if self.state == 'down' else self.background_color
        Rectangle:
            size: self.size
            pos: self.pos


<CoinLabel@Label>
    text_size: self.width, None
    halign: 'left'
    valign: 'top'
    shorten: True


<CoinItem>
    outpoint: ''
    address: ''
    block_height: ''
    amount: ''
    size_hint: 1, None
    height: '65dp'
    padding: dp(12)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: (0.192, .498, 0.745, 1) if self.selected  \
                else (0.15, 0.15, 0.17, 1)
        Rectangle:
            size: self.size
            pos: self.pos
    BoxLayout:
        spacing: '8dp'
        height: '32dp'
        orientation: 'vertical'
        Widget
        CoinLabel:
            text: root.outpoint
        Widget
        CoinLabel:
            text: '%s    Height: %s' % (root.address, root.block_height)
            color: .699, .699, .699, 1
            font_size: '13sp'
        Widget
        CoinLabel:
            text: '%s' % root.amount
            color: .699, .899, .699, 1
            font_size: '13sp'
        Widget


<CoinsDialog@Popup>
    id: dlg
    title: _('Coins')
    cmbox: cmbox
    padding: 0
    spacing: 0
    BoxLayout:
        id: box
        padding: '12dp', '12dp', '12dp', '12dp'
        spacing: '12dp'
        orientation: 'vertical'
        size_hint: 1, 1
        BoxLayout:
            spacing: '6dp'
            size_hint: 1, None
            height: self.minimum_height
            orientation: 'horizontal'
            AddressFilter:
                opacity: 1
                size_hint: 1, None
                height: self.minimum_height
                spacing: '5dp'
                AddressButton:
                    id: clear_btn
                    disabled: True
                    disabled_color: 0.5, 0.5, 0.5, 1
                    text: _('Clear Selection') + root.selected_str
                    on_release:
                        Clock.schedule_once(lambda dt: root.clear_selection())
        RecycleView:
            scroll_type: ['bars', 'content']
            bar_width: '15dp'
            viewclass: 'CoinItem'
            id: scroll_container
            CoinsRecycleBoxLayout:
                dlg: dlg
                orientation: 'vertical'
                default_size: None, dp(72)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                multiselect: False
                touch_multiselect: False
        BoxLayout:
            id: cmbox
            height: '48dp'
            size_hint: 1, None
            orientation: 'vertical'
            canvas.before:
                Color:
                    rgba: .1, .1, .1, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
''')


class CoinItem(RecycleDataViewBehavior, BoxLayout):
    index = None
    selected = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super(CoinItem, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if super(CoinItem, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        self.selected = is_selected


class CoinsRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                            RecycleBoxLayout):
    def select_node(self, node):
        super(CoinsRecycleBoxLayout, self).select_node(node)
        self.dlg.selection_changed(self.selected_nodes)

    def deselect_node(self, node):
        super(CoinsRecycleBoxLayout, self).deselect_node(node)
        self.dlg.selection_changed(self.selected_nodes)


class CoinsDialog(Factory.Popup):

    selected_str = StringProperty('')

    def __init__(self, app, filter_val=0):
        Factory.Popup.__init__(self)
        self.app = app
        self.context_menu = None
        self.coins_selected = []
        self.utxos = []

    def get_card(self, prev_h, prev_n, addr, amount, height):
        ci = {}
        ci['outpoint'] = f'{prev_h[:32]}...:{prev_n}'
        ci['address'] = addr
        ci['amount'] = self.app.format_amount_and_units(amount)
        ci['block_height'] = str(height)
        ci['prev_h'] = prev_h
        ci['prev_n'] = prev_n
        return ci

    def update(self):
        w = self.app.wallet
        utxos = w.get_utxos()
        utxos.sort()
        container = self.ids.scroll_container
        container.layout_manager.clear_selection()
        container.scroll_y = 1
        cards = []
        self.utxos = utxos
        for utxo in utxos:
            prev_h = utxo.prevout.txid.hex()
            prev_n = utxo.prevout.out_idx
            addr = utxo.address
            amount = utxo.value_sats()
            height = utxo.block_height
            card = self.get_card(prev_h, prev_n, addr, amount, height)
            cards.append(card)
        container.data = cards

    def hide_menu(self):
        if self.context_menu is not None:
            self.cmbox.remove_widget(self.context_menu)
            self.context_menu = None

    def clear_selection(self):
        container = self.ids.scroll_container
        container.layout_manager.clear_selection()

    def selection_changed(self, nodes):
        w = self.app.wallet
        self.hide_menu()
        self.coins_selected = [self.utxos[i] for i in nodes]
        if not self.coins_selected:
            self.selected_str = ''
            self.ids.clear_btn.disabled = True
            return
        else:
            self.selected_str = f' ({len(self.coins_selected)})'
            self.ids.clear_btn.disabled = False
