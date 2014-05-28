
from message_control import MessageControl
from message_textview import MessageTextView
from conversation_textview import ConversationTextview

import threading

from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gdk

class ChatControlBase(MessageControl):

    def __init__(self, type_id, parent_win, widget_name, contact):
        # Undo needs this variable to know if space has been pressed.
        # Initialize it to True so empty textview is saved in undo list
        self.space_pressed = True

        MessageControl.__init__(self, type_id, parent_win, widget_name, contact)

        # Create textviews and connect signals
        self.conv_textview = ConversationTextview()

        id_ = self.conv_textview.tv.connect('key_press_event',
            self._conv_textview_key_press_event)
        self.handlers[id_] = self.conv_textview.tv


        self.conv_scrolledwindow = self.xml.get_object(
            'conversation_scrolledwindow')
        self.conv_scrolledwindow.add(self.conv_textview.tv)
        widget = self.conv_scrolledwindow.get_vadjustment()
        id_ = widget.connect('value-changed',
            self.on_conversation_vadjustment_value_changed)
        self.handlers[id_] = widget
        id_ = widget.connect('changed',
            self.on_conversation_vadjustment_changed)
        self.handlers[id_] = widget
        self.scroll_to_end_id = None
        self.was_at_the_end = True
        self.correcting = False
        self.last_sent_msg = None
        self.last_sent_txt = None
        self.last_received_txt = {} # one per name
        self.last_received_id = {} # one per name

        # add MessageTextView to UI and connect signals
        self.msg_scrolledwindow = self.xml.get_object('message_scrolledwindow')
        self.msg_textview = MessageTextView()
        id_ = self.msg_textview.connect('mykeypress',
            self._on_message_textview_mykeypress_event)
        self.handlers[id_] = self.msg_textview
        self.msg_scrolledwindow.add(self.msg_textview)
        id_ = self.msg_textview.connect('key_press_event',
            self._on_message_textview_key_press_event)
        self.handlers[id_] = self.msg_textview
        #id_ = self.msg_textview.connect('configure-event',
        #    self.on_configure_event)
        #self.handlers[id_] = self.msg_textview
        #id_ = self.msg_textview.connect('populate_popup',
        #    self.on_msg_textview_populate_popup)
        #self.handlers[id_] = self.msg_textview
        # Setup DND
        #id_ = self.msg_textview.connect('drag_data_received',
        #    self._on_drag_data_received)
        #self.handlers[id_] = self.msg_textview
        #self.msg_textview.drag_dest_set(Gtk.DestDefaults.MOTION |
        #    Gtk.DestDefaults.HIGHLIGHT, self.dnd_list, Gdk.DragAction.COPY)

        #self.update_font()

        # Hook up send button
        #widget = self.xml.get_object('send_button')
        #id_ = widget.connect('clicked', self._on_send_button_clicked)
        #widget.set_sensitive(False)
        #self.handlers[id_] = widget

        #widget = self.xml.get_object('formattings_button')
        #id_ = widget.connect('clicked', self.on_formattings_button_clicked)
        #self.handlers[id_] = widget

        # the following vars are used to keep history of user's messages
        self.sent_history = []
        self.sent_history_pos = 0
        self.received_history = []
        self.received_history_pos = 0
        self.orig_msg = None

        # Attach speller
        #if gajim.config.get('use_speller') and HAS_GTK_SPELL:
        #    self.set_speller()
        #self.conv_textview.tv.show()
        #self._paint_banner()

        # For XEP-0172
        self.user_nick = None

        self.smooth = True

        self.command_hits = []
        self.last_key_tabs = False

        # PluginSystem: adding GUI extension point for ChatControlBase
        # instance object (also subclasses, eg. ChatControl or GroupchatControl)
        #gajim.plugin_manager.gui_extension_point('chat_control_base', self)

        #gajim.ged.register_event_handler('our-show', ged.GUI1,
        #    self._nec_our_status)
        #gajim.ged.register_event_handler('ping-sent', ged.GUI1,
        #    self._nec_ping_sent)
        #gajim.ged.register_event_handler('ping-reply', ged.GUI1,
        #    self._nec_ping_reply)
        #gajim.ged.register_event_handler('ping-error', ged.GUI1,
        #    self._nec_ping_error)

        # This is bascially a very nasty hack to surpass the inability
        # to properly use the super, because of the old code.
        #CommandTools.__init__(self)

    def _conv_textview_key_press_event(self, widget, event):
        # translate any layout to latin_layout
        valid, entries = self.keymap.get_entries_for_keyval(event.keyval)
        keycode = entries[0].keycode
        if (event.get_state() & Gdk.ModifierType.CONTROL_MASK and keycode in (
        self.keycode_c, self.keycode_ins)) or (
        event.get_state() & Gdk.ModifierType.SHIFT_MASK and \
        event.keyval in (Gdk.KEY_Page_Down, Gdk.KEY_Page_Up)):
            return False
        self.parent_win.notebook.event(event)
        return True

    def _on_message_textview_key_press_event(self, widget, event):
        if event.keyval == Gdk.KEY_space:
            self.space_pressed = True

        elif (self.space_pressed or self.msg_textview.undo_pressed) and \
        event.keyval not in (Gdk.KEY_Control_L, Gdk.KEY_Control_R) and \
        not (event.keyval == Gdk.KEY_z and event.get_state() & Gdk.ModifierType.CONTROL_MASK):
            # If the space key has been pressed and now it hasnt,
            # we save the buffer into the undo list. But be carefull we're not
            # pressiong Control again (as in ctrl+z)
            _buffer = widget.get_buffer()
            start_iter, end_iter = _buffer.get_bounds()
            self.msg_textview.save_undo(_buffer.get_text(start_iter, end_iter, True))
            self.space_pressed = False

        # Ctrl [+ Shift] + Tab are not forwarded to notebook. We handle it here
        if self.widget_name == 'groupchat_control':
            if event.keyval not in (Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Tab):
                self.last_key_tabs = False
        if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            # CTRL + SHIFT + TAB
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK and \
                            event.keyval == Gdk.KEY_ISO_Left_Tab:
                self.parent_win.move_to_next_unread_tab(False)
                return True
            # SHIFT + PAGE_[UP|DOWN]: send to conv_textview
            elif event.keyval == Gdk.KEY_Page_Down or \
                            event.keyval == Gdk.KEY_Page_Up:
                self.conv_textview.tv.event(event)
                return True
        elif event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            if event.keyval == Gdk.KEY_Tab:  # CTRL + TAB
                self.parent_win.move_to_next_unread_tab(True)
                return True
