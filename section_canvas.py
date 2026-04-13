# -*- coding: utf-8 -*-

import clr
clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")
clr.AddReference("PresentationCore")

from System.Windows.Shapes import Rectangle, Ellipse, Polyline
from System.Windows.Controls import Panel
from System.Windows.Media import (
    Brushes,
    SolidColorBrush,
    Color,
    PointCollection,
    PenLineJoin,
    PenLineCap
)
from System.Windows import Point


class SectionCanvasController(object):
    EXTRA_TIE_OFFSET_MM = 25.0
    BAR_INSET_MM = 18.0
    BAR_RADIUS_MM = 8.0
    CLICK_TIE_PAD_MM = 6.0

    def __init__(self, canvas, get_selected_info_fn, get_selected_data_fn, on_data_changed_fn=None):
        self.canvas = canvas
        self.get_selected_info = get_selected_info_fn
        self.get_selected_data = get_selected_data_fn
        self.on_data_changed = on_data_changed_fn
        self.selected_bar_ids = []

    def clear_current_ties(self):
        data = self.get_selected_data()
        if data is None:
            return
        data["section_ties"] = []
        self.selected_bar_ids = []
        self.redraw()
        if self.on_data_changed:
            self.on_data_changed()

    def redraw(self):
        if self.canvas is None:
            return

        self.canvas.Children.Clear()

        sel = self.get_selected_info()
        data = self.get_selected_data()
        if sel is None or data is None:
            return

        geom = self._get_section_geometry_px(sel, data)
        if geom is None:
            return

        col_stroke = SolidColorBrush(Color.FromRgb(47, 143, 87))
        col_fill = SolidColorBrush(Color.FromRgb(245, 245, 245))
        tie_brush = SolidColorBrush(Color.FromRgb(0, 64, 128))
        bar_fill = SolidColorBrush(Color.FromRgb(73, 73, 147))
        bar_fill_selected = SolidColorBrush(Color.FromRgb(120, 90, 200))

        self._draw_rect(
            geom["x0"], geom["y0"], geom["rect_w"], geom["rect_h"],
            col_stroke, col_fill, 2.4, 0.0, 1
        )

        self._draw_rect(
            geom["main_tie_x"], geom["main_tie_y"], geom["main_tie_w"], geom["main_tie_h"],
            tie_brush, Brushes.Transparent, 2.0, 10.0, 2
        )

        ties = data.get("section_ties", [])
        for t in ties:
            ids = t.get("bar_ids", [])
            if len(ids) != 2:
                continue

            p1 = self._find_bar_by_id(geom["bar_points"], ids[0])
            p2 = self._find_bar_by_id(geom["bar_points"], ids[1])
            if p1 is None or p2 is None:
                continue

            if t.get("kind", "RECT") == "C":
                self._draw_c_tie(p1, p2, geom, tie_brush)
            else:
                self._draw_closed_tie(p1, p2, geom, tie_brush)

        for p in geom["bar_points"]:
            fill = bar_fill_selected if p["id"] in self.selected_bar_ids else bar_fill
            self._draw_circle(
                p["x"], p["y"], geom["bar_r_px"],
                fill, Brushes.Black, 1.2,
                tag_value=p["id"],
                handler=self._on_bar_click
            )

    def build_export_data(self, sel, data):
        geom = self._get_section_geometry_mm(sel, data)
        if geom is None:
            return None

        out = {
            "segment": {
                "mark": sel.get("mark", u""),
                "base_level": sel.get("base_level", u""),
                "top_level": sel.get("top_level", u""),
                "width_mm": sel.get("width_mm", 0.0),
                "depth_mm": sel.get("depth_mm", 0.0)
            },
            "TC": [],
            "DC": [],
            "DK": []
        }

        for p in geom["bar_points"]:
            out["TC"].append({
                "id": p["id"],
                "x_mm": round(p["x_mm"], 3),
                "y_mm": round(p["y_mm"], 3)
            })

        ties = data.get("section_ties", [])
        for t in ties:
            ids = t.get("bar_ids", [])
            if len(ids) != 2:
                continue

            p1 = self._find_bar_by_id(geom["bar_points"], ids[0])
            p2 = self._find_bar_by_id(geom["bar_points"], ids[1])
            if p1 is None or p2 is None:
                continue

            if t.get("kind", "RECT") == "C":
                pts = self._build_c_tie_points_mm(p1, p2, geom)
                out["DC"].append({
                    "bar_ids": [p1["id"], p2["id"]],
                    "points_mm": pts
                })
            else:
                rect = self._build_closed_tie_rect_mm(p1, p2, geom)
                out["DK"].append({
                    "bar_ids": [p1["id"], p2["id"]],
                    "rect_mm": rect
                })

        return out

    def _on_bar_click(self, sender, args):
        try:
            bar_id = int(sender.Tag)
        except:
            return

        sel = self.get_selected_info()
        data = self.get_selected_data()
        if sel is None or data is None:
            return

        if bar_id in self.selected_bar_ids:
            self.selected_bar_ids.remove(bar_id)
        else:
            if len(self.selected_bar_ids) >= 2:
                self.selected_bar_ids = []
            self.selected_bar_ids.append(bar_id)

        geom = self._get_section_geometry_px(sel, data)
        if geom and len(self.selected_bar_ids) == 2:
            self._add_tie_from_two_selected_bars(data, geom["bar_points"])
            self.selected_bar_ids = []
            if self.on_data_changed:
                self.on_data_changed()

        self.redraw()
        try:
            args.Handled = True
        except:
            pass

    def _add_tie_from_two_selected_bars(self, data, bar_points):
        if len(self.selected_bar_ids) != 2:
            return

        p1 = self._find_bar_by_id(bar_points, self.selected_bar_ids[0])
        p2 = self._find_bar_by_id(bar_points, self.selected_bar_ids[1])
        if p1 is None or p2 is None:
            return
        if p1["id"] == p2["id"]:
            return

        same_x = abs(p1["x"] - p2["x"]) < 1e-6
        same_y = abs(p1["y"] - p2["y"]) < 1e-6

        kind = "RECT"
        if same_x or same_y:
            kind = "C"

        ties = data.get("section_ties", [])

        # tránh tạo trùng
        pair = sorted([p1["id"], p2["id"]])
        for ex in ties:
            ex_ids = ex.get("bar_ids", [])
            if len(ex_ids) == 2 and sorted(ex_ids) == pair and ex.get("kind", "") == kind:
                return

        ties.append({
            "kind": kind,
            "bar_ids": [p1["id"], p2["id"]]
        })
        data["section_ties"] = ties

    def _get_cover_mm(self, data):
        try:
            return float(str(data["top_cover_mm"]).replace(",", "."))
        except:
            return 25.0

    def _get_section_geometry_mm(self, sel, data):
        col_w = max(float(sel["width_mm"]), 1.0)
        col_h = max(float(sel["depth_mm"]), 1.0)

        cover_mm = self._get_cover_mm(data)

        main_tie_x1 = -col_w * 0.5 + cover_mm
        main_tie_x2 =  col_w * 0.5 - cover_mm
        main_tie_y1 = -col_h * 0.5 + cover_mm
        main_tie_y2 =  col_h * 0.5 - cover_mm

        bar_inset = self.BAR_RADIUS_MM + self.BAR_INSET_MM
        field_x1 = main_tie_x1 + bar_inset
        field_x2 = main_tie_x2 - bar_inset
        field_y1 = main_tie_y1 + bar_inset
        field_y2 = main_tie_y2 - bar_inset

        field_w = max(1.0, field_x2 - field_x1)
        field_h = max(1.0, field_y2 - field_y1)

        bar_points = self._build_bar_points_mm(data, field_x1, field_y1, field_w, field_h)

        return {
            "col_w": col_w,
            "col_h": col_h,
            "main_tie_rect": {
                "x1": main_tie_x1, "y1": main_tie_y1,
                "x2": main_tie_x2, "y2": main_tie_y2
            },
            "bar_points": bar_points,
            "center_x": 0.0,
            "center_y": 0.0
        }

    def _build_bar_points_mm(self, data, field_x1, field_y1, field_w, field_h):
        cx_count = max(2, int(data["cx_count"]))
        cy_count = max(2, int(data["cy_count"]))

        xs = []
        ys = []

        if cx_count <= 1:
            xs = [field_x1 + field_w * 0.5]
        else:
            for i in range(cx_count):
                xs.append(field_x1 + (field_w * i / float(cx_count - 1)))

        if cy_count <= 1:
            ys = [field_y1 + field_h * 0.5]
        else:
            for i in range(cy_count):
                ys.append(field_y1 + (field_h * i / float(cy_count - 1)))

        pts = []
        idx = 0

        for ix, x in enumerate(xs):
            pts.append({"id": idx, "x_mm": x, "y_mm": field_y1, "ix": ix, "iy": 0})
            idx += 1
            pts.append({"id": idx, "x_mm": x, "y_mm": field_y1 + field_h, "ix": ix, "iy": cy_count - 1})
            idx += 1

        for iy, y in enumerate(ys):
            pts.append({"id": idx, "x_mm": field_x1, "y_mm": y, "ix": 0, "iy": iy})
            idx += 1
            pts.append({"id": idx, "x_mm": field_x1 + field_w, "y_mm": y, "ix": cx_count - 1, "iy": iy})
            idx += 1

        unique = []
        seen = set()
        for p in pts:
            key = (round(p["x_mm"], 3), round(p["y_mm"], 3))
            if key not in seen:
                seen.add(key)
                unique.append(p)

        for i, p in enumerate(unique):
            p["id"] = i

        return unique

    def _get_section_geometry_px(self, sel, data):
        try:
            cw = self.canvas.ActualWidth
            ch = self.canvas.ActualHeight
        except:
            cw = 320
            ch = 240

        if cw < 50:
            cw = 320
        if ch < 50:
            ch = 240

        geom_mm = self._get_section_geometry_mm(sel, data)

        col_w = geom_mm["col_w"]
        col_h = geom_mm["col_h"]

        pad = 18.0
        draw_w = max(20.0, cw - 2 * pad)
        draw_h = max(20.0, ch - 2 * pad)

        scale_x = draw_w / col_w
        scale_y = draw_h / col_h
        scale = min(scale_x, scale_y)

        rect_w = col_w * scale
        rect_h = col_h * scale

        x0 = (cw - rect_w) * 0.5
        y0 = (ch - rect_h) * 0.5

        def mm_to_px(x_mm, y_mm):
            px = x0 + (x_mm + col_w * 0.5) * scale
            py = y0 + (y_mm + col_h * 0.5) * scale
            return px, py

        main_tie = geom_mm["main_tie_rect"]
        tie_x1, tie_y1 = mm_to_px(main_tie["x1"], main_tie["y1"])
        tie_x2, tie_y2 = mm_to_px(main_tie["x2"], main_tie["y2"])

        bar_points = []
        for p in geom_mm["bar_points"]:
            px, py = mm_to_px(p["x_mm"], p["y_mm"])
            bar_points.append({
                "id": p["id"],
                "x": px,
                "y": py,
                "x_mm": p["x_mm"],
                "y_mm": p["y_mm"],
                "ix": p["ix"],
                "iy": p["iy"]
            })

        bar_r_px = max(6.0, self.BAR_RADIUS_MM * scale * 0.45)

        return {
            "cw": cw,
            "ch": ch,
            "scale": scale,
            "x0": x0,
            "y0": y0,
            "rect_w": rect_w,
            "rect_h": rect_h,
            "main_tie_x": tie_x1,
            "main_tie_y": tie_y1,
            "main_tie_w": tie_x2 - tie_x1,
            "main_tie_h": tie_y2 - tie_y1,
            "bar_r_px": bar_r_px,
            "bar_points": bar_points,
            "center_x": x0 + rect_w * 0.5,
            "center_y": y0 + rect_h * 0.5
        }

    def _find_bar_by_id(self, bar_points, bid):
        for p in bar_points:
            if p["id"] == bid:
                return p
        return None

    def _build_closed_tie_rect_mm(self, p1, p2, geom_mm):
        pad = self.BAR_RADIUS_MM + self.CLICK_TIE_PAD_MM
        x1 = min(p1["x_mm"], p2["x_mm"]) - pad
        y1 = min(p1["y_mm"], p2["y_mm"]) - pad
        x2 = max(p1["x_mm"], p2["x_mm"]) + pad
        y2 = max(p1["y_mm"], p2["y_mm"]) + pad
        return {
            "x1": round(x1, 3),
            "y1": round(y1, 3),
            "x2": round(x2, 3),
            "y2": round(y2, 3)
        }

    def _build_c_tie_points_mm(self, p1, p2, geom_mm):
        same_x = abs(p1["x_mm"] - p2["x_mm"]) < 1e-6
        same_y = abs(p1["y_mm"] - p2["y_mm"]) < 1e-6
        pad = self.BAR_RADIUS_MM + self.CLICK_TIE_PAD_MM

        pts = []

        if same_x:
            x = p1["x_mm"]
            y1 = min(p1["y_mm"], p2["y_mm"]) - pad
            y2 = max(p1["y_mm"], p2["y_mm"]) + pad

            if x <= geom_mm["center_x"]:
                x_open = x + pad
                x_back = x - pad
            else:
                x_open = x - pad
                x_back = x + pad

            pts = [(x_open, y1), (x_back, y1), (x_back, y2), (x_open, y2)]

        elif same_y:
            y = p1["y_mm"]
            x1 = min(p1["x_mm"], p2["x_mm"]) - pad
            x2 = max(p1["x_mm"], p2["x_mm"]) + pad

            if y <= geom_mm["center_y"]:
                y_open = y + pad
                y_back = y - pad
            else:
                y_open = y - pad
                y_back = y + pad

            pts = [(x1, y_open), (x1, y_back), (x2, y_back), (x2, y_open)]

        out = []
        for x, y in pts:
            out.append({"x": round(x, 3), "y": round(y, 3)})
        return out

    def _draw_closed_tie(self, p1, p2, geom, tie_brush):
        pad = geom["bar_r_px"] + 6.0

        x1 = min(p1["x"], p2["x"]) - pad
        y1 = min(p1["y"], p2["y"]) - pad
        x2 = max(p1["x"], p2["x"]) + pad
        y2 = max(p1["y"], p2["y"]) + pad

        self._draw_rect(
            x1, y1, x2 - x1, y2 - y1,
            tie_brush, Brushes.Transparent, 4.0, 0.0, 4
        )

    def _draw_c_tie(self, p1, p2, geom, tie_brush):
        same_x = abs(p1["x"] - p2["x"]) < 1e-6
        same_y = abs(p1["y"] - p2["y"]) < 1e-6

        pad = geom["bar_r_px"] + 6.0

        if same_x:
            x = p1["x"]
            y1 = min(p1["y"], p2["y"]) - pad
            y2 = max(p1["y"], p2["y"]) + pad

            if x <= geom["center_x"]:
                x_open = x + pad
                x_back = x - pad
            else:
                x_open = x - pad
                x_back = x + pad

            pts = [
                (x_open, y1),
                (x_back, y1),
                (x_back, y2),
                (x_open, y2)
            ]
            self._draw_polyline(pts, tie_brush, 4.0)
            return

        if same_y:
            y = p1["y"]
            x1 = min(p1["x"], p2["x"]) - pad
            x2 = max(p1["x"], p2["x"]) + pad

            if y <= geom["center_y"]:
                y_open = y + pad
                y_back = y - pad
            else:
                y_open = y - pad
                y_back = y + pad

            pts = [
                (x1, y_open),
                (x1, y_back),
                (x2, y_back),
                (x2, y_open)
            ]
            self._draw_polyline(pts, tie_brush, 4.0)
            return

    def _draw_rect(self, x, y, w, h, stroke_brush, fill_brush, stroke_thickness, radius=0.0, zindex=1):
        r = Rectangle()
        r.Width = w
        r.Height = h
        r.Stroke = stroke_brush
        r.Fill = fill_brush
        r.StrokeThickness = stroke_thickness
        r.RadiusX = radius
        r.RadiusY = radius
        r.SetValue(self.canvas.LeftProperty, x)
        r.SetValue(self.canvas.TopProperty, y)
        self.canvas.Children.Add(r)
        Panel.SetZIndex(r, zindex)
        return r

    def _draw_circle(self, cx, cy, radius, fill_brush, stroke_brush, stroke_thickness, tag_value=None, handler=None):
        e = Ellipse()
        e.Width = radius * 2.0
        e.Height = radius * 2.0
        e.Fill = fill_brush
        e.Stroke = stroke_brush
        e.StrokeThickness = stroke_thickness
        if tag_value is not None:
            e.Tag = tag_value
        if handler is not None:
            e.MouseLeftButtonDown += handler
        e.SetValue(self.canvas.LeftProperty, cx - radius)
        e.SetValue(self.canvas.TopProperty, cy - radius)
        self.canvas.Children.Add(e)
        Panel.SetZIndex(e, 6)
        return e

    def _draw_polyline(self, point_list, stroke_brush, stroke_thickness):
        pl = Polyline()
        pc = PointCollection()
        for x, y in point_list:
            pc.Add(Point(x, y))
        pl.Points = pc
        pl.Stroke = stroke_brush
        pl.StrokeThickness = stroke_thickness
        pl.Fill = Brushes.Transparent
        pl.StrokeLineJoin = PenLineJoin.Round
        pl.StrokeStartLineCap = PenLineCap.Round
        pl.StrokeEndLineCap = PenLineCap.Round
        self.canvas.Children.Add(pl)
        Panel.SetZIndex(pl, 4)
        return pl