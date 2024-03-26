import urwid  # type: ignore
import time
from .common import GenericComponent
import logging

logger = logging.getLogger(__name__)


class Header(GenericComponent):

    def __init__(self, parent):
        self.parent = parent
        super().__init__()

    def _build_widget(self):

        color_attr = 'title-debug' if self.parent.debug else 'title'
        if hasattr(self.parent, 'collector'):
            obs_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.parent.collector.timestamp))
        else:
            obs_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

        if self.parent.refresh_paused:
            pause = ('paused', 'PAUSED')
        else:
            pause = ''

        return urwid.Columns([
            (10, urwid.Text((color_attr, 'nvmeof-top'), align='left')),
            (20, urwid.Text(('normal', f"   GW vers: {self.parent.collector.gw_info.version}"))),
            (27, urwid.Text(('normal', f"GW Address: {self.parent.args.server_addr}"))),
            (15, urwid.Text(('normal', f"Subsystems: {len(self.parent.collector.nqn_list)}"))),
            urwid.Text(''),
            urwid.Text([
                pause,
                ('normal', f' {obs_time} ')
            ], align='right')
        ], dividechars=3)
