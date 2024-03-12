import urwid
from .common import GenericComponent
import logging

logger = logging.getLogger(__name__)


class HelpInformation(GenericComponent):
    divide_chars = 3

    def __init__(self, parent):
        self.parent = parent
        super().__init__()

        self.visible = False

    @property
    def page_height(self):
        return len(self.content) + 2

    def _build_widget(self):
        self.content = [
            urwid.Divider(),
            urwid.Text([
                ('pgm', 'nvmeof-top'),
                " is a command line tool to monitor the performance of a specific nvme subsystem (nqn) "
                "provided by a Ceph NVMe-oF Gateway."
            ]),
            urwid.Divider(),
            urwid.Text("The following interactive commands are supported: "),
            urwid.Divider(),
            urwid.Columns([
                (5, urwid.Text(('bold', 'h'), align='right')),
                urwid.Text(('normal', 'Display this help page!'))
            ], dividechars=self.divide_chars),
            urwid.Columns([
                (5, urwid.Text(('bold', 'o'), align='right')),
                urwid.Text(('normal', 'Change runtime options like refresh interval, latency thresholds and sort sequence'))
            ], dividechars=self.divide_chars),
            urwid.Columns([
                (5, urwid.Text(('bold', 'p'), align='right')),
                urwid.Text(('normal', 'Pause the automatic refresh (toggles refresh on and off)'))
            ], dividechars=self.divide_chars),
            urwid.Columns([
                (5, urwid.Text(('bold', 'q'), align='right')),
                urwid.Text('Quit the application')
            ], dividechars=self.divide_chars),
            urwid.Columns([
                (5, urwid.Text(('bold', 's'), align='right')),
                urwid.Text('Change the sort direction')
            ], dividechars=self.divide_chars),
            urwid.Divider(),
            urwid.Text("Press 'h' or 'esc' to return.")
        ]

        if self.parent.collector.cpustats_enabled:
            logger.debug("adding 'c' command info to the help page since the collector provides CPU stats")
            self.content.insert(5, urwid.Columns([
                                (5, urwid.Text(('bold', 'c'), align='right')),
                                urwid.Text(('normal', 'CPU usage stats. Toggle between overview and per core views'))
                                ], dividechars=self.divide_chars))

        content = urwid.SimpleListWalker(
            [urwid.AttrMap(widget, None, "normal") for widget in self.content])

        return \
            urwid.LineBox(
                urwid.Filler(
                    urwid.Padding(
                        urwid.BoxAdapter(
                            urwid.ListBox(content),
                            height=self.page_height),
                        left=1,
                        right=1
                    ),
                    'top'),
                title="Help"
            )
