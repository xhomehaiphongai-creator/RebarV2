# -*- coding: utf-8 -*-

import clr
clr.AddReference("PresentationCore")
clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")

from System.Windows.Controls import TextBlock, Panel
from System.Windows.Shapes import Rectangle, Line
from System.Windows.Media import Brushes, SolidColorBrush, Color


class ColumnPreviewController(object):
    def __init__(self, canvas, info_text=None, on_selection_changed=None):
        self.canvas = canvas
        self.info_text = info_text
        self.on_selection_changed = on_selection_changed
        self.column_infos = []
        self.selected_index = -1
        self.hit_rects = []

    def set_data(self, column_infos):
        self.column_infos = column_infos or []
        if self.column_infos:
            if self.selected_index < 0 or self.selected_index >= len(self.column_infos):
                self.selected_index = 0
        else:
            self.selected_index = -1
        self.redraw()

    def get_selected_info(self):
        if self.selected_index < 0:
            return None
        if self.selected_index >= len(self.column_infos):
            return None
        return self.column_infos[self.selected_index]

    def redraw(self):
        self.canvas.Children.Clear()
        self.hit_rects = []

        if not self.column_infos:
            self._update_info_text()
            return

        try:
            w = self.canvas.ActualWidth
            h = self.canvas.ActualHeight
        except:
            w = 360
            h = 560

        if w < 50:
            w = 360
        if h < 50:
            h = 560

        pad_left = 80.0
        pad_right = 80.0
        pad_top = 18.0
        pad_bottom = 22.0

        draw_w = max(50.0, w - pad_left - pad_right)
        draw_h = max(50.0, h - pad_top - pad_bottom)

        min_z = min([x["z_min_ft"] for x in self.column_infos])
        max_z = max([x["z_max_ft"] for x in self.column_infos])

        min_cx = min([x["center_x_ft"] for x in self.column_infos])
        max_cx = max([x["center_x_ft"] for x in self.column_infos])

        use_y = False
        if abs(max_cx - min_cx) < 1e-6:
            min_cx = min([x["center_y_ft"] for x in self.column_infos])
            max_cx = max([x["center_y_ft"] for x in self.column_infos])
            use_y = True

        max_width_ft = 0.0
        for info in self.column_infos:
            col_w_ft = abs(info["width_mm"]) / 304.8
            col_d_ft = abs(info["depth_mm"]) / 304.8
            max_width_ft = max(max_width_ft, col_w_ft, col_d_ft)

        if max_width_ft < 1e-6:
            max_width_ft = 1.0

        range_z = max(max_z - min_z, 1.0)
        range_x = max((max_cx - min_cx), max_width_ft * 1.5, 1.0)

        sx = draw_w / range_x
        sy = draw_h / range_z
        scale = min(sx, sy)

        origin_x = pad_left + (draw_w - range_x * scale) * 0.5
        origin_y = pad_top + draw_h

        level_map = {}
        for i, info in enumerate(self.column_infos):
            z0 = info["z_min_ft"]
            z1 = info["z_max_ft"]

            center_ft = info["center_y_ft"] if use_y else info["center_x_ft"]
            width_ft = max(abs(info["width_mm"]) / 304.8, abs(info["depth_mm"]) / 304.8)

            x = origin_x + (center_ft - min_cx) * scale - width_ft * scale * 0.5
            y = origin_y - (z1 - min_z) * scale
            rw = max(10.0, width_ft * scale)
            rh = max(18.0, (z1 - z0) * scale)

            body = Rectangle()
            body.Width = rw
            body.Height = rh
            body.Stroke = Brushes.DarkGreen
            body.Fill = SolidColorBrush(Color.FromRgb(95, 190, 123))
            body.StrokeThickness = 1.5
            body.SetValue(self.canvas.LeftProperty, x)
            body.SetValue(self.canvas.TopProperty, y)
            self.canvas.Children.Add(body)
            Panel.SetZIndex(body, 1)

            inner = Rectangle()
            inner.Width = max(1.0, rw - 4.0)
            inner.Height = max(1.0, rh - 4.0)
            inner.Stroke = Brushes.Red
            inner.StrokeThickness = 0.8
            inner.Fill = Brushes.Transparent
            inner.SetValue(self.canvas.LeftProperty, x + 2.0)
            inner.SetValue(self.canvas.TopProperty, y + 2.0)
            self.canvas.Children.Add(inner)
            Panel.SetZIndex(inner, 2)

            hit = Rectangle()
            hit.Width = rw + 10.0
            hit.Height = rh + 10.0
            hit.Fill = Brushes.Transparent
            hit.Stroke = Brushes.Transparent
            hit.Tag = i
            hit.SetValue(self.canvas.LeftProperty, x - 5.0)
            hit.SetValue(self.canvas.TopProperty, y - 5.0)
            hit.MouseLeftButtonDown += self._on_segment_click
            self.canvas.Children.Add(hit)
            Panel.SetZIndex(hit, 20)
            self.hit_rects.append(hit)

            left_text = TextBlock()
            left_text.Text = u"Height = {0:.0f} (mm)\nBxH = {1:.0f}x{2:.0f}\nMark : {3}".format(
                info["height_mm"], info["width_mm"], info["depth_mm"], info["mark"]
            )
            left_text.FontSize = 11
            left_text.Foreground = Brushes.Black
            left_text.SetValue(self.canvas.LeftProperty, max(4.0, x - 128.0))
            left_text.SetValue(self.canvas.TopProperty, y + max(8.0, rh * 0.18))
            self.canvas.Children.Add(left_text)
            Panel.SetZIndex(left_text, 5)

            right_text = TextBlock()
            right_text.Text = u"Main Rebar: 4Ø18\nDistribute: L1, L2, L1"
            right_text.FontSize = 11
            right_text.Foreground = Brushes.Red
            right_text.SetValue(self.canvas.LeftProperty, x + rw + 12.0)
            right_text.SetValue(self.canvas.TopProperty, y + max(8.0, rh * 0.18))
            self.canvas.Children.Add(right_text)
            Panel.SetZIndex(right_text, 5)

            key_base = round(z0, 6)
            if key_base not in level_map:
                level_map[key_base] = {
                    "y": origin_y - (z0 - min_z) * scale,
                    "name": info["base_level"],
                    "offset": info["base_offset_mm"]
                }

            is_topmost = (i == len(self.column_infos) - 1)
            if not is_topmost:
                key_top = round(z1, 6)
                if key_top not in level_map:
                    level_map[key_top] = {
                        "y": origin_y - (z1 - min_z) * scale,
                        "name": info["top_level"],
                        "offset": info["top_offset_mm"]
                    }

        self._draw_levels(level_map, w)
        self._update_selection_visual()
        self._update_info_text()

    def _draw_levels(self, level_map, canvas_w):
        keys = sorted(level_map.keys(), reverse=True)
        for key in keys:
            item = level_map[key]
            y = item["y"]

            ln = Line()
            ln.X1 = 10.0
            ln.X2 = canvas_w - 10.0
            ln.Y1 = y
            ln.Y2 = y
            ln.Stroke = Brushes.Gray
            ln.StrokeThickness = 0.8
            ln.StrokeDashArray.Add(3)
            ln.StrokeDashArray.Add(2)
            self.canvas.Children.Add(ln)
            Panel.SetZIndex(ln, 0)

            txt = TextBlock()
            if item["offset"] and abs(item["offset"]) > 0.1:
                txt.Text = u"▼ {0} ({1:+.0f})".format(item["name"], item["offset"])
            else:
                txt.Text = u"▼ {0}".format(item["name"])
            txt.FontSize = 11
            txt.Foreground = Brushes.Black
            txt.Background = Brushes.White
            txt.SetValue(self.canvas.LeftProperty, canvas_w * 0.5 + 6.0)
            txt.SetValue(self.canvas.TopProperty, y - 10.0)
            self.canvas.Children.Add(txt)
            Panel.SetZIndex(txt, 6)

    def _on_segment_click(self, sender, args):
        try:
            idx = int(sender.Tag)
            self.selected_index = idx
            self._update_selection_visual()
            self._update_info_text()
            if self.on_selection_changed:
                self.on_selection_changed(self.get_selected_info())
            args.Handled = True
        except:
            pass

    def _update_selection_visual(self):
        for i, hit in enumerate(self.hit_rects):
            if i == self.selected_index:
                hit.Stroke = Brushes.Blue
                hit.StrokeThickness = 2.2
            else:
                hit.Stroke = Brushes.Transparent
                hit.StrokeThickness = 0.0

    def _update_info_text(self):
        if self.info_text is None:
            return

        info = self.get_selected_info()
        if info is None:
            self.info_text.Text = u"Chưa chọn đoạn cột"
            return

        self.info_text.Text = u"Đoạn đang chọn: {0} | BxH: {1:.0f}x{2:.0f} | Base: {3} | Top: {4}".format(
            info["mark"],
            info["width_mm"],
            info["depth_mm"],
            info["base_level"],
            info["top_level"]
        )