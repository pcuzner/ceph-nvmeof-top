import urwid  # type: ignore
import logging
from .common import GenericComponent, BoxButton, FixedEdit, PullDown, PullDownOptions
# from nvmeof_top.utils import valid_nqn
import string
from typing import List

logger = logging.getLogger(__name__)


class Options(GenericComponent):

    def __init__(self, parent, callback) -> None:
        self.parent = parent
        self.content = []
        self.callback = callback

        self.radio_button_state = self.parent.sort_key
        self.subsystem_pulldown: PullDown
        self.input_delay: FixedEdit
        self.input_read_threshold: FixedEdit
        self.input_write_threshold: FixedEdit
        self.current_subsystem = self.parent.subsystem_nqn
        self.current_delay = str(self.parent.delay)

        self.container: urwid.ListBox  # container widget holding all the content

        self.error = urwid.Text(('normal', ''))

        super().__init__()

    @property
    def page_height(self) -> int:
        return len(self.content) + 9

    def _valid_options(self) -> bool:
        """Validate the options the user has provided"""

        if not self.valid_delay():
            logger.info(f"user supplied an invalid delay value: {self.input_delay.edit_text}")
            self.error = urwid.Text(('error', "'Delay' must be set a positive number > 0"))
            self.current_delay = self.input_delay.edit_text
            self.update()
            self.container.set_focus(5)
            return False

        self.error = urwid.Text(('normal', ''))
        return True

    def valid_delay(self):
        if len(self.input_delay.edit_text) == 0:
            return False
        if int(self.input_delay.edit_text) < 1:
            return False
        return True

    def update_parent(self, component) -> None:
        """Check the options, and if appropriate pass them back to the parent object (main UI)"""
        if not self._valid_options():
            logger.info("invalid options provided, unable to apply. User needs to make some changes.")
            return
        logger.info("Updating options")
        logger.debug(f"radio button {self.radio_button_state}")
        data = {
            'subsystem': self.subsystem_pulldown.selected_option,
            'delay': int(self.input_delay.edit_text),
            'sort_key': self.radio_button_state,
            'read_latency_threshold': int(self.input_read_threshold.edit_text),
            'write_latency_threshold': int(self.input_write_threshold.edit_text),
        }
        self.container.set_focus(3)
        self.callback(data)

    def update_sort_key(self, component, new_state, data) -> None:
        """Update the current active radio button state

        update_sort_key is called when a state change occurs within the whole button group
        so it will for one option checked, you will see 2 calls: one to turn off the old
        option (FALSE), and another to turn on the new option (TRUE)
        """
        logger.debug(f"radio button new state for {data} is {new_state}")
        if new_state:
            self.radio_button_state = data

    def _build_widget(self) -> urwid.Widget:
        self.input_delay = FixedEdit(caption="Refresh Delay: ", edit_text=self.current_delay, width=2, valid_chars=string.digits)
        self.input_read_threshold = FixedEdit(caption="Read Latency (ms): ", edit_text=str(self.parent.read_latency_threshold), width=2, valid_chars=string.digits)
        self.input_write_threshold = FixedEdit(caption="Write Latency (ms): ", edit_text=str(self.parent.write_latency_threshold), width=2, valid_chars=string.digits)
        sort_options: List[urwid.RadioButton] = []
        for key in self.parent.text_headers:
            urwid.RadioButton(sort_options, label=key, on_state_change=self.update_sort_key, user_data=key)

        options = PullDownOptions(options_list=self.parent.collector.nqn_list)
        self.subsystem_pulldown = PullDown(options)

        # reminder set_focus on self.container uses the index position of the widget in this list
        self.content = [
            urwid.Divider(),
            urwid.Text("To change runtime options, make the required changes below and press 'Apply'. "
                       "To abort your changes simply press 'esc'."),
            urwid.Divider(),
            urwid.Columns([
                (12, urwid.Text('\nSubsystem: ')),
                (options.width, urwid.LineBox(self.subsystem_pulldown)),
                urwid.Text('')
            ]),
            urwid.Divider(),
            self.input_delay,
            urwid.Divider(),
            urwid.Text('Latency thresholds for reads and writes may be defined to highlight performance anomalies. '
                       'A value of 0 disables the threshold.'),
            urwid.Columns([
                urwid.Text(''),
                (22, self.input_read_threshold),
                (23, self.input_write_threshold),
                urwid.Text(''),
            ], dividechars=5),
            urwid.Divider(),
            urwid.Text("Sort the namespaces by selecting a sort field below:"),
            urwid.GridFlow(cells=sort_options, cell_width=20, h_sep=2, v_sep=0, align='left'),
            urwid.Divider(),
            urwid.Columns([
                self.error,
                (9, urwid.AttrMap(BoxButton('Apply', on_press=self.update_parent), 'box-button', 'box-button-highlight'))
            ]),
        ]

        self.container = urwid.ListBox(self.content)

        return urwid.LineBox(
            urwid.Filler(
                urwid.Padding(
                    urwid.BoxAdapter(
                        self.container,
                        height=self.page_height),
                    left=1,
                    right=1
                ),
                'top'),
            title="Options"
        )
