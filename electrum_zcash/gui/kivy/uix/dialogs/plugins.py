#!/usr/bin/env python
# -*- coding: utf-8 -*-

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from electrum_zcash.gui.kivy.i18n import _
from electrum_zcash.logging import Logger
from electrum_zcash.plugin import run_hook


Builder.load_string('''
<PluginLabel@ButtonBehavior+Label>
    text_size: self.size
    halign: 'left'
    valign: 'middle'


<PluginWidget@BoxLayout>
    fullname: ''
    orientation: 'horizontal'
    size_hint: 0.6, None
    height: '48dp'
    CheckBox:
        id: cb
        disabled: False
        active: False
        size_hint: None, 1
        width: '48dp'
        on_active: root.on_cb_active(self.active)
    PluginLabel:
        on_release: cb.active = not cb.active
        text: root.fullname
        disabled: cb.disabled


<SettingsBox@BoxLayout>
    orientation: 'horizontal'
    size_hint: 0.4, None
    height: '48dp'


<PluginHelp@Button>
    help_text: ''
    size_hint: None, None
    size: '48dp', '48dp'
    text: '?'


<PluginsDialog@Popup>
    title: _('Plugins')
    BoxLayout:
        orientation: 'vertical'
        padding: '10dp', '10dp'
        ScrollView:
            GridLayout:
                id: grid
                cols: 3
                spacing: '5dp'
                size_hint: 1, None
                height: self.minimum_height
        Button:
            text: _('Close')
            size_hint: 1, None
            height: '48dp'
            on_release: root.dismiss()
''')


class PluginWidget(BoxLayout):

    def __init__(self, *, app, name, fullname, settings_box):
        super(PluginWidget, self).__init__()
        self.app = app
        self.fullname = fullname
        self.name = name
        self.settings_box = settings_box
        self.active = False

    def update_settings_box(self, plugin):
        settings_widget = None
        if plugin and plugin.requires_settings() and plugin.is_enabled():
            settings_widget = plugin.settings_widget(self.app)
        self.settings_box.update(settings_widget)

    def update(self, from_cb=False):
        plugins = self.app.plugins
        wallet = self.app.wallet
        p = plugins.get(self.name)
        cb = self.ids.cb
        cb.disabled = (not p and not plugins.is_available(self.name, wallet)
                       or p and not p.is_available()
                       or p and not p.can_user_disable())
        self.active = bool(p and p.is_enabled())
        self.update_settings_box(p)
        if cb.active != self.active:
            cb.active = self.active

    def on_cb_active(self, is_checked):
        if self.active != is_checked:
            self.app.plugins.toggle(self.name)
            self.update()
            run_hook('init_kivy', self.app)


class SettingsBox(BoxLayout):

    def update(self, widget):
        self.clear_widgets()
        if widget:
            self.add_widget(widget)


class PluginHelp(Button):

    def __init__(self, *, app, help_text):
        super(PluginHelp, self).__init__()
        self.app = app
        self.help_text = help_text

    def on_release(self):
            width = self.app.root.width * 0.8
            self.app.show_info_bubble(text=self.help_text, width=width,
                                      arrow_pos=None)


class PluginsDialog(Factory.Popup, Logger):

    def __init__(self, app):
        super(PluginsDialog, self).__init__()
        self.app = app
        self.config = app.electrum_config
        self.network = app.network
        plugins = app.plugins
        grid = self.ids.grid
        for i, plugin_dict in enumerate(plugins.descriptions.values()):
            if plugin_dict.get('registers_keystore'):
                continue
            try:
                module_name = plugin_dict['__name__']
                prefix, _separator, name = module_name.rpartition('.')
                settings_box = SettingsBox()
                plugin_widget = PluginWidget(app=app, name=name,
                                             fullname=plugin_dict['fullname'],
                                             settings_box=settings_box)
                grid.add_widget(plugin_widget)
                grid.add_widget(settings_box)

                help_text = plugin_dict['description']
                requires = plugin_dict.get('requires')
                if requires:
                    help_text += '\n\n' + _('Requires') + ':\n'
                    help_text += '\n'.join(map(lambda x: x[1], requires))
                plugin_help = PluginHelp(app=app, help_text=help_text)
                grid.add_widget(plugin_help)
            except Exception as e:
                self.logger.exception(f'cannot display plugin {name}')

    def update(self):
        for widget in self.ids.grid.children:
            if isinstance(widget, PluginWidget):
                widget.update()
