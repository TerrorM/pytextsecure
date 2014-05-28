from gi.repository import Gtk, Gdk, GObject, GLib
from gi.overrides import keysyms

class MessageWindow(object):

    hid = 0 # drag_data_received handler id
    (
            CLOSE_TAB_MIDDLE_CLICK,
            CLOSE_ESC,
            CLOSE_CLOSE_BUTTON,
            CLOSE_COMMAND,
            CLOSE_CTRL_KEY
    ) = range(5)


    def __init__(self, parent_window=None, parent_paned=None):
                # A dictionary of dictionaries
        # where _contacts[account][jid] == A MessageControl
        self._controls = {}

        # dict { handler id: widget}. Keeps callbacks, which
        # lead to cylcular references
        self.handlers = {}

        # Don't show warning dialogs when we want to delete the window
        self.dont_warn_on_delete = False


        self.window = parent_window
        self.parent_paned = parent_paned

        self.widget_name = 'message_window'
        self.xml = Gtk.Builder()
        self.xml.add_from_file('glade/' + self.widget_name + '.glade')
        self.window = self.xml.get_object(self.widget_name)
        self.notebook = self.xml.get_object('notebook')
        self.parent_paned = None

        orig_window = self.window
        self.window = parent_window
        self.parent_paned = parent_paned
        self.notebook.reparent(self.parent_paned)
        #self.parent_paned.pack2(self.notebook, resize=True, shrink=True)
        orig_window.destroy()
        del orig_window

        # NOTE: we use 'connect_after' here because in
        # MessageWindowMgr._new_window we register handler that saves window
        # state when closing it, and it should be called before
        # MessageWindow._on_window_delete, which manually destroys window
        # through win.destroy() - this means no additional handlers for
        # 'delete-event' are called.
        #id_ = self.window.connect_after('delete-event', self._on_window_delete)
        #self.handlers[id_] = self.window
        #id_ = self.window.connect('destroy', self._on_window_destroy)
        #self.handlers[id_] = self.window
        #id_ = self.window.connect('focus-in-event', self._on_window_focus)
        #self.handlers[id_] = self.window


        #id_ = self.notebook.connect('switch-page',
        #    self._on_notebook_switch_page)
        #self.handlers[id_] = self.notebook
        #id_ = self.notebook.connect('key-press-event',
        #    self._on_notebook_key_press)
        #self.handlers[id_] = self.notebook


    def new_tab(self, control):
        alias = control.get_alias()

        #if control.account not in self._controls:
        #    self._controls[control.account] = {}

        self._controls[alias] = control

        #if self.get_num_controls() == 2:
            # is first conversation_textview scrolled down ?
        #    scrolled = False
        #    first_widget = self.notebook.get_nth_page(0)
        #    ctrl = self._widget_to_control(first_widget)
        #    conv_textview = ctrl.conv_textview
        #    if conv_textview.at_the_end():
        #        scrolled = True
        #    self.notebook.set_show_tabs(True)
        #    if scrolled:
        #        GLib.idle_add(conv_textview.scroll_to_end_iter)

        # Add notebook page and connect up to the tab's close button
        xml = Gtk.Builder()
        xml.add_from_file('glade/message_window.glade')
        tab_label_box = xml.get_object('chat_tab_ebox')
        widget = xml.get_object('tab_close_button')
        # this reduces the size of the button
