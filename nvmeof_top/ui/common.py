import urwid  # noqa: F401 type: ignore
from typing import List, ClassVar
import string
import logging
logger = logging.getLogger(__name__)

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
    ('pb smooth', 'dark blue', ''),
    ('reveal focus', 'black', 'dark blue', 'standout')
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


class PullDownOptions:
    def __init__(self, options_list: List[str], min_width: int = 20, default: int = 0):
        self.items = options_list
        self.min_width = min_width
        self._default = default

    @property
    def width(self):
        max_options_width = max([len(item) for item in self.items])
        return max([self.min_width, max_options_width]) + 7

    @property
    def default(self):
        return self.items[self._default]


class CustomButton(urwid.Button):
    button_left = urwid.Text('')
    button_right = urwid.Text('\u25bc')  # down arrow


class SelectableText(urwid.Text):
    def __init__(self, markup, cb):
        super().__init__(markup=markup)
        self.cb = cb

    def selectable(self):
        return True

    def keypress(self, size, key):
        logger.debug(f"in keypress of the selectabletext widget with key: *{key}*")
        if key in ['enter', ' ']:
            self.cb(self.text)
            return
        elif key == 'esc':
            self.cb('')
            return

        return key


class PopUpDialog(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button"""

    signals: ClassVar[list[str]] = ["close"]

    def __init__(self, options, cb, offset: int = 2):
        # close_button = urwid.Button("Cancel")
        # urwid.connect_signal(close_button, "click", lambda button: self._emit("close"))

        # the item is offset for better alignment within the linebox
        items = [urwid.AttrMap(urwid.Padding(SelectableText(f"{item}", cb), align='left', left=offset, right=0), '', 'reveal focus') for item in options.items]

        dialog = urwid.LineBox(
            urwid.ListBox(
                urwid.SimpleListWalker(items)
            ),
            tline=u' ',
            tlcorner=u'│',
            trcorner=u'│',)
        super().__init__(urwid.AttrMap(dialog, "popbg"))


class PullDown(urwid.PopUpLauncher):

    def __init__(self, options: PullDownOptions) -> None:
        self.options = options
        self.selected_option = self.options.default
        super().__init__(CustomButton(self.selected_option, on_press=self.open_pop_up))
        # urwid.connect_signal(self.original_widget, "click", lambda button: self.open_pop_up())

    def create_pop_up(self) -> PopUpDialog:
        pop_up = PopUpDialog(self.options, self.cb_selected)
        return pop_up

    def open_pop_up(self, *args):
        self._pop_up_widget = self.create_pop_up()
        self._invalidate()

    def cb_selected(self, content):
        logger.debug(content)
        if content:
            self.selected_option = content
        self._original_widget = CustomButton(self.selected_option, on_press=self.open_pop_up)
        # urwid.connect_signal(self.original_widget, "click", lambda button: self.open_pop_up())
        self.close_pop_up()

    @property
    def width(self):
        max_options_width = max([len(item) for item in self.options])
        return max([self.min_width, max_options_width])

    @property
    def height(self):
        return len(self.options.items) + 2

    def get_pop_up_parameters(self):
        """Handle the positioning of the popup relative to the original widget

        A -1 value for left is used to account for the positioning when a LineBox is used to wrap
        the original widget
        """
        return {"left": -1, "top": 1, "overlay_width": self.options.width, "overlay_height": self.height}
