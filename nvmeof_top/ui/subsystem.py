import urwid
from .common import GenericComponent


class SubsystemInfo(GenericComponent):

    def __init__(self, parent):
        self.parent = parent
        super().__init__()

    def _build_widget(self):
        active = self.parent.collector.connections_active
        defined = self.parent.collector.connections_defined
        return urwid.Columns([
            (52, urwid.Text(('normal', f'Subsystem: {self.parent.collector.subsystem_nqn}'))),
            (22, urwid.Text(('normal', f'Total IOPS: {self.parent.collector.total_iops:8,}'))),
            (26, urwid.Text(('normal', f'Throughput: {(self.parent.collector.total_bandwidth / 1024**2):>7.2f} MiB/s'), align='left')),
            (21, urwid.Text([
                ('normal', f'Namespaces: {self.parent.collector.total_namespaces_defined:}/'),
                ('warning', '256')])),
            (25, urwid.Text(('normal', f'Clients: {active}/{defined}')))
        ], dividechars=2)
