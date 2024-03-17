import argparse
from .grpc import GatewayClient
from nvmeof_top.collector import DataCollector, DummyCollector
from nvmeof_top.utils import abort
import threading
import time
import logging
import urwid  # type: ignore
from nvmeof_top.ui import palette, Header, SubsystemInfo, NamespaceTable, HelpInformation, Options, CPUStats
from typing import Union

logger = logging.getLogger(__name__)


class NVMeoFTop:
    text_headers = ['NSID', 'RBD pool/image', 'IOPS', 'r/s', 'rMB/s', 'r_await', 'rareq-sz', 'w/s', 'wMB/s', 'w_await', 'wareq-sz', 'LBGrp', 'QoS']
    text_template = "{:>4}   {:<40}   {:>7}   {:>6}   {:>6}   {:>7}   {:>8}   {:>6}   {:>6}   {:>7}   {:>8}   {:^5}   {:>3}\n"

    def __init__(self, args: argparse.Namespace, client: GatewayClient):
        self.client = client
        self.args = args
        self.delay = args.delay
        self.subsystem_nqn = args.subsystem
        self.collector: Union[DataCollector, DummyCollector]
        self.ui_loop: urwid.MainLoop

        # these variables are used to hold the UI objects
        self.header: Header
        self.cpustats: CPUStats
        self.subsystem: SubsystemInfo
        self.namespaces: NamespaceTable

        # this list should match the UI object names. It is iterated over to call the update() methods
        # of each UI component
        self.panels = [
            'header',
            'cpustats',
            'subsystem',
            'namespaces'
        ]

        self.cpu_per_core = False
        self.ui = None
        self.components = None
        self.options: Options
        self.sort_key = 'NSID'
        self.refresh_paused = False
        self.reverse_sort = False

        self.help: HelpInformation
        self.read_latency_threshold = 0
        self.write_latency_threshold = 0

    @property
    def debug(self):
        return self.args.demo is not None

    def to_stdout(self):
        """Dump namespace performance stats to stdout"""
        logger.debug("writing stats to stdout")
        sort_pos = NVMeoFTop.text_headers.index(self.sort_key)
        with self.collector.lock:
            ns_data = self.collector.get_sorted_namespaces(sort_pos=sort_pos)
            # ns_data = self.collector.namespaces

        rows = []
        if self.args.with_timestamp:
            tstamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.collector.timestamp))
            rows.append(f"{tstamp}\n")
        if not self.args.no_headings:
            rows.append(NVMeoFTop.text_template.format(*NVMeoFTop.text_headers))
        if ns_data:
            # ns_data.sort(key=lambda x: x.nsid, reverse=False)
            for ns in ns_data:
                # row = self.build_ns_row(ns)
                rows.append(NVMeoFTop.text_template.format(*ns))
        else:
            rows.append("<no namespaces defined>\n")

        print(''.join(rows), end='')

    def options_handler(self, user_data):
        """Callback handler invoked when the user hits 'Apply' in the Options screen"""
        logger.debug(f"received {user_data}")
        logger.info("applying any changes to runtime options")

        if user_data['subsystem'] != self.subsystem_nqn:
            logger.info(f"Changing subsystem collection to {user_data['subsystem']}")
            self.collector.update_subsystem(user_data['subsystem'])
            self.subsystem_nqn = user_data['subsystem']
            self.subsystem.update()
            self.collector.reset_namespace_data()

        if user_data['sort_key'] != self.sort_key:
            logger.debug(f"changing sort key from {self.sort_key} to {user_data['sort_key']}")
            self.sort_key = user_data['sort_key']
            self.namespaces.update()

        if self.delay != user_data['delay']:
            logger.debug(f"changing refresh delay from {self.delay} to {user_data['delay']}")

            self.delay = user_data['delay']

        if self.read_latency_threshold != user_data['read_latency_threshold']:
            logger.debug(f"changing read latency threshold from {self.read_latency_threshold} to {user_data['read_latency_threshold']}")
            self.read_latency_threshold = user_data['read_latency_threshold']
            self.namespaces.update()

        if self.write_latency_threshold != user_data['write_latency_threshold']:
            logger.debug(f"changing write latency threshold from {self.write_latency_threshold} to {user_data['write_latency_threshold']}")
            self.write_latency_threshold = user_data['write_latency_threshold']
            self.namespaces.update()

        self.options.visible = False
        self.reset_ui()

    def reset_ui(self):
        self.loop.widget = self.ui

    @property
    def modal_active(self) -> bool:
        return self.help.visible or self.options.visible

    def quit_ui(self) -> None:
        logger.info("User has pressed 'q' or 'esc' to quit the ui")
        raise urwid.ExitMainLoop

    def default_key_handler(self, key) -> None:
        """Define the default handler for keypresses not managed by child components"""
        if key in ['Q', 'q']:
            self.quit_ui()
        elif key == 'esc':
            if not self.modal_active:
                self.quit_ui()
            if self.help.visible:
                logger.debug('esc pressed, hiding the help modal')
                self.help.visible = False
                self.loop.widget = self.ui
                return
            if self.options.visible:
                logger.debug('esc pressed, option changes skipped')
                self.options.visible = False
                self.loop.widget = self.ui
                return
        elif key in ['P', 'p']:
            self.refresh_paused = not self.refresh_paused
            pause_state = 'paused' if self.refresh_paused else 'resumed'
            logger.info(f"User {pause_state} the refresh")
            self.header.update()
            return

        if not self.refresh_paused:

            if key in ['c', 'C'] and self.collector.cpustats_enabled:
                self.cpu_per_core = not self.cpu_per_core
                logger.debug(f"Show cpu usage per core: {self.cpu_per_core}")
                self.cpustats.update()
                return
            elif key in ['O', 'o']:
                if self.refresh_paused:
                    return

                self.options.visible = not self.options.visible
                if self.options.visible:
                    # +2 is added to the height to account for the line border
                    self.loop.widget = urwid.Overlay(
                        self.options,
                        self.ui,
                        align=("relative", 50),
                        valign=("relative", 50),
                        width=("relative", 60),
                        height=(self.options.page_height + 2),
                        min_width=50)
                else:
                    self.loop.widget = self.ui

            elif key in ['s', 'S']:
                logger.info('changing the namespace sort direction')
                self.reverse_sort = not self.reverse_sort
                self.namespaces.update()
                return
            elif key in ('H', 'h'):
                self.help.visible = not self.help.visible
                if self.help.visible:

                    # +2 is added to the height to account for the line border
                    self.loop.widget = urwid.Overlay(
                        self.help,
                        self.ui,
                        align=("relative", 50),
                        valign=("relative", 50),
                        width=("relative", 60),
                        height=(self.help.page_height + 2),
                        min_width=50)
                else:
                    self.loop.widget = self.ui

        logger.debug(f"ui parent has received an unmanaged {key} keypress")

    def _build_ui(self) -> urwid.Frame:
        """Create the layout of the App"""

        title_colors = 'title-debug' if self.debug else 'title'
        title = urwid.AttrMap(self.header, title_colors)
        self.components = urwid.Pile([
            self.cpustats,
            self.subsystem,
            urwid.Divider(),
            self.namespaces
        ])
        self.body = urwid.Filler(
            self.components,
            valign='top'
        )

        return urwid.Frame(
            self.body,
            header=title,
            footer=None
        )

    def _update_panels(self) -> None:
        logger.debug("running _update_panels")
        for panel_name in self.panels:
            panel = getattr(self, panel_name)
            panel.update()

    def refresh_ui(self, loop_object, data) -> None:
        if not self.refresh_paused:
            logger.debug("updating all panels")
            self._update_panels()

        self.loop.set_alarm_at(time.time() + self.delay, self.refresh_ui, None)

    def console_mode(self) -> None:
        logger.info(f"Running in console mode querying {self.args.subsystem}")
        self.help = HelpInformation(self)
        self.header = Header(self)
        self.cpustats = CPUStats(self)
        self.subsystem = SubsystemInfo(self)
        self.namespaces = NamespaceTable(self, NVMeoFTop.text_headers, NVMeoFTop.text_template)
        self.options = Options(self, self.options_handler)
        self.options.visible = False
        self.ui = self._build_ui()
        self.loop = urwid.MainLoop(
            self.ui,
            palette=palette,
            pop_ups=True,
            unhandled_input=self.default_key_handler
        )
        self.loop.set_alarm_at(time.time() + self.delay, self.refresh_ui, None)

        try:
            self.loop.run()
        except urwid.widget.WidgetError:
            abort(12, "Terminal window is too small")
        except KeyboardInterrupt:
            abort(0, "User quit with CTRL-C")

    def batch_mode(self) -> None:
        logger.info(f"Running in batch mode querying {self.args.subsystem}")
        event = threading.Event()
        ctr = 0
        try:
            print("waiting for samples...")
            while not event.is_set():
                if not self.collector.ready:
                    abort(self.collector.health.rc, self.collector.health.msg)

                if self.collector.samples_ready:
                    self.to_stdout()
                    if self.args.count:
                        ctr += 1
                        if ctr > self.args.count:
                            break
                event.wait(self.delay)

        except KeyboardInterrupt:
            logger.info("nvmeof-top stopped by user")

        print("\nnvmeof-top stopped.")

    def run(self) -> None:
        if self.debug:
            self.collector = DummyCollector(self, self.args.demo)
        else:
            self.collector = DataCollector(self)
        logger.info(f"nvmeof-top running with a {self.collector.__class__.__name__} collector")

        self.collector.initialise()
        if not self.collector.ready:
            abort(self.collector.health.rc, self.collector.health.msg)

        t = threading.Thread(target=self.collector.run, daemon=True)
        t.start()

        if self.args.batch:
            self.batch_mode()
        else:
            self.console_mode()
