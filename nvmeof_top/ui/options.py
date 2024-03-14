import urwid  # type: ignore
import logging
from .common import GenericComponent, BoxButton, FixedEdit
from nvmeof_top.utils import valid_nqn
import string
from typing import List

logger = logging.getLogger(__name__)


class Options(GenericComponent):

    def __init__(self, parent, callback):
        self.parent = parent
        self.content = []
        self.callback = callback

        self.radio_button_state = self.parent.sort_key
        self.input_subsystem = None
        self.input_delay = None
        self.input_sort_key = None
        self.input_read_threshold = None
        self.input_write_threshold = None
        self.current_subsystem = self.parent.subsystem_nqn
        self.current_delay = str(self.parent.delay)

        self.container = None  # container widget holding all the content

        self.error = urwid.Text(('normal', ''))

        super().__init__()

    @property
    def page_height(self) -> int:
        return len(self.content) + 7

    def _valid_options(self) -> bool:
        """Validate the options the user has provided"""

        current_subsystem = self.input_subsystem.edit_text
        try:
            valid_nqn(current_subsystem)
        except ValueError as err:
            logger.error(f"user provided nqn of '{current_subsystem}' which is an invalid")
            self.error = urwid.Text(('error', f'Invalid subsystem name (nqn) format: {str(err)}'))
            self.current_subsystem = current_subsystem
            self.update()
            self.container.set_focus(3)
            return False

        if current_subsystem not in self.parent.collector.nqn_list:
            logger.error(f"user provided nqn of '{current_subsystem}' does not exist on this gateway")
            self.error = urwid.Text(('error', 'Subsystem is not defined to this gateway'))
            self.current_subsystem = current_subsystem
            self.update()
            self.container.set_focus(3)
            return False

        if len(self.input_delay.edit_text) == 0:
            logger.info("user provided a null value for delay, which is invalid!")

            self.error = urwid.Text(('error', 'Delay must be provided'))
            self.current_delay = self.input_delay.edit_text
            self.update()
            self.container.set_focus(5)
            return False

        if int(self.input_delay.edit_text) < 1:
            logger.info("user supplied delay of 0 makes no sense, it must be >= 1")

            self.error = urwid.Text(('error'), 'Delay must be set to 1 or higher')
            self.current_delay = self.input_delay.edit_text
            self.update()
            self.container.set_focus(5)
            return False

        self.error = urwid.Text(('normal', ''))
        return True

    def update_parent(self, component) -> None:
        """Check the options, and if appropriate pass them back to the parent object (main UI)"""
        if not self._valid_options():
            logger.info("invalid options provided, unable to apply. User needs to make some changes.")
            return
        logger.info("Updating options")
        logger.debug(f"radio button {self.radio_button_state}")
        data = {
            'subsystem': self.input_subsystem.edit_text,
            'delay': int(self.input_delay.edit_text),
            'sort_key': self.radio_button_state,
            'read_latency_threshold': int(self.input_read_threshold.edit_text),
            'write_latency_threshold': int(self.input_write_threshold.edit_text),
        }
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
        self.input_subsystem = FixedEdit(caption="Subsystem: ", edit_text=self.current_subsystem, multiline=False, align='left', allow_tab=False, width=40)
        self.input_read_threshold = FixedEdit(caption="Read Latency (ms): ", edit_text=str(self.parent.read_latency_threshold), width=2, valid_chars=string.digits)
        self.input_write_threshold = FixedEdit(caption="Write Latency (ms): ", edit_text=str(self.parent.write_latency_threshold), width=2, valid_chars=string.digits)
        sort_options: List[urwid.RadioButton] = []
        for key in self.parent.text_headers:
            urwid.RadioButton(sort_options, label=key, on_state_change=self.update_sort_key, user_data=key)

        # reminder set_focus on self.container uses the index position of the widget in this list
        self.content = [
            urwid.Divider(),
            urwid.Text("To change runtime options, make the required changes below and press 'Apply'. "
                       "To abort your changes simply press 'esc'."),
            urwid.Divider(),
            self.input_subsystem,
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
                urwid.Text(''),
                (9, urwid.AttrMap(BoxButton('Apply', on_press=self.update_parent), 'box-button', 'box-button-highlight'))
            ]),
            urwid.Divider(),
            self.error
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