################################################################################
        # temporary solution instead Gtk.binding_entry_add_signal
        message_buffer = self.msg_textview.get_buffer()
        event_state = event.get_state()
        if event.keyval == Gdk.KEY_Up:
            if event_state & Gdk.ModifierType.CONTROL_MASK:
                if event_state & Gdk.ModifierType.SHIFT_MASK: # Ctrl+Shift+UP
                    self.scroll_messages('up', message_buffer, 'received')
                else:  # Ctrl+UP
                    self.scroll_messages('up', message_buffer, 'sent')
            return True
        elif event.keyval == Gdk.KEY_Down:
            if event_state & Gdk.ModifierType.CONTROL_MASK:
                if event_state & Gdk.ModifierType.SHIFT_MASK: # Ctrl+Shift+Down
                    self.scroll_messages('down', message_buffer, 'received')
                else:  # Ctrl+Down
                    self.scroll_messages('down', message_buffer, 'sent')
            return True

        elif event.keyval == Gdk.KEY_Return or \
        event.keyval == Gdk.KEY_KP_Enter:  # ENTER
            message_textview = widget
            message_buffer = message_textview.get_buffer()
            start_iter, end_iter = message_buffer.get_bounds()
            message = message_buffer.get_text(start_iter, end_iter, False)
            xhtml = self.msg_textview.get_xhtml()

            if event_state & Gdk.ModifierType.CONTROL_MASK:  # Ctrl + ENTER
                end_iter = message_buffer.get_end_iter()
                message_buffer.insert_at_cursor('\n')
                send_message = False
            else: # ENTER
                send_message = True

            #if gajim.connections[self.account].connected < 2 and send_message:
                # we are not connected
            #    dialogs.ErrorDialog(_('A connection is not available'),
            #            _('Your message can not be sent until you are connected.'))
            #    send_message = False

            if send_message:
                self.send_message(message) # send the message
            return True
        elif event.keyval == Gdk.KEY_z: # CTRL+z
            if event_state & Gdk.ModifierType.CONTROL_MASK:
                self.msg_textview.undo()
                return True
