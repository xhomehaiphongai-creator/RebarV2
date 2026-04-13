# -*- coding: utf-8 -*-

import os
import codecs

from pyrevit import forms

from data_utils import get_bar_type_names_start_with_d
from preview_canvas import ColumnPreviewController
from section_canvas import SectionCanvasController
from segment_state import SegmentStateStore, make_segment_key
from settings_io import load_inf_defaults, save_inf_defaults, save_run_text
from ui_helpers import (
    load_xaml,
    load_count_combobox,
    load_text_combobox,
    set_combo_by_text,
    get_selected_text,
    get_selected_int,
    to_bool,
    bool_to_text,
    find_preferred_bar
)


UI_DEBUG_PATH = os.path.join(os.path.dirname(__file__), "ui_debug.txt")

RUN_TXT_SPEC = u"""
RUN.TXT SPEC
============

1. [GENERAL]
- COLUMN_IDS
- fixed_length_L
- top_hook_upper
- continue_wait_top
- auto_partition
- splice_length_Ln
- splice_from_bottom_L
- split_rebar_at_foundation_wait
- enable_tie_spacing
- tie_spacing_mm
- Hm_mm
- Lb_mm

2. [SEGMENT] (moi cot 1 block)
- COLUMN_ID
- MARK
- BASE
- TOP
- WIDTH_MM
- DEPTH_MM

- MAIN_BAR
- TIE_BAR
- HOOK_BAR
- LAYOUT
- TOP_COVER_MM

- COUNT_B   = so thep theo phuong B
- COUNT_H   = so thep theo phuong H

- CX_COUNT / CY_COUNT chi de backward-compatible
- KHONG dung TC lam nguon chinh de tao main rebar nua

3. DC / DK
- co the giu lai neu task sau can dung
- nhung main rebar phai doc COUNT_B / COUNT_H
"""


def write_ui_debug(lines):
    try:
        f = codecs.open(UI_DEBUG_PATH, "w", "utf-8")
        try:
            f.write(u"\n".join(lines))
        finally:
            f.close()
    except:
        pass


class SegmentOption(forms.TemplateListItem):
    @property
    def name(self):
        info = self.item
        return u"{0} | BxH {1:.0f}x{2:.0f} | {3} -> {4}".format(
            info["mark"],
            info["width_mm"],
            info["depth_mm"],
            info["base_level"],
            info["top_level"]
        )


