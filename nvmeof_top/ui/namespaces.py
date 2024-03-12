import urwid
import re
from .common import GenericComponent
import logging
logger = logging.getLogger(__name__)


class NamespaceTable(GenericComponent):
    alignment_map = {
        '<': 'left',
        '>': 'right',
        '^': 'center'
    }

    def __init__(self, parent, headings, fmt_template):
        self.parent = parent
        self.collector = parent.collector
        self.headings = headings
        self.headings_fmt = fmt_template
        self.column_widths = re.findall(r'\d+', self.headings_fmt)
        self.column_alignment = re.findall(r'[<^>]', self.headings_fmt)
        self.dividechars = 3

        self.threshold_map = {}
        super().__init__()

    def _build_headings(self):
        th = []
        ptr = 0
        for hdr in self.headings:
            width = int(self.column_widths[ptr])
            alignment = self._column_alignment(ptr)
            col_attr = 'bold' if hdr == self.parent.sort_key else 'normal'

            th.append((width, urwid.Text((col_attr, hdr), align=alignment)))
            ptr += 1
        return urwid.Columns(th, dividechars=self.dividechars)

    def _get_color_by_threshold(self, ptr: int, field: str):
        if self.threshold_map[ptr] > 0 and float(field) > self.threshold_map[ptr]:
            return 'warning'
        return 'normal'

    def _refresh_thresholds_map(self):
        return {
            self.headings.index('r_await'): float(self.parent.read_latency_threshold),
            self.headings.index('w_await'): float(self.parent.write_latency_threshold),
        }

    def _build_rows(self):
        self.threshold_map = self._refresh_thresholds_map()
        rows = []
        if self.collector.samples_ready:
            ns_data = self.collector.get_sorted_namespaces(sort_pos=self.headings.index(self.parent.sort_key))
            for ns in ns_data:
                cols = []
                ptr = 0
                for field in ns:
                    alignment = self._column_alignment(ptr)
                    column_color = 'normal'
                    if ptr in self.threshold_map:
                        column_color = self._get_color_by_threshold(ptr, field)
                    cols.append((int(self.column_widths[ptr]), urwid.Text((column_color, str(field)), align=alignment)))
                    ptr += 1
                rows.append(urwid.Columns(cols, dividechars=self.dividechars))
            if not ns_data:
                rows.append(urwid.Text(('warning', 'No Namespaces found')))
        else:
            rows.append(urwid.Text(('warning', 'waiting for data...')))

        return urwid.Pile(rows)

    def _column_alignment(self, pos) -> str:
        return NamespaceTable.alignment_map[self.column_alignment[pos]]

    def _build_widget(self):
        th = self._build_headings()
        rows = self._build_rows()
        return urwid.Pile([th, rows])