################################################################################
        return False


    def _on_message_textview_mykeypress_event(self, widget, event_keyval,
    event_keymod):
        """
        When a key is pressed: if enter is pressed without the shift key, message
        (if not empty) is sent and printed in the conversation
        """
        # NOTE: handles mykeypress which is custom signal connected to this
        # CB in new_tab(). for this singal see message_textview.py
        message_textview = widget
        message_buffer = message_textview.get_buffer()
        start_iter, end_iter = message_buffer.get_bounds()
        message = message_buffer.get_text(start_iter, end_iter, False)
        xhtml = self.msg_textview.get_xhtml()

        # construct event instance from binding
        event = Gdk.Event(Gdk.EventType.KEY_PRESS)  # it's always a key-press here
        event.keyval = event_keyval
        event.state = event_keymod
        event.time = 0  # assign current time

        if event.keyval == Gdk.KEY_Up:
            if event.get_state() == Gdk.ModifierType.CONTROL_MASK:  # Ctrl+UP
                self.scroll_messages('up', message_buffer, 'sent')
            # Ctrl+Shift+UP
            elif event.get_state() == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
                self.scroll_messages('up', message_buffer, 'received')
        elif event.keyval == Gdk.KEY_Down:
            if event.get_state() == Gdk.ModifierType.CONTROL_MASK:  # Ctrl+Down
                self.scroll_messages('down', message_buffer, 'sent')
            # Ctrl+Shift+Down
            elif event.get_state() == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
                self.scroll_messages('down', message_buffer, 'received')
        elif event.keyval == Gdk.KEY_Return or \
                event.keyval == Gdk.KEY_KP_Enter:  # ENTER
            # NOTE: SHIFT + ENTER is not needed to be emulated as it is not
            # binding at all (textview's default action is newline)

            if gajim.config.get('send_on_ctrl_enter'):
                # here, we emulate GTK default action on ENTER (add new line)
                # normally I would add in keypress but it gets way to complex
                # to get instant result on changing this advanced setting
                if event.get_state() == 0:  # no ctrl, no shift just ENTER add newline
                    end_iter = message_buffer.get_end_iter()
                    message_buffer.insert_at_cursor('\n')
                    send_message = False
                elif event.get_state() & Gdk.ModifierType.CONTROL_MASK:  # CTRL + ENTER
                    send_message = True
            else: # send on Enter, do newline on Ctrl Enter
                if event.get_state() & Gdk.ModifierType.CONTROL_MASK:  # Ctrl + ENTER
                    end_iter = message_buffer.get_end_iter()
                    message_buffer.insert_at_cursor('\n')
                    send_message = False
                else: # ENTER
                    send_message = True

            if gajim.connections[self.account].connected < 2 and send_message:
                # we are not connected
                dialogs.ErrorDialog(_('A connection is not available'),
                        _('Your message can not be sent until you are connected.'))
                send_message = False

            if send_message:
                self.send_message(message, xhtml=xhtml) # send the message
        elif event.keyval == Gdk.KEY_z: # CTRL+z
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                self.msg_textview.undo()
        else:
            # Give the control itself a chance to process
            self.handle_message_textview_mykey_press(widget, event_keyval,
                    event_keymod)


    def on_conversation_vadjustment_changed(self, adjustment):
        # used to stay at the end of the textview when we shrink conversation
        # textview.
        if self.was_at_the_end:
            if self.conv_textview.at_the_end():
                # we are at the end
                self.conv_textview.bring_scroll_to_end(-18)
            else:
                self.conv_textview.bring_scroll_to_end(-18, use_smooth=False)
        self.was_at_the_end = (adjustment.get_upper() - adjustment.get_value()\
            - adjustment.get_page_size()) < 18

    def on_conversation_vadjustment_value_changed(self, adjustment):
        # stop automatic scroll when we manually scroll
        if not self.conv_textview.auto_scrolling:
            self.conv_textview.stop_scrolling()
        self.was_at_the_end = (adjustment.get_upper() - adjustment.get_value() \
            - adjustment.get_page_size()) < 18

    def shutdown(self):
        super(ChatControlBase, self).shutdown()



    def send_message(self, message):
        """
        Send the given message to the active tab. Doesn't return None if error
        """
        if not message or message == '\n':
            return None

        #if process_commands and self.process_as_command(message):
        #    return

        #label = self.get_seclabel()

        def _cb(msg, cb, *cb_args):
            self.last_sent_msg = msg
            self.last_sent_txt = cb_args[0]
            if cb:
                cb(msg, *cb_args)

        if self.correcting and self.last_sent_msg:
            correction_msg = self.last_sent_msg
        else:
            correction_msg = None

        #gajim.nec.push_outgoing_event(MessageOutgoingEvent(None,
        #    account=self.account, jid=self.contact.jid, message=message,
        #    keyID=keyID, type_=type_, chatstate=chatstate, msg_id=msg_id,
        #    resource=resource, user_nick=self.user_nick, xhtml=xhtml,
        #    label=label, callback=_cb, callback_args=[callback] + callback_args,
        #    control=self, attention=attention, correction_msg=correction_msg))

        print('sending message...')
        import push_message
        threading.Thread(target=push_message.handleSendMms,
             args=(message, self.contact ),
              ).start()
        #self.set_chat_text(' > ' + message, widget)

        # Record the history of sent messages
        #self.save_message(message, 'sent')

        # Be sure to send user nickname only once according to JEP-0172
        #self.user_nick = None

        # Clear msg input
        message_buffer = self.msg_textview.get_buffer()
        message_buffer.set_text('') # clear message buffer (and tv of course)


    def print_conversation_line(self, text, kind, name):
        """
        Print 'chat' type messages
        correct_id = (message_id, correct_id)
        """
        jid = self.contact
        full_jid = self.get_alias()
        textview = self.conv_textview
        end = False
        if self.was_at_the_end or kind == 'outgoing':
            end = True
        old_txt = ''
        if name in self.last_received_txt:
            old_txt = self.last_received_txt[name]

        textview.print_conversation_line(text, jid, kind, name)

        if not self.parent_win:
            return

        if (not self.parent_win.get_active_control() or \
        self != self.parent_win.get_active_control() or \
        not self.parent_win.is_active() or not end) and \
        kind in ('incoming', 'incoming_queue', 'error'):
            self.parent_win.redraw_tab(self)
            #if not self.parent_win.is_active():
            #    self.parent_win.show_title(True, self) # Enabled Urgent hint
            #else:
            #    self.parent_win.show_title(False, self) # Disabled Urgent hint



