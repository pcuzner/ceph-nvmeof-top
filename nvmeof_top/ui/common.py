import urwid  # noqa: F401 type: ignore
import string

palette = [
    ('title', 'dark blue,bold', ''),
    ('title-debug', 'dark red,bold', ''),
    ('normal', '', ''),
    ('warning', 'yellow', ''),
    ('error', 'dark red', ''),
    ('error msg', 'white,bold', 'dark red', ''),
    ('bold', 'white,bold', ''),
    ('paused', 'black', 'white'),
    ('pgm', 'dark blue,bold', ''),
    ('border', 'dark blue', ''),
    ('box-button', 'white', 'dark blue'),
    ('box-button-highlight', 'white,bold', 'dark blue'),
    ('bar busy', 'dark green', 'dark gray'),
    ('bar idle', 'dark gray', 'dark gray'),
    ('bar busy:bar idle', 'dark green', 'dark gray'),
    ('pb normal', 'white', '', 'standout'),
    ('pb complete', 'white', 'dark blue'),
    ('pb smooth', 'dark blue', '')
]

BLOCK_HORIZONTAL = [chr(x) for x in range(0x258F, 0x2587, -1)]


class GenericComponent(urwid.Padding):

    def __init__(self):
        self.focus_support = True
        self.colour = 'normal'
        self.visible = True
        self.content = []
        widget = self._build_widget()

        super().__init__(widget)

    def _build_widget(self):
        return urwid.Padding(urwid.Text(""))

    def _build_table(self):
        raise NotImplementedError("build_table called by not implemented")

    def update(self):
        self.original_widget = self._build_widget()


class BoxButton(urwid.WidgetWrap):
    """Inspired by https://stackoverflow.com/a/65871001/778272"""
    def __init__(self, label, on_press):
        label_widget = urwid.Text(label, align='center')
        self.widget = urwid.LineBox(label_widget)
        self.hidden_button = urwid.Button('hidden button', on_press=on_press)
        super().__init__(self.widget)

    def selectable(self):
        return True

    def keypress(self, *args, **kwargs):
        return self.hidden_button.keypress(*args, **kwargs)

    def mouse_event(self, *args, **kwargs):
        return self.hidden_button.mouse_event(*args, **kwargs)


class FixedEdit(urwid.Edit):
    """Edit fields with fixed maximum length and validation"""

    def __init__(self, caption="",
                 edit_text="", multiline=False,
                 align='left', wrap='any', allow_tab=False,
                 valid_chars=string.printable,
                 width=0):

        self.max_width = width
        self.valid_chars = valid_chars

        super().__init__(
            caption=caption,
            edit_text=edit_text,
            multiline=multiline,
            align=align,
            wrap=wrap,
            allow_tab=allow_tab
        )

    def keypress(self, size, key):
        rc = urwid.Edit.keypress(self, size, key)

        if len(self.edit_text) > self.max_width:
            self.edit_text = self.edit_text[0:self.max_width]
        else:
            urwid.emit_signal(self, 'change')

        return rc

    def valid_char(self, ch):
        # if the field is full disregard the keypress
        if len(self.edit_text) == self.max_width:
            return False
        else:
            # otherwise check for the validity of the key
            return True if ch in self.valid_chars else False
