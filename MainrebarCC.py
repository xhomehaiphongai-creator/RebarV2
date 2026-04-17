# -*- coding: utf-8 -*-

import os
import sys
import codecs
import traceback

THIS_DIR = os.path.dirname(__file__)
if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

from pyrevit import forms

from rb_common import ft_to_mm, parse_float, parse_int, fmt_mm
from rb_runio import parse_run_file, get_value_ci
from rb_geom import (
    get_hosts_from_general,
    get_host_id_text,
    get_transform_of_column,
    get_local_extents_of_column,
    get_system_length_ft,
    get_axis_mapping
)
from rb_types import (
    find_rebar_shape_flexible,
    get_main_bar_type,
    get_rebar_bar_diameter_ft
)
from rb_points import build_boundary_points_with_faces
from rb_create_m17a import create_main_rebars_m17a


PUSHBUTTON_DIR = os.path.dirname(THIS_DIR)
LIB_DIR = os.path.join(PUSHBUTTON_DIR, "lib")

RUN_PATH = os.path.join(LIB_DIR, "Run.txt")
DEBUG_PATH = os.path.join(LIB_DIR, "MainrebarCC_debug.txt")

REBAR_SHAPE_NAME = "M_17A"
EXTRA_INSET_MM = 30.0
DEBUG_UI = False


def write_debug(lines):
    try:
        f = codecs.open(DEBUG_PATH, "w", "utf-8")
        try:
            f.write("\r\n".join(lines))
        finally:
            f.close()
    except:
        pass


def show_debug(lines):
    if not DEBUG_UI:
        return
    try:
        forms.alert(u"\n".join(lines), title=u"MAINREBAR DEBUG", warn_icon=False)
    except:
        pass


def get_segment_for_host(host, segments, fallback_index=None):
    host_id = get_host_id_text(host)

    for seg in segments:
        meta = seg.get("meta", {})
        sid = get_value_ci(meta, ["COLUMN_ID"], "")
        if sid and sid == host_id:
            return seg

    if fallback_index is not None and 0 <= fallback_index < len(segments):
        return segments[fallback_index]

    return None


def create_main_rebars_for_host(col, seg_meta, rebar_shape, debug_lines):
    t = get_transform_of_column(col)
    ext = get_local_extents_of_column(col, t)

    main_bar_raw = get_value_ci(seg_meta, ["MAIN_BAR", "main_bar"], "D18")
    bar_type = get_main_bar_type(main_bar_raw, debug_lines)
    if bar_type is None:
        raise Exception("Khong tim thay RebarBarType tu MAIN_BAR = {}".format(main_bar_raw))

    bar_dia_ft = get_rebar_bar_diameter_ft(bar_type)
    bar_dia_mm = ft_to_mm(bar_dia_ft)

    count_b = parse_int(get_value_ci(seg_meta, ["COUNT_B", "CX_COUNT", "cx_count"], 2), 2)
    count_h = parse_int(get_value_ci(seg_meta, ["COUNT_H", "CY_COUNT", "cy_count"], 2), 2)

    if count_b < 2:
        count_b = 2
    if count_h < 2:
        count_h = 2

    width_mm = parse_float(get_value_ci(seg_meta, ["WIDTH_MM"], 0.0), 0.0)
    depth_mm = parse_float(get_value_ci(seg_meta, ["DEPTH_MM"], 0.0), 0.0)

    axis_map = get_axis_mapping(ext, seg_meta, width_mm, depth_mm)

    if axis_map == "DIRECT":
        count_x = count_b
        count_y = count_h
    else:
        count_x = count_h
        count_y = count_b

    lb_mm = parse_float(get_value_ci(seg_meta, ["LB_MM", "Lb_mm", "lb_mm"], 350.0), 350.0)
    lb_ft = lb_mm / 304.8

    system_length_ft = get_system_length_ft(col)

    min_x_mm = ft_to_mm(ext["minx"])
    max_x_mm = ft_to_mm(ext["maxx"])
    min_y_mm = ft_to_mm(ext["miny"])
    max_y_mm = ft_to_mm(ext["maxy"])

    bar_radius_mm = bar_dia_mm * 0.5
    total_inset_mm = bar_radius_mm + EXTRA_INSET_MM

    point_items = build_boundary_points_with_faces(
        min_x_mm, max_x_mm,
        min_y_mm, max_y_mm,
        total_inset_mm,
        count_x,
        count_y
    )

    debug_lines.append("")
    debug_lines.append("HOST:")
    debug_lines.append("  id            = {}".format(get_host_id_text(col)))
    debug_lines.append("  main_bar      = {}".format(main_bar_raw))
    debug_lines.append("  dia_mm        = {}".format(fmt_mm(bar_dia_mm)))
    debug_lines.append("  count_b       = {}".format(count_b))
    debug_lines.append("  count_h       = {}".format(count_h))
    debug_lines.append("  axis_map      = {}".format(axis_map))
    debug_lines.append("  count_x       = {}".format(count_x))
    debug_lines.append("  count_y       = {}".format(count_y))
    debug_lines.append("  lb_mm         = {}".format(fmt_mm(lb_mm)))
    debug_lines.append("  system_len_mm = {}".format(fmt_mm(ft_to_mm(system_length_ft))))
    debug_lines.append("  inset_mm      = {}".format(fmt_mm(total_inset_mm)))

    created = create_main_rebars_m17a(
        col,
        bar_type,
        rebar_shape,
        point_items,
        system_length_ft,
        lb_ft,
        debug_lines
    )

    return created


def main():
    debug = []
    try:
        debug.append("========== MAINREBAR START ==========")

        if not os.path.exists(RUN_PATH):
            raise Exception("Khong tim thay Run.txt: {}".format(RUN_PATH))

        general, segments = parse_run_file(RUN_PATH)
        if not segments:
            raise Exception("Run.txt khong co [SEGMENT].")

        rebar_shape = find_rebar_shape_flexible(REBAR_SHAPE_NAME)
        if rebar_shape is None:
            raise Exception("Khong tim thay RebarShape: {}".format(REBAR_SHAPE_NAME))

        hosts = get_hosts_from_general(general)
        if not hosts:
            raise Exception("Khong doc duoc cot tu COLUMN_IDS.")

        total_created = 0

        for idx, host in enumerate(hosts):
            seg = get_segment_for_host(host, segments, idx)
            if seg is None:
                continue

            created = create_main_rebars_for_host(
                host,
                seg.get("meta", {}),
                rebar_shape,
                debug
            )
            total_created += len(created)

        debug.append("")
        debug.append("TOTAL CREATED = {}".format(total_created))
        debug.append("========== MAINREBAR END ==========")

        write_debug(debug)
        show_debug(debug)
        return total_created

    except Exception as ex:
        debug.append("")
        debug.append("ERROR:")
        debug.append(str(ex))
        debug.append("")
        debug.append(traceback.format_exc())
        write_debug(debug)
        show_debug(debug)
        forms.alert(
            u"Loi khi chay MainrebarCC.py:\n{}".format(unicode(ex)),
            title=u"THÉP CỘT CUR"
        )
        return None


if __name__ == "__main__":
    main()