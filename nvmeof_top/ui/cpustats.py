import urwid
from .common import GenericComponent
import logging
from typing import Union
logger = logging.getLogger(__name__)


class CPUStats(GenericComponent):
    def __init__(self, parent):
        self.parent = parent
        super().__init__()

    def _determine_colour(self, value: Union[int, float]):
        if value >= 90:
            return 'error'
        elif value >= 80:
            return 'warning'
        return 'normal'

    def _build_widget(self):
        logger.debug("_build_widgets called for cpustats")
        widgets = []
        if self.parent.collector.cpustats_enabled:
            logger.debug(f"parents cpu_per_core flag: {self.parent.cpu_per_core}")
            logger.debug("fetching cpu stats")
            thread_stats = self.parent.collector.get_cpu_stats()
            cpu_busy = []
            for name, stats in thread_stats.items():
                if name == 'app_thread':
                    continue
                cpu_busy.append(stats.busy_rate)

            total_cores = len(cpu_busy)
            total_cpu_busy = sum(cpu_busy)
            total_color = self._determine_colour(total_cpu_busy / total_cores)
            avg_cpu_busy = sum(cpu_busy) / len(cpu_busy)
            avg_color = self._determine_colour(avg_cpu_busy)
            min_cpu_busy = min(cpu_busy)
            min_color = self._determine_colour(min_cpu_busy)
            max_cpu_busy = max(cpu_busy)
            max_color = self._determine_colour(max_cpu_busy)
            widgets.append(urwid.Columns([
                (18, (urwid.Text(f"Reactor Cores: {total_cores:>2}"))),
                (11, (urwid.Text(('normal', "Total CPU:"), align='right'))),
                (7, (urwid.Text((total_color, f"{total_cpu_busy:>4}%  ")))),
                (8, (urwid.Text(('normal', "AVG CPU:")))),
                (7, (urwid.Text((avg_color, f"{avg_cpu_busy:4.1f}%  ")))),
                (8, (urwid.Text(('normal', "Min CPU:"), align='right'))),
                (6, (urwid.Text((min_color, f"{min_cpu_busy:3}%  ")))),
                (8, (urwid.Text(('normal', "Max CPU:"), align='right'))),
                (6, (urwid.Text((max_color, f"{max_cpu_busy:3}%  ")))),
                urwid.Text('')
            ], dividechars=1))
            if self.parent.cpu_per_core:
                for thread_name in thread_stats.keys():
                    if thread_name == 'app_thread':
                        # ignore this thread
                        continue
                    stats = thread_stats[thread_name]
                    hbar = urwid.ProgressBar('pb normal', 'pb complete', stats.busy_rate, 100, 'pb smooth')
                    widgets.append(urwid.Columns([
                        (22, urwid.Text(thread_name, align='left')),
                        (50, hbar),
                        # (4, urwid.Text((thread_color, f"{stats.busy_rate:>3}%"))),
                        urwid.Text('')
                    ], dividechars=2)
                    )

        logger.debug(f"cpustats contains {len(widgets)} widgets")
        # Using a Pile container enables the widget to occupy no space if cpu stats are not available
        return urwid.Pile(widgets)
