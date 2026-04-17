# -*- coding: utf-8 -*-

import os
import sys

THIS_DIR = os.path.dirname(__file__)
if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)


def evenly_spaced_values(v0, v1, count):
    if count <= 1:
        return [(v0 + v1) * 0.5]

    if abs(v1 - v0) < 1e-9:
        return [v0 for _ in range(count)]

    vals = []
    for i in range(count):
        t = float(i) / float(count - 1)
        vals.append(v0 + (v1 - v0) * t)
    return vals


def add_or_keep_point_with_face(out_list, x, y, face, tol_mm=0.5):
    for item in out_list:
        if abs(item["x"] - x) <= tol_mm and abs(item["y"] - y) <= tol_mm:
            return
    out_list.append({"x": x, "y": y, "face": face})


def build_boundary_points_with_faces(min_x_mm, max_x_mm, min_y_mm, max_y_mm, inset_mm, count_x, count_y):
    dst_min_x = min_x_mm + inset_mm
    dst_max_x = max_x_mm - inset_mm
    dst_min_y = min_y_mm + inset_mm
    dst_max_y = max_y_mm - inset_mm

    if dst_min_x > dst_max_x:
        midx = (min_x_mm + max_x_mm) * 0.5
        dst_min_x = midx
        dst_max_x = midx

    if dst_min_y > dst_max_y:
        midy = (min_y_mm + max_y_mm) * 0.5
        dst_min_y = midy
        dst_max_y = midy

    x_vals = evenly_spaced_values(dst_min_x, dst_max_x, max(2, int(count_x)))
    y_vals = evenly_spaced_values(dst_min_y, dst_max_y, max(2, int(count_y)))

    items = []

    row_first = (int(count_x) >= int(count_y))

    if row_first:
        for x in x_vals:
            add_or_keep_point_with_face(items, x, dst_min_y, "BOTTOM")
            add_or_keep_point_with_face(items, x, dst_max_y, "TOP")

        for y in y_vals:
            add_or_keep_point_with_face(items, dst_min_x, y, "LEFT")
            add_or_keep_point_with_face(items, dst_max_x, y, "RIGHT")
    else:
        for y in y_vals:
            add_or_keep_point_with_face(items, dst_min_x, y, "LEFT")
            add_or_keep_point_with_face(items, dst_max_x, y, "RIGHT")

        for x in x_vals:
            add_or_keep_point_with_face(items, x, dst_min_y, "BOTTOM")
            add_or_keep_point_with_face(items, x, dst_max_y, "TOP")

    return items