class MainWindow(object):
    def __init__(self, xaml_path, column_infos):
        self.column_infos = column_infos or []
        self.state_store = SegmentStateStore()
        self._is_loading_segment = False
        self.saved_defaults = load_inf_defaults()
        self.run_after_close = False

        self.ui = load_xaml(xaml_path)
        if self.ui is None:
            raise Exception("Khong load duoc ui.xaml")

        self._bind_controls()
        self._load_settings_tab()

        self.preview = ColumnPreviewController(
            self.canvas_preview,
            self.txt_selected_segment,
            self._on_preview_selection_changed
        )

        self.section_canvas = SectionCanvasController(
            self.canvas_section,
            self._get_selected_segment,
            self._get_selected_segment_data,
            self._on_section_data_changed
        )

        self._load_data()
        self._hook_events()

        self.canvas_preview.Loaded += self._on_canvas_ready
        self.canvas_preview.SizeChanged += self._on_canvas_ready

        self.canvas_section.Loaded += self._on_section_canvas_ready
        self.canvas_section.SizeChanged += self._on_section_canvas_ready

    # -----------------------------------------------------
    # UI BIND
    # -----------------------------------------------------
    def _bind_controls(self):
        self.main_tab = self.ui.FindName("main_tab")
        self.settings_host = self.ui.FindName("settings_host")

        self.cbo_cx = self.ui.FindName("cbo_cx")
        self.cbo_cy = self.ui.FindName("cbo_cy")
        self.cbo_main_bar = self.ui.FindName("cbo_main_bar")
        self.cbo_tie_bar = self.ui.FindName("cbo_tie_bar")
        self.cbo_hook_bar = self.ui.FindName("cbo_hook_bar")
        self.cbo_layout = self.ui.FindName("cbo_layout")

        self.txt_total_bar = self.ui.FindName("txt_total_bar")
        self.txt_area = self.ui.FindName("txt_area")
        self.txt_ratio = self.ui.FindName("txt_ratio")
        self.txt_top_cover = self.ui.FindName("txt_top_cover")

        self.canvas_preview = self.ui.FindName("canvas_preview")
        self.canvas_section = self.ui.FindName("canvas_section")
        self.txt_selected_segment = self.ui.FindName("txt_selected_segment")

        self.btn_apply_all = self.ui.FindName("btn_apply_all")
        self.btn_clear = self.ui.FindName("btn_clear")
        self.btn_run = self.ui.FindName("btn_run")
        self.btn_close = self.ui.FindName("btn_close")
        self.btn_save = self.ui.FindName("btn_save")

        self.txt_fixed_length_L = None
        self.chk_top_hook_upper = None
        self.chk_continue_wait_top = None
        self.chk_auto_partition = None
        self.txt_splice_length_Ln = None
        self.txt_splice_from_bottom_L = None
        self.chk_split_rebar_at_foundation_wait = None
        self.chk_enable_tie_spacing = None
        self.txt_tie_spacing_mm = None
        self.txt_Hm_mm = None
        self.txt_Lb_mm = None

    def _load_settings_tab(self):
        if self.settings_host is None:
            return

        ui2_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui2.xaml")
        settings_root = load_xaml(ui2_path)
        if settings_root is None:
            return

        self.settings_host.Content = settings_root

        self.txt_fixed_length_L = settings_root.FindName("txt_fixed_length_L")
        self.chk_top_hook_upper = settings_root.FindName("chk_top_hook_upper")
        self.chk_continue_wait_top = settings_root.FindName("chk_continue_wait_top")
        self.chk_auto_partition = settings_root.FindName("chk_auto_partition")
        self.txt_splice_length_Ln = settings_root.FindName("txt_splice_length_Ln")
        self.txt_splice_from_bottom_L = settings_root.FindName("txt_splice_from_bottom_L")
        self.chk_split_rebar_at_foundation_wait = settings_root.FindName("chk_split_rebar_at_foundation_wait")
        self.chk_enable_tie_spacing = settings_root.FindName("chk_enable_tie_spacing")
        self.txt_tie_spacing_mm = settings_root.FindName("txt_tie_spacing_mm")
        self.txt_Hm_mm = settings_root.FindName("txt_Hm_mm")
        self.txt_Lb_mm = settings_root.FindName("txt_Lb_mm")

    # -----------------------------------------------------
    # DATA LOAD
    # -----------------------------------------------------
    def _load_data(self):
        load_count_combobox(self.cbo_cx)
        load_count_combobox(self.cbo_cy)

        bar_names = get_bar_type_names_start_with_d()
        if not bar_names:
            bar_names = [u"D6", u"D8", u"D10", u"D12", u"D14", u"D16", u"D18"]

        load_text_combobox(self.cbo_main_bar, bar_names)
        load_text_combobox(self.cbo_tie_bar, bar_names)
        load_text_combobox(self.cbo_hook_bar, bar_names)
        load_text_combobox(self.cbo_layout, [u"L1, L2, L1", u"L1"])

        if self.btn_apply_all is not None:
            self.btn_apply_all.Content = u"ÁP DỤNG CHO CỘT"
        if self.btn_save is not None:
            self.btn_save.Content = u"SAVE"

        s = self.saved_defaults

        fallback = {
            "cx_count": int(s.get("cx_count", "2") or "2"),
            "cy_count": int(s.get("cy_count", "2") or "2"),
            "main_bar": find_preferred_bar(bar_names, s.get("main_bar", u""), u"D18"),
            "tie_bar": find_preferred_bar(bar_names, s.get("tie_bar", u"D6"), u"D6"),
            "hook_bar": find_preferred_bar(bar_names, s.get("hook_bar", u"D6"), u"D6"),
            "layout": s.get("layout", u"L1, L2, L1") or u"L1, L2, L1",
            "top_cover_mm": s.get("top_cover_mm", u"25") or u"25",
            "section_ties": []
        }

        for info in self.column_infos:
            self.state_store.ensure(info, fallback)

        self._load_general_defaults_to_controls()

        if self.column_infos:
            self._load_segment_to_controls(self.column_infos[0])
        else:
            self._refresh_summary()

    def _load_general_defaults_to_controls(self):
        s = self.saved_defaults

        if self.txt_fixed_length_L is not None:
            self.txt_fixed_length_L.Text = s.get("fixed_length_L", u"300") or u"300"
        if self.chk_top_hook_upper is not None:
            self.chk_top_hook_upper.IsChecked = to_bool(s.get("top_hook_upper", u"1"), True)
        if self.chk_continue_wait_top is not None:
            self.chk_continue_wait_top.IsChecked = to_bool(s.get("continue_wait_top", u"0"), False)
        if self.chk_auto_partition is not None:
            self.chk_auto_partition.IsChecked = to_bool(s.get("auto_partition", u"1"), True)
        if self.txt_splice_length_Ln is not None:
            self.txt_splice_length_Ln.Text = s.get("splice_length_Ln", u"600") or u"600"
        if self.txt_splice_from_bottom_L is not None:
            self.txt_splice_from_bottom_L.Text = s.get("splice_from_bottom_L", u"0") or u"0"
        if self.chk_split_rebar_at_foundation_wait is not None:
            self.chk_split_rebar_at_foundation_wait.IsChecked = to_bool(s.get("split_rebar_at_foundation_wait", u"0"), False)
        if self.chk_enable_tie_spacing is not None:
            self.chk_enable_tie_spacing.IsChecked = to_bool(s.get("enable_tie_spacing", u"0"), False)
        if self.txt_tie_spacing_mm is not None:
            self.txt_tie_spacing_mm.Text = s.get("tie_spacing_mm", u"300") or u"300"
        if self.txt_Hm_mm is not None:
            self.txt_Hm_mm.Text = s.get("Hm_mm", u"350") or u"350"
        if self.txt_Lb_mm is not None:
            self.txt_Lb_mm.Text = s.get("Lb_mm", u"350") or u"350"

    # -----------------------------------------------------
    # EVENTS
    # -----------------------------------------------------
    def _hook_events(self):
        self.cbo_cx.SelectionChanged += self._on_any_setting_changed
        self.cbo_cy.SelectionChanged += self._on_any_setting_changed
        self.cbo_main_bar.SelectionChanged += self._on_any_setting_changed
        self.cbo_tie_bar.SelectionChanged += self._on_any_setting_changed
        self.cbo_hook_bar.SelectionChanged += self._on_any_setting_changed
        self.cbo_layout.SelectionChanged += self._on_any_setting_changed
        self.txt_top_cover.TextChanged += self._on_any_setting_changed

        self.btn_apply_all.Click += self._on_apply_to_columns
        self.btn_clear.Click += self._on_clear_current_ties
        self.btn_run.Click += self._on_run
        self.btn_close.Click += self._on_close

        if self.btn_save is not None:
            self.btn_save.Click += self._on_save_defaults

    def _on_canvas_ready(self, sender, args):
        self.preview.set_data(self.column_infos)
        self._load_segment_to_controls(self.preview.get_selected_info())

    def _on_section_canvas_ready(self, sender, args):
        self.section_canvas.redraw()

    def _on_preview_selection_changed(self, selected_info):
        self._load_segment_to_controls(selected_info)

    def _on_any_setting_changed(self, sender, args):
        self._save_current_segment_settings()

    def _on_section_data_changed(self):
        self._refresh_summary()

    def _on_clear_current_ties(self, sender, args):
        self.section_canvas.clear_current_ties()

    def _on_close(self, sender, args):
        self.run_after_close = False
        self.ui.Close()

    # -----------------------------------------------------
    # CURRENT SEGMENT
    # -----------------------------------------------------
    def _get_selected_segment(self):
        if self.preview is None:
            return None
        return self.preview.get_selected_info()

    def _get_selected_segment_data(self):
        sel = self._get_selected_segment()
        if sel is None:
            return None
        return self.state_store.ensure(sel)

    def _get_current_settings_from_controls(self):
        sel = self._get_selected_segment()
        ties = []
        if sel is not None:
            old_data = self.state_store.ensure(sel)
            ties = [dict(x) for x in old_data.get("section_ties", [])]

        return {
            "cx_count": get_selected_int(self.cbo_cx, 2),
            "cy_count": get_selected_int(self.cbo_cy, 2),
            "main_bar": get_selected_text(self.cbo_main_bar, u""),
            "tie_bar": get_selected_text(self.cbo_tie_bar, u"D6"),
            "hook_bar": get_selected_text(self.cbo_hook_bar, u"D6"),
            "layout": get_selected_text(self.cbo_layout, u"L1, L2, L1"),
            "top_cover_mm": self.txt_top_cover.Text if self.txt_top_cover is not None else u"25",
            "section_ties": ties
        }

    def _save_current_segment_settings(self):
        if self._is_loading_segment:
            return

        sel = self._get_selected_segment()
        if sel is None:
            return

        self.state_store.set(sel, self._get_current_settings_from_controls())
        self._refresh_summary()
        self.section_canvas.redraw()

    def _load_segment_to_controls(self, info):
        if info is None:
            return

        data = self.state_store.ensure(info)

        self._is_loading_segment = True
        try:
            set_combo_by_text(self.cbo_cx, str(data["cx_count"]))
            set_combo_by_text(self.cbo_cy, str(data["cy_count"]))
            set_combo_by_text(self.cbo_main_bar, data["main_bar"])
            set_combo_by_text(self.cbo_tie_bar, data["tie_bar"])
            set_combo_by_text(self.cbo_hook_bar, data["hook_bar"])
            set_combo_by_text(self.cbo_layout, data["layout"])
            if self.txt_top_cover is not None:
                self.txt_top_cover.Text = unicode(data["top_cover_mm"])
        finally:
            self._is_loading_segment = False

        self._refresh_summary()
        self.section_canvas.selected_bar_ids = []
        self.section_canvas.redraw()

    def _refresh_summary(self):
        sel = self._get_selected_segment()
        if sel is None:
            if self.txt_total_bar is not None:
                self.txt_total_bar.Text = u""
            if self.txt_area is not None:
                self.txt_area.Text = u"0.000 (cm²)"
            if self.txt_ratio is not None:
                self.txt_ratio.Text = u"0.000%"
            return

        data = self.state_store.ensure(sel)
        total = 2 * int(data["cx_count"]) + 2 * int(data["cy_count"]) - 4
        if total < 4:
            total = 4

        if self.txt_total_bar is not None:
            self.txt_total_bar.Text = unicode(total) + data["main_bar"]
        if self.txt_area is not None:
            self.txt_area.Text = u"0.000 (cm²)"
        if self.txt_ratio is not None:
            self.txt_ratio.Text = u"0.000%"

    # -----------------------------------------------------
    # SAVE / RUN
    # -----------------------------------------------------
    def _collect_save_payload(self):
        data = self._get_current_settings_from_controls()
        return {
            "cx_count": unicode(data["cx_count"]),
            "cy_count": unicode(data["cy_count"]),
            "main_bar": data["main_bar"],
            "tie_bar": data["tie_bar"],
            "hook_bar": data["hook_bar"],
            "layout": data["layout"],
            "top_cover_mm": data["top_cover_mm"],

            "fixed_length_L": self.txt_fixed_length_L.Text if self.txt_fixed_length_L is not None else u"300",
            "top_hook_upper": bool_to_text(self.chk_top_hook_upper.IsChecked if self.chk_top_hook_upper is not None else True),
            "continue_wait_top": bool_to_text(self.chk_continue_wait_top.IsChecked if self.chk_continue_wait_top is not None else False),
            "auto_partition": bool_to_text(self.chk_auto_partition.IsChecked if self.chk_auto_partition is not None else True),
            "splice_length_Ln": self.txt_splice_length_Ln.Text if self.txt_splice_length_Ln is not None else u"600",
            "splice_from_bottom_L": self.txt_splice_from_bottom_L.Text if self.txt_splice_from_bottom_L is not None else u"0",
            "split_rebar_at_foundation_wait": bool_to_text(self.chk_split_rebar_at_foundation_wait.IsChecked if self.chk_split_rebar_at_foundation_wait is not None else False),
            "enable_tie_spacing": bool_to_text(self.chk_enable_tie_spacing.IsChecked if self.chk_enable_tie_spacing is not None else False),
            "tie_spacing_mm": self.txt_tie_spacing_mm.Text if self.txt_tie_spacing_mm is not None else u"300",
            "Hm_mm": self.txt_Hm_mm.Text if self.txt_Hm_mm is not None else u"350",
            "Lb_mm": self.txt_Lb_mm.Text if self.txt_Lb_mm is not None else u"350"
        }

    def _safe_element_id_text(self, info, debug_lines=None):
        if debug_lines is None:
            debug_lines = []

        debug_lines.append(u"--- COLUMN INFO ---")
        try:
            debug_lines.append(u"keys = {}".format(u", ".join(sorted([unicode(k) for k in info.keys()]))))
        except:
            debug_lines.append(u"keys = <cannot read>")

        try:
            el = info.get("element", None)
            debug_lines.append(u"element exists = {}".format(el is not None))
            if el is not None:
                try:
                    debug_lines.append(u"element class = {}".format(el.GetType().FullName))
                except:
                    pass
                try:
                    debug_lines.append(u"element id str(raw) = {}".format(unicode(el.Id)))
                except:
                    pass
                try:
                    sid = str(el.Id.Value)
                    debug_lines.append(u"element id via Value = {}".format(sid))
                    return sid
                except Exception as ex:
                    debug_lines.append(u"element id via Value ERROR = {}".format(unicode(ex)))
                try:
                    sid = el.Id.ToString()
                    debug_lines.append(u"element id via ToString = {}".format(sid))
                    return sid
                except Exception as ex:
                    debug_lines.append(u"element id via ToString ERROR = {}".format(unicode(ex)))
                try:
                    sid = str(el.Id)
                    debug_lines.append(u"element id via str = {}".format(sid))
                    return sid
                except Exception as ex:
                    debug_lines.append(u"element id via str ERROR = {}".format(unicode(ex)))
        except Exception as ex:
            debug_lines.append(u"read element ERROR = {}".format(unicode(ex)))

        try:
            raw = info.get("id", None)
            debug_lines.append(u"raw id exists = {}".format(raw is not None))
            if raw is not None:
                try:
                    sid = str(raw.Value)
                    debug_lines.append(u"raw id via Value = {}".format(sid))
                    return sid
                except Exception as ex:
                    debug_lines.append(u"raw id via Value ERROR = {}".format(unicode(ex)))
                try:
                    sid = raw.ToString()
                    debug_lines.append(u"raw id via ToString = {}".format(sid))
                    return sid
                except Exception as ex:
                    debug_lines.append(u"raw id via ToString ERROR = {}".format(unicode(ex)))
                try:
                    sid = str(raw)
                    debug_lines.append(u"raw id via str = {}".format(sid))
                    return sid
                except Exception as ex:
                    debug_lines.append(u"raw id via str ERROR = {}".format(unicode(ex)))
        except Exception as ex:
            debug_lines.append(u"read raw id ERROR = {}".format(unicode(ex)))

        debug_lines.append(u"result = None")
        return None

    def _get_selected_column_ids_text(self):
        ids = []
        seen = set()
        dbg = []
        dbg.append(u"Start _get_selected_column_ids_text")
        dbg.append(u"column_infos count = {}".format(len(self.column_infos)))

        for idx, info in enumerate(self.column_infos):
            dbg.append(u"INDEX = {}".format(idx))
            sid = self._safe_element_id_text(info, dbg)

            if not sid:
                dbg.append(u"skip because sid empty")
                continue

            sid = sid.strip()
            dbg.append(u"sid stripped = {}".format(sid))

            if not sid:
                dbg.append(u"skip because sid blank")
                continue

            if sid in seen:
                dbg.append(u"skip because duplicate sid")
                continue

            seen.add(sid)
            ids.append(sid)
            dbg.append(u"accepted sid = {}".format(sid))

        dbg.append(u"FINAL COLUMN_IDS = {}".format(u",".join(ids)))
        write_ui_debug(dbg)

        return u",".join(ids)

    def _on_save_defaults(self, sender, args):
        save_inf_defaults(self._collect_save_payload())

    def _collect_general_run_settings(self):
        general = self._collect_save_payload()
        return {
            "fixed_length_L": general.get("fixed_length_L", u"300"),
            "top_hook_upper": general.get("top_hook_upper", u"1"),
            "continue_wait_top": general.get("continue_wait_top", u"0"),
            "auto_partition": general.get("auto_partition", u"1"),
            "splice_length_Ln": general.get("splice_length_Ln", u"600"),
            "splice_from_bottom_L": general.get("splice_from_bottom_L", u"0"),
            "split_rebar_at_foundation_wait": general.get("split_rebar_at_foundation_wait", u"0"),
            "enable_tie_spacing": general.get("enable_tie_spacing", u"0"),
            "tie_spacing_mm": general.get("tie_spacing_mm", u"300"),
            "Hm_mm": general.get("Hm_mm", u"350"),
            "Lb_mm": general.get("Lb_mm", u"350")
        }

    def _build_segment_run_lines(self, info, general):
        st = self.state_store.ensure(info)
        exported = self.section_canvas.build_export_data(info, st)
        if exported is None:
            return []

        seg = exported["segment"]

        dbg = []
        column_id = self._safe_element_id_text(info, dbg) or u""

        # Quy uoc chot:
        # COUNT_B = so thep theo phuong B
        # COUNT_H = so thep theo phuong H
        count_b = unicode(st.get("cx_count", 2))
        count_h = unicode(st.get("cy_count", 2))

        lines = []
        lines.append(u"[SEGMENT]")
        lines.append(u"COLUMN_ID={}".format(column_id))
        lines.append(u"MARK={}".format(seg.get("mark", u"")))
        lines.append(u"BASE={}".format(seg.get("base_level", u"")))
        lines.append(u"TOP={}".format(seg.get("top_level", u"")))
        lines.append(u"WIDTH_MM={}".format(seg.get("width_mm", u"")))
        lines.append(u"DEPTH_MM={}".format(seg.get("depth_mm", u"")))

        # Per-column UI state
        lines.append(u"MAIN_BAR={}".format(st.get("main_bar", u"")))
        lines.append(u"TIE_BAR={}".format(st.get("tie_bar", u"")))
        lines.append(u"HOOK_BAR={}".format(st.get("hook_bar", u"")))
        lines.append(u"LAYOUT={}".format(st.get("layout", u"")))
        lines.append(u"TOP_COVER_MM={}".format(st.get("top_cover_mm", u"25")))

        # So thep ro nghia theo B / H
        lines.append(u"COUNT_B={}".format(count_b))
        lines.append(u"COUNT_H={}".format(count_h))

        # Backward-compatible
        lines.append(u"CX_COUNT={}".format(unicode(st.get("cx_count", 2))))
        lines.append(u"CY_COUNT={}".format(unicode(st.get("cy_count", 2))))

        # Copy setting chung xuong tung cot de rebarrun doc de hon
        lines.append(u"FIXED_LENGTH_L={}".format(general["fixed_length_L"]))
        lines.append(u"TOP_HOOK_UPPER={}".format(general["top_hook_upper"]))
        lines.append(u"CONTINUE_WAIT_TOP={}".format(general["continue_wait_top"]))
        lines.append(u"AUTO_PARTITION={}".format(general["auto_partition"]))
        lines.append(u"SPLICE_LENGTH_LN={}".format(general["splice_length_Ln"]))
        lines.append(u"SPLICE_FROM_BOTTOM_L={}".format(general["splice_from_bottom_L"]))
        lines.append(u"SPLIT_REBAR_AT_FOUNDATION_WAIT={}".format(general["split_rebar_at_foundation_wait"]))
        lines.append(u"ENABLE_TIE_SPACING={}".format(general["enable_tie_spacing"]))
        lines.append(u"TIE_SPACING_MM={}".format(general["tie_spacing_mm"]))
        lines.append(u"HM_MM={}".format(general["Hm_mm"]))
        lines.append(u"LB_MM={}".format(general["Lb_mm"]))

        # BO TC khoi Run.txt de tranh MainrebarCC suy nguoc sai
        # Giu DC/DK neu can cho task sau
        lines.append(u"DC_COUNT={}".format(len(exported["DC"])))
        for dc in exported["DC"]:
            pt_text = []
            for p in dc["points_mm"]:
                pt_text.append(u"({}, {})".format(p["x"], p["y"]))
            lines.append(
                u"DC;BAR_IDS={};PTS={}".format(
                    ",".join([unicode(x) for x in dc["bar_ids"]]),
                    ";".join(pt_text)
                )
            )

        lines.append(u"DK_COUNT={}".format(len(exported["DK"])))
        for dk in exported["DK"]:
            r = dk["rect_mm"]
            lines.append(
                u"DK;BAR_IDS={};RECT=({}, {}, {}, {})".format(
                    ",".join([unicode(x) for x in dk["bar_ids"]]),
                    r["x1"], r["y1"], r["x2"], r["y2"]
                )
            )

        lines.append(u"")
        return lines

    def _make_run_text(self):
        lines = []
        general = self._collect_general_run_settings()

        # -----------------------------
        # GENERAL
        # -----------------------------
        lines.append(u"[GENERAL]")
        lines.append(u"COLUMN_IDS={}".format(self._get_selected_column_ids_text()))

        for k in [
            "fixed_length_L",
            "top_hook_upper",
            "continue_wait_top",
            "auto_partition",
            "splice_length_Ln",
            "splice_from_bottom_L",
            "split_rebar_at_foundation_wait",
            "enable_tie_spacing",
            "tie_spacing_mm",
            "Hm_mm",
            "Lb_mm"
        ]:
            lines.append(u"{}={}".format(k, general.get(k, u"")))
        lines.append(u"")

        # -----------------------------
        # SEGMENT per column
        # -----------------------------
        for info in self.column_infos:
            seg_lines = self._build_segment_run_lines(info, general)
            lines.extend(seg_lines)

        return u"\n".join(lines)

    def _on_run(self, sender, args):
        try:
            self._save_current_segment_settings()
            save_run_text(self._make_run_text())

            self.run_after_close = True
            self.ui.Close()

        except Exception as ex:
            forms.alert(
                u"Loi khi chuan bi chay rebarrun:\n{}".format(unicode(ex)),
                title=u"THÉP CỘT CUR"
            )

    # -----------------------------------------------------
    # APPLY
    # -----------------------------------------------------
    def _on_apply_to_columns(self, sender, args):
        source = self._get_selected_segment()
        if source is None:
            forms.alert(u"Chưa chọn đoạn cột nguồn.", title=u"THÉP CỘT CUR")
            return

        options = [SegmentOption(x) for x in self.column_infos if make_segment_key(x) != make_segment_key(source)]
        if not options:
            return

        picked = None
        old_topmost = False

        try:
            try:
                old_topmost = self.ui.Topmost
                self.ui.Topmost = False
            except:
                old_topmost = False

            picked = forms.SelectFromList.show(
                options,
                title=u"Chọn các đoạn cột để áp dụng thông số",
                multiselect=True,
                button_name=u"Áp dụng"
            )
        finally:
            try:
                self.ui.Topmost = old_topmost
                self.ui.Activate()
                self.ui.Focus()
            except:
                pass

        if not picked:
            return

        targets = []
        for x in picked:
            try:
                targets.append(x.item)
            except:
                targets.append(x)

        self._save_current_segment_settings()
        self.state_store.clone_from_source_to_targets(source, targets)

        self.preview.redraw()
        self._refresh_summary()
        self.section_canvas.redraw()