# -*- coding: utf-8 -*-

from pyrevit import revit
from Autodesk.Revit.DB import XYZ, Line, Curve
from Autodesk.Revit.DB.Structure import (
    Rebar,
    RebarStyle,
    RebarHookOrientation
)
from System.Collections.Generic import List

from config import (
    STRAIGHT_TOL_MM,
    MAX_COLUMN_SHIFT_MM,
    CRANK_ZONE_MM,
    MIN_SEG_MM
)
from geom_utils import (
    mm_to_ft,
    sub,
    length_xy,
    normalize_xy,
    dist_xy,
    get_main_solid,
    get_horizontal_face_points,
    get_column_data,
    inward_corners,
    get_column_center_xy_from_rect
)
from rebar_utils import get_cover_distance

doc = revit.doc


def match_points_nearest(lower_pts, upper_pts):
    pairs = []
    used_upper = set()

    for i, lp in enumerate(lower_pts):
        best_j = None
        best_d = None

        for j, up in enumerate(upper_pts):
            if j in used_upper:
                continue
            d = dist_xy(lp, up)
            if best_j is None or d < best_d:
                best_j = j
                best_d = d

        if best_j is None:
            raise Exception("Khong ghep duoc 4 goc.")

        used_upper.add(best_j)
        pairs.append((i, best_j, best_d))

    return pairs


def make_curve_list(points):
    curves = List[Curve]()
    for i in range(len(points) - 1):
        if points[i].DistanceTo(points[i + 1]) > mm_to_ft(MIN_SEG_MM):
            curves.Add(Line.CreateBound(points[i], points[i + 1]))
    return curves


def plane_normal_from_points(points):
    dir_xy = None

    for i in range(len(points) - 1):
        v = sub(points[i + 1], points[i])
        if length_xy(v) > 1e-6:
            dir_xy = normalize_xy(v)
            break

    if dir_xy is None or length_xy(dir_xy) < 1e-9:
        return XYZ.BasisX

    n = XYZ.BasisZ.CrossProduct(dir_xy)
    if n.GetLength() < 1e-9:
        return XYZ.BasisX

    return n.Normalize()


def create_single_rebar(host, bar_type, pts):
    curves = make_curve_list(pts)
    if curves.Count == 0:
        return None

    normal = plane_normal_from_points(pts)

    rb = Rebar.CreateFromCurves(
        doc,
        RebarStyle.Standard,
        bar_type,
        None,
        None,
        host,
        normal,
        curves,
        RebarHookOrientation.Left,
        RebarHookOrientation.Left,
        True,
        True
    )
    return rb


def sort_lower_upper(cols):
    arr = []

    for c in cols:
        solid = get_main_solid(c)
        if solid is None:
            raise Exception("Khong doc duoc hinh hoc cot.")

        _, zbot = get_horizontal_face_points(solid, False)
        _, ztop = get_horizontal_face_points(solid, True)
        zmid = (zbot + ztop) * 0.5

        arr.append((zmid, c))

    arr.sort(key=lambda x: x[0])
    return arr[0][1], arr[1][1]


def build_bar_paths(lower_col, upper_col, bar_type):
    lower_rect_top, lower_z0, lower_z1 = get_column_data(lower_col, True)
    upper_rect_bot, upper_z0, upper_z1 = get_column_data(upper_col, False)

    if upper_z0 < lower_z1 - mm_to_ft(20.0):
        raise Exception("Cot tren va cot duoi khong hop le theo cao do.")

    cover = get_cover_distance(lower_col)

    try:
        bar_r = bar_type.BarDiameter * 0.5
    except:
        bar_r = mm_to_ft(10.0)

    in_offset = cover + bar_r

    lower_bar_pts = inward_corners(lower_rect_top, in_offset)
    upper_bar_pts = inward_corners(upper_rect_bot, in_offset)

    lower_bar_pts = [XYZ(p.X, p.Y, lower_z1) for p in lower_bar_pts]
    upper_bar_pts = [XYZ(p.X, p.Y, upper_z0) for p in upper_bar_pts]

    c1 = get_column_center_xy_from_rect(lower_bar_pts)
    c2 = get_column_center_xy_from_rect(upper_bar_pts)
    center_shift = dist_xy(c1, c2)

    if center_shift > mm_to_ft(MAX_COLUMN_SHIFT_MM):
        raise Exception("Do lech tam 2 cot > 100 mm.")

    pairs = match_points_nearest(lower_bar_pts, upper_bar_pts)

    lower_rect_bot, _, _ = get_column_data(lower_col, False)
    upper_rect_top, _, _ = get_column_data(upper_col, True)

    lower_start_pts = inward_corners(lower_rect_bot, in_offset)
    upper_end_pts = inward_corners(upper_rect_top, in_offset)

    lower_start_pts = [XYZ(p.X, p.Y, lower_z0) for p in lower_start_pts]
    upper_end_pts = [XYZ(p.X, p.Y, upper_z1) for p in upper_end_pts]

    crank_zone = mm_to_ft(CRANK_ZONE_MM)
    paths = []

    for i_low, j_up, dxy in pairs:
        p_start = lower_start_pts[i_low]
        p_low_top = lower_bar_pts[i_low]
        p_up_bot = upper_bar_pts[j_up]
        p_end = upper_end_pts[j_up]

        if dxy <= mm_to_ft(STRAIGHT_TOL_MM):
            pts = [
                p_start,
                XYZ(p_start.X, p_start.Y, p_end.Z)
            ]
            paths.append(("straight", pts))
            continue

        z1 = max(p_start.Z + mm_to_ft(100.0), p_low_top.Z - crank_zone)
        z2 = min(p_end.Z - mm_to_ft(100.0), p_up_bot.Z + crank_zone)

        if z2 <= z1 + mm_to_ft(50.0):
            zmid1 = p_low_top.Z - mm_to_ft(30.0)
            zmid2 = p_up_bot.Z + mm_to_ft(30.0)

            if zmid2 <= zmid1:
                zmid = (p_low_top.Z + p_up_bot.Z) * 0.5
                zmid1 = zmid - mm_to_ft(10.0)
                zmid2 = zmid + mm_to_ft(10.0)

            z1 = zmid1
            z2 = zmid2

        p1 = XYZ(p_start.X, p_start.Y, z1)
        p2 = XYZ(p_up_bot.X, p_up_bot.Y, z2)
        p3 = XYZ(p_up_bot.X, p_up_bot.Y, p_end.Z)

        pts = [p_start, p1, p2, p3]
        paths.append(("crank", pts))

    return paths


def create_rebars(host_col, bar_type, paths):
    created = []

    with revit.Transaction("Create 4 corner rebars between 2 columns"):
        for kind, pts in paths:
            rb = create_single_rebar(host_col, bar_type, pts)
            if rb:
                created.append(rb)

    return created