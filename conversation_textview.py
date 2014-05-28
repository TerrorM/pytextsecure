from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import GLib

from htmltextview import HtmlTextView

import queue

from threading import Timer # for smooth scrolling

class ConversationTextview(GObject.GObject):
    """
    Class for the conversation textview (where user reads already said messages)
    for chat/groupchat windows
    """
    __gsignals__ = dict(
            quote = (GObject.SignalFlags.RUN_LAST | GObject.SignalFlags.ACTION,
                    None, # return value
                    (str, ) # arguments
            )
    )

    # smooth scroll constants
    MAX_SCROLL_TIME = 0.4 # seconds
    SCROLL_DELAY = 33 # milliseconds

    def __init__(self, used_in_history_window = False):
        """
        If used_in_history_window is True, then we do not show Clear menuitem in
        context menu
        """
        GObject.GObject.__init__(self)
        self.used_in_history_window = used_in_history_window

        #self.fc = FuzzyClock()


        # no need to inherit TextView, use it as atrribute is safer
        self.tv = HtmlTextView()
        #self.tv.hyperlink_handler = self.hyperlink_handler

        # set properties
        self.tv.set_border_width(1)
        self.tv.set_accepts_tab(True)
        self.tv.set_editable(False)
        self.tv.set_cursor_visible(False)
        self.tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.tv.set_left_margin(2)
        self.tv.set_right_margin(2)
        self.handlers = {}
        self.images = []
        self.image_cache = {}
        self.xep0184_marks = {}
        self.xep0184_shown = {}
        self.last_sent_message_marks = [None, None]
        # A pair per occupant. Key is '' in normal chat
        self.last_received_message_marks = {}

        # It's True when we scroll in the code, so we can detect scroll from user
        self.auto_scrolling = False

        # connect signals
        id_ = self.tv.connect('motion_notify_event',
                self.on_textview_motion_notify_event)
        self.handlers[id_] = self.tv
        id_ = self.tv.connect('populate_popup', self.on_textview_populate_popup)
        self.handlers[id_] = self.tv
        id_ = self.tv.connect('button_press_event',
                self.on_textview_button_press_event)
        self.handlers[id_] = self.tv

        id_ = self.tv.connect('draw', self.on_textview_draw)
        self.handlers[id_] = self.tv


        self.change_cursor = False
        self.last_time_printout = 0

        #font = Pango.FontDescription(gajim.config.get('conversation_font'))
        #self.tv.override_font(font)
        buffer_ = self.tv.get_buffer()
        end_iter = buffer_.get_end_iter()
        buffer_.create_mark('end', end_iter, False)

        #self.tagIn = buffer_.create_tag('incoming')
        #color = gajim.config.get('inmsgcolor')
        #font = Pango.FontDescription(gajim.config.get('inmsgfont'))
        #self.tagIn.set_property('foreground', color)
        #self.tagIn.set_property('font-desc', font)

        #self.tagOut = buffer_.create_tag('outgoing')
        #color = gajim.config.get('outmsgcolor')
        #font = Pango.FontDescription(gajim.config.get('outmsgfont'))
        #self.tagOut.set_property('foreground', color)
        #self.tagOut.set_property('font-desc', font)

        #self.tagStatus = buffer_.create_tag('status')
        #color = gajim.config.get('statusmsgcolor')
        #font = Pango.FontDescription(gajim.config.get('satusmsgfont'))
        #self.tagStatus.set_property('foreground', color)
        #self.tagStatus.set_property('font-desc', font)

        #self.tagInText = buffer_.create_tag('incomingtxt')
        #color = gajim.config.get('inmsgtxtcolor')
        #font = Pango.FontDescription(gajim.config.get('inmsgtxtfont'))
        #if color:
        #    self.tagInText.set_property('foreground', color)
        #self.tagInText.set_property('font-desc', font)

        #self.tagOutText = buffer_.create_tag('outgoingtxt')
        #color = gajim.config.get('outmsgtxtcolor')
        #if color:
        #    font = Pango.FontDescription(gajim.config.get('outmsgtxtfont'))
        #self.tagOutText.set_property('foreground', color)
        #self.tagOutText.set_property('font-desc', font)

        #colors = gajim.config.get('gc_nicknames_colors')
        #colors = colors.split(':')
        #for i, color in enumerate(colors):
        #    tagname = 'gc_nickname_color_' + str(i)
        #    tag = buffer_.create_tag(tagname)
        #    tag.set_property('foreground', color)

        #self.tagMarked = buffer_.create_tag('marked')
        #color = gajim.config.get('markedmsgcolor')
        #self.tagMarked.set_property('foreground', color)
        #self.tagMarked.set_property('weight', Pango.Weight.BOLD)

        #tag = buffer_.create_tag('time_sometimes')
        #tag.set_property('foreground', 'darkgrey')
        #Pango.SCALE_SMALL
        #tag.set_property('scale', 0.8333333333333)
        #tag.set_property('justification', Gtk.Justification.CENTER)

        #tag = buffer_.create_tag('small')
        #Pango.SCALE_SMALL
        #tag.set_property('scale', 0.8333333333333)

        #tag = buffer_.create_tag('restored_message')
        #color = gajim.config.get('restored_messages_color')
        #tag.set_property('foreground', color)

        #self.tv.create_tags()

        #tag = buffer_.create_tag('bold')
        #tag.set_property('weight', Pango.Weight.BOLD)

        #tag = buffer_.create_tag('italic')
        #tag.set_property('style', Pango.Style.ITALIC)

        #tag = buffer_.create_tag('underline')
        #tag.set_property('underline', Pango.Underline.SINGLE)

        #buffer_.create_tag('focus-out-line', justification = Gtk.Justification.CENTER)
        #self.displaymarking_tags = {}

        #tag = buffer_.create_tag('xep0184-warning')
        #tag.set_property('foreground', '#cc0000')

        #tag = buffer_.create_tag('xep0184-received')
        #tag.set_property('foreground', '#73d216')

        # One mark at the begining then 2 marks between each lines
        #size = gajim.config.get('max_conversation_lines')
        #size = 2 * size - 1
        #self.marks_queue = queue.Queue(size)

        self.allow_focus_out_line = True
        # holds a mark at the end of --- line
        self.focus_out_end_mark = None

        #self.xep0184_warning_tooltip = tooltips.BaseTooltip()

        #self.line_tooltip = tooltips.BaseTooltip()
        self.smooth_id = None
        self.just_cleared = False

        size = 500
        size = 2 * size - 1
        self.marks_queue = queue.Queue(size)

    def print_conversation_line(self, text, jid, kind, name):
        """
        Print 'chat' type messages
        """
        buffer_ = self.tv.get_buffer()
        buffer_.begin_user_action()

        if self.marks_queue.full():
            # remove oldest line
            m1 = self.marks_queue.get()
            m2 = self.marks_queue.get()
            i1 = buffer_.get_iter_at_mark(m1)
            i2 = buffer_.get_iter_at_mark(m2)
            buffer_.delete(i1, i2)
            buffer_.delete_mark(m1)

        end_iter = buffer_.get_end_iter()
        end_offset = end_iter.get_offset()
        at_the_end = self.at_the_end()
        move_selection = False
        if buffer_.get_has_selection() and buffer_.get_selection_bounds()[1].\
        get_offset() == end_offset:
            move_selection = True


        # Create one mark and add it to queue once if it's the first line
        # else twice (one for end bound, one for start bound)
        mark = None
        if buffer_.get_char_count() > 0:
            mark = buffer_.create_mark(None, end_iter, left_gravity=True)
            self.marks_queue.put(mark)
        if not mark:
            mark = buffer_.create_mark(None, end_iter, left_gravity=True)
        self.marks_queue.put(mark)

        if kind == 'incoming_queue':
            kind = 'incoming'

        # print the time stamp

        # We don't have tim for outgoing messages...
        import time
        tim = time.localtime()

        direction_mark = ''
        # don't apply direction mark if it's status message

        timestamp_str = self.get_time_to_show(tim, direction_mark)
        timestamp = time.strftime(timestamp_str, tim)
        timestamp = timestamp + ' '

        buffer_.insert (end_iter, timestamp)

        self.print_name(name, kind, direction_mark=direction_mark, iter_=end_iter)
        #if kind == 'incoming':
        #    text_tags.append('incomingtxt')
        #    mark1 = mark
        #elif kind == 'outgoing':
        #    text_tags.append('outgoingtxt')
        #    mark1 = mark

        #subject = None
        #self.print_subject(subject, iter_=end_iter)
        self.print_real_text(text, name, iter_=end_iter)


        # scroll to the end of the textview
        if at_the_end or kind == 'outgoing':
            # we are at the end or we are sending something
            # scroll to the end (via idle in case the scrollbar has appeared)
            if True:
                GLib.idle_add(self.smooth_scroll_to_end)
            else:
                GLib.idle_add(self.scroll_to_end)

        self.just_cleared = False
        buffer_.end_user_action()
        return end_iter

    # Smooth scrolling inspired by Pidgin code
    def smooth_scroll(self):
        parent = self.tv.get_parent()
        if not parent:
            return False
        vadj = parent.get_vadjustment()
        max_val = vadj.get_upper() - vadj.get_page_size() + 1
        cur_val = vadj.get_value()
        # scroll by 1/3rd of remaining distance
        onethird = cur_val + ((max_val - cur_val) / 3.0)
        self.auto_scrolling = True
        vadj.set_value(onethird)
        self.auto_scrolling = False
        if max_val - onethird < 0.01:
            self.smooth_id = None
            self.smooth_scroll_timer.cancel()
            return False
        return True

    def smooth_scroll_timeout(self):
        GLib.idle_add(self.do_smooth_scroll_timeout)
        return

    def do_smooth_scroll_timeout(self):
        if not self.smooth_id:
            # we finished scrolling
            return
        GLib.source_remove(self.smooth_id)
        self.smooth_id = None
        parent = self.tv.get_parent()
        if parent:
            vadj = parent.get_vadjustment()
            self.auto_scrolling = True
            vadj.set_value(vadj.get_upper() - vadj.get_page_size() + 1)
            self.auto_scrolling = False

    def smooth_scroll_to_end(self):
        if None != self.smooth_id: # already scrolling
            return False
        self.smooth_id = GLib.timeout_add(self.SCROLL_DELAY,
                self.smooth_scroll)
        self.smooth_scroll_timer = Timer(self.MAX_SCROLL_TIME,
                self.smooth_scroll_timeout)
        self.smooth_scroll_timer.start()
        return False

    def print_name(self, name, kind, direction_mark='', iter_=None):
        if name:
            buffer_ = self.tv.get_buffer()
            if iter_:
                end_iter = iter_
            else:
                end_iter = buffer_.get_end_iter()

            before_str = ''
            after_str = ':'
            format_ = before_str + name + direction_mark + after_str + ' '
            buffer_.insert(end_iter, format_)

    def print_real_text(self, text, name, iter_=None):
        """
        Add normal and special text. call this to add text
        """
        # /me is replaced by name if name is given
        if name and (text.startswith('/me ') or text.startswith('/me\n')):
            text = '* ' + name + text[3:]
            #text_tags.append('italic')
        # detect urls formatting and if the user has it on emoticons
        buffer_ = self.tv.get_buffer()
        buffer_.insert (iter_, text + "\n")
        #return self.detect_and_print_special_text(text, iter_=iter_)



    def get_time_to_show(self, tim, direction_mark=''):
        from calendar import timegm
        import time
        """
        Get the time, with the day before if needed and return it. It DOESN'T
        format a fuzzy time
        """
        format_ = ''
        # get difference in days since epoch (86400 = 24*3600)
        # number of days since epoch for current time (in GMT) -
        # number of days since epoch for message (in GMT)
        diff_day = int(int(timegm(time.localtime())) / 86400 -\
                int(timegm(tim)) / 86400)

        timestamp_str = '[%X]'
        format_ += timestamp_str
        tim_format = time.strftime(format_, tim)
        return tim_format

    def on_textview_motion_notify_event(self, widget, event):
        """
        Change the cursor to a hand when we are over a mail or an url
        """
        w = self.tv.get_window(Gtk.TextWindowType.TEXT)
        device = w.get_display().get_device_manager().get_client_pointer()
        pointer = w.get_device_position(device)
        x, y = self.tv.window_to_buffer_coords(Gtk.TextWindowType.TEXT,
            pointer[1], pointer[2])
        tags = self.tv.get_iter_at_location(x, y).get_tags()
        if self.change_cursor:
            w.set_cursor(Gdk.Cursor.new(Gdk.CursorType.XTERM))
            self.change_cursor = False
        tag_table = self.tv.get_buffer().get_tag_table()
        over_line = False
        xep0184_warning = False

        for tag in tags:
            if tag in (tag_table.lookup('url'), tag_table.lookup('mail'), \
            tag_table.lookup('xmpp'), tag_table.lookup('sth_at_sth')):
                w.set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND2))
                self.change_cursor = True
            elif tag == tag_table.lookup('focus-out-line'):
                over_line = True
            elif tag == tag_table.lookup('xep0184-warning'):
                xep0184_warning = True

        #if self.line_tooltip.timeout != 0:
            # Check if we should hide the line tooltip
        #    if not over_line:
        #        self.line_tooltip.hide_tooltip()
        #if self.xep0184_warning_tooltip.timeout != 0:
            # Check if we should hide the XEP-184 warning tooltip
        #    if not xep0184_warning:
        #        self.xep0184_warning_tooltip.hide_tooltip()
        if over_line and not self.line_tooltip.win:
            self.line_tooltip.timeout = GLib.timeout_add(500,
                    self.show_line_tooltip)
            w.set_cursor(Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR))
            self.change_cursor = True
        if xep0184_warning and not self.xep0184_warning_tooltip.win:
            self.xep0184_warning_tooltip.timeout = GLib.timeout_add(500,
                    self.show_xep0184_warning_tooltip)
            w.set_cursor(Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR))
            self.change_cursor = True


    def on_textview_populate_popup(self, textview, menu):
        """
        Override the default context menu and we prepend Clear (only if
        used_in_history_window is False) and if we have sth selected we show a
        submenu with actions on the phrase (see
        on_conversation_textview_button_press_event)
        """
        separator_menuitem_was_added = False


        menu.show_all()

    def on_textview_button_press_event(self, widget, event):
        # If we clicked on a taged text do NOT open the standard popup menu
        # if normal text check if we have sth selected
        self.selected_phrase = '' # do not move belove event button check!

        if event.button != 3: # if not right click
            return False

        x, y = self.tv.window_to_buffer_coords(Gtk.TextWindowType.TEXT,
                int(event.x), int(event.y))
        iter_ = self.tv.get_iter_at_location(x, y)
        tags = iter_.get_tags()

        if tags: # we clicked on sth special (it can be status message too)
            for tag in tags:
                tag_name = tag.get_property('name')
                if tag_name in ('url', 'mail', 'xmpp', 'sth_at_sth'):
                    return True # we block normal context menu

        # we check if sth was selected and if it was we assign
        # selected_phrase variable
        # so on_conversation_textview_populate_popup can use it
        buffer_ = self.tv.get_buffer()
        return_val = buffer_.get_selection_bounds()
        if return_val: # if sth was selected when we right-clicked
            # get the selected text
            start_sel, finish_sel = return_val[0], return_val[1]
            self.selected_phrase = buffer_.get_text(start_sel, finish_sel, True)
        elif iter_.get_char() and ord(iter_.get_char()) > 31:
            # we clicked on a word, do as if it's selected for context menu
            start_sel = iter_.copy()
            if not start_sel.starts_word():
                start_sel.backward_word_start()
            finish_sel = iter_.copy()
            if not finish_sel.ends_word():
                finish_sel.forward_word_end()
            self.selected_phrase = buffer_.get_text(start_sel, finish_sel, True)

    def on_textview_draw(self, widget, ctx):
        return
        #TODO
        expalloc = event.area
        exp_x0 = expalloc.x
        exp_y0 = expalloc.y
        exp_x1 = exp_x0 + expalloc.width
        exp_y1 = exp_y0 + expalloc.height

        try:
            tryfirst = [self.image_cache[(exp_x0, exp_y0)]]
        except KeyError:
            tryfirst = []

        for image in tryfirst + self.images:
            imgalloc = image.allocation
            img_x0 = imgalloc.x
            img_y0 = imgalloc.y
            img_x1 = img_x0 + imgalloc.width
            img_y1 = img_y0 + imgalloc.height

            if img_x0 <= exp_x0 and img_y0 <= exp_y0 and \
            exp_x1 <= img_x1 and exp_y1 <= img_y1:
                self.image_cache[(img_x0, img_y0)] = image
                widget.propagate_expose(image, event)
                return True
        return False

    def at_the_end(self):
        buffer_ = self.tv.get_buffer()
        end_iter = buffer_.get_end_iter()
        end_rect = self.tv.get_iter_location(end_iter)
        visible_rect = self.tv.get_visible_rect()
        if end_rect.y <= (visible_rect.y + visible_rect.height):
            return True
        return False

    def bring_scroll_to_end(self, diff_y = 0,
    use_smooth=True):
        ''' scrolls to the end of textview if end is not visible '''
        buffer_ = self.tv.get_buffer()
        end_iter = buffer_.get_end_iter()
        end_rect = self.tv.get_iter_location(end_iter)
        visible_rect = self.tv.get_visible_rect()
        # scroll only if expected end is not visible
        if end_rect.y >= (visible_rect.y + visible_rect.height + diff_y):
            if use_smooth:
                GLib.idle_add(self.smooth_scroll_to_end)
            else:
                GLib.idle_add(self.scroll_to_end_iter)