class ChatControl(ChatControlBase):

    def __init__(self, parent_win, contact):
        ChatControlBase.__init__(self, 'chat', parent_win,
            'chat_control', contact)

    def update_ui(self):
        # The name banner is drawn here
        ChatControlBase.update_ui(self)

    def get_tab_label(self):

        name = self.contact

        label_str = GLib.markup_escape_text(name)

        return label_str

    def shutdown(self):


        self.msg_textview.destroy()
        # PluginSystem: calling shutdown of super class (ChatControlBase) to let
        # it remove it's GUI extension points
        super(ChatControl, self).shutdown()


    def send_message(self, message, keyID='', chatstate=None, xhtml=None,
    process_commands=True, attention=False):
        """
        Send a message to contact
        """

        contact = self.contact

        ChatControlBase.send_message(self, message )

        self.print_conversation(message, self.contact)

    def print_conversation(self, text, frm='', tim=None, encrypted=False,
    subject=None, xhtml=None, simple=False, xep0184_id=None,
    displaymarking=None, msg_id=None, correct_id=None):
        """
        Print a line in the conversation

        If frm is set to status: it's a status message.
        if frm is set to error: it's an error message. The difference between
                status and error is mainly that with error, msg count as a new message
                (in systray and in control).
        If frm is set to info: it's a information message.
        If frm is set to print_queue: it is incomming from queue.
        If frm is set to another value: it's an outgoing message.
        If frm is not set: it's an incomming message.
        """
        contact = self.contact


        if not frm:
            kind = 'incoming'
            name = self.contact
        else:
            kind = 'outgoing'
            name = self.get_our_nick()

        ChatControlBase.print_conversation_line(self, text, kind, name)

    def get_our_nick(self):
        return 'You'