#        style = Gtk.RcStyle()
#        style.xthickness = 0
#        style.ythickness = 0
#        widget.modify_style(style)

        id_ = widget.connect('clicked', self._on_close_button_clicked, control)
        control.handlers[id_] = widget

        id_ = tab_label_box.connect('button-press-event',
            self.on_tab_eventbox_button_press_event, control.widget)
        control.handlers[id_] = tab_label_box
        self.notebook.append_page(control.widget, tab_label_box)

        self.notebook.set_tab_reorderable(control.widget, True)

        self.redraw_tab(control)
        if self.parent_paned:
            self.notebook.show_all()
        else:
            self.window.show_all()
        # NOTE: we do not call set_control_active(True) since we don't know
        # whether the tab is the active one.

        GLib.timeout_add(500, control.msg_textview.grab_focus)

    def set_active_tab(self, ctrl):
        ctrl_page = self.notebook.page_num(ctrl.widget)
        self.notebook.set_current_page(ctrl_page)
        self.window.present()
        GLib.idle_add(ctrl.msg_textview.grab_focus)


    def get_active_control(self):
        notebook = self.notebook
        active_widget = notebook.get_nth_page(notebook.get_current_page())
        return self._widget_to_control(active_widget)

    def _widget_to_control(self, widget):
        for ctrl in self.controls():
            if ctrl.widget == widget:
                return ctrl
        return None

    def controls(self):
        for ctrl in list(self._controls.values()):
            yield ctrl


    def redraw_tab(self, ctrl, chatstate = None):

        tab = self.notebook.get_tab_label(ctrl.widget)
        if not tab:
            return
        hbox = tab.get_children()[0]
        status_img = hbox.get_children()[0]
        nick_label = hbox.get_children()[1]


        # Update nick
        nick_label.set_max_width_chars(10)
        tab_label_str = ctrl.get_tab_label()
        nick_label.set_markup(tab_label_str)

    def is_active(self):
        return self.window.is_active()


    def on_tab_eventbox_button_press_event(self, widget, event, child):
        if event.button == 3: # right click
            n = self.notebook.page_num(child)
            self.notebook.set_current_page(n)
            self.popup_menu(event)
        elif event.button == 2: # middle click
            ctrl = self._widget_to_control(child)
            self.remove_tab(ctrl, self.CLOSE_TAB_MIDDLE_CLICK)
        else:
            ctrl = self._widget_to_control(child)
            GLib.idle_add(ctrl.msg_textview.grab_focus)

    def remove_tab(self, ctrl, method, reason = None, force = False):
        """
        Reason is only for gc (offline status message) if force is True, do not
        ask any confirmation
        """
        def close(ctrl):
            #if reason is not None: # We are leaving gc with a status message
            #    ctrl.shutdown(reason)
            #else: # We are leaving gc without status message or it's a chat
            #    ctrl.shutdown()
            # Update external state
            #gajim.events.remove_events(ctrl.account, ctrl.get_full_jid,
            #        types = ['printed_msg', 'chat', 'gc_msg'])

            alias = ctrl.get_alias()
            #jid = gajim.get_jid_without_resource(fjid)

            fctrl = self.get_control(alias)
            #bctrl = self.get_control(jid, ctrl.account)
            # keep last_message_time around unless this was our last control with
            # that jid
            #if not fctrl and not bctrl and \
            #fjid in gajim.last_message_time[ctrl.account]:
            #    del gajim.last_message_time[ctrl.account][fjid]

            self.notebook.remove_page(self.notebook.page_num(ctrl.widget))

            del self._controls[alias]

            #if len(self._controls[ctrl.account]) == 0:
            #    del self._controls[ctrl.account]

            #self.check_tabs()
            #self.show_title()

        def on_yes(ctrl):
            close(ctrl)

        def on_no(ctrl):
            return

        def on_minimize(ctrl):
            if method != self.CLOSE_COMMAND:
                ctrl.minimize()
                self.check_tabs()
                return
            close(ctrl)

        # Shutdown the MessageControl
        close(ctrl)

    def _on_close_button_clicked(self, button, control):
        """
        When close button is pressed: close a tab
        """
        self.remove_tab(control, self.CLOSE_CLOSE_BUTTON)


    def get_control(self, key):
        """
        Return the MessageControl for alias or n, where n is a notebook page index.
        When key is an int index acct may be None
        """

        if isinstance(key, str):
            alias = key
            try:
                return self._controls[alias]
            except Exception:
                return None
        else:
            page_num = key
            notebook = self.notebook
            if page_num is None:
                page_num = notebook.get_current_page()
            nth_child = notebook.get_nth_page(page_num)
            return self._widget_to_control(nth_child)


class MessageWindowMgr(GObject.GObject):
    """
    A manager and factory for MessageWindow objects
    """

    __gsignals__ = {
            'window-delete': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self, parent_window, parent_paned):

        GObject.GObject.__init__(self)
        self._windows = {}

        self.parent_win = parent_window
        self.parent_paned = parent_paned

    def get_control(self, alias):
        """
        Amongst all windows, return the MessageControl for jid
        """
        win = self.get_window()
        if win:
            return win.get_control(alias)
        return None


    def get_window(self):
        if self._windows != {}:
            return self._windows

        return None

    def has_control(self, alias):
        return (alias in self._controls)

    def windows(self):
        for w in list(self._windows.values()):
            yield w

    def create_window(self):

        win = self._windows

        if win == {}:
            win = self._new_window()

        #if win_role:
        #    win.window.set_role(win_role)

        self._windows = win
        return win

    def _new_window(self):
        parent_win = self.parent_win
        parent_paned = self.parent_paned
        win = MessageWindow(parent_win, parent_paned)
        # we track the lifetime of this window
        win.window.connect('delete-event', self._on_window_delete)
        win.window.connect('destroy', self._on_window_destroy)
        return win

    def _on_window_delete(self, win, event):
        if self.dont_warn_on_delete:
            # Destroy the window
            return False

        # Number of controls that will be closed and for which we'll loose data:
        # chat, pm, gc that won't go in roster
        number_of_closed_control = 0
        for ctrl in self.controls():
            if not ctrl.safe_shutdown():
                number_of_closed_control += 1

        if number_of_closed_control > 1:
            def on_yes1(checked):
                if checked:
                    gajim.config.set('confirm_close_multiple_tabs', False)
                self.dont_warn_on_delete = True
                for ctrl in self.controls():
                    if ctrl.minimizable():
                        ctrl.minimize()
                win.destroy()

            if not gajim.config.get('confirm_close_multiple_tabs'):
                # destroy window
                return False
            dialogs.YesNoDialog(
                _('You are going to close several tabs'),
                _('Do you really want to close them all?'),
                checktext=_('_Do not ask me again'), on_response_yes=on_yes1,
                transient_for=self.window)
            return True

        def on_yes(ctrl):
            if self.on_delete_ok == 1:
                self.dont_warn_on_delete = True
                win.destroy()
            self.on_delete_ok -= 1

        def on_no(ctrl):
            return

    def _on_window_destroy(self, win):
        for ctrl in self.controls():
            ctrl.shutdown()
        self._controls.clear()
        # Clean up handlers connected to the parent window, this is important since
        # self.window may be the RosterWindow
        for i in list(self.handlers.keys()):
            if self.handlers[i].handler_is_connected(i):
                self.handlers[i].disconnect(i)
            del self.handlers[i]
        del self.handlers
