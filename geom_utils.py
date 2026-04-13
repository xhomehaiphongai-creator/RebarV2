# -*- coding: utf-8 -*-

import math

from Autodesk.Revit.DB import (
    Options,
    Solid,
    GeometryInstance,
    XYZ,
    UnitUtils,
    UnitTypeId
)

from config import POINT_TOL


def mm_to_ft(mm):
    return UnitUtils.ConvertToInternalUnits(mm, UnitTypeId.Millimeters)


def ft_to_mm(ft):
    return UnitUtils.ConvertFromInternalUnits(ft, UnitTypeId.Millimeters)


def add(a, b):
    return XYZ(a.X + b.X, a.Y + b.Y, a.Z + b.Z)


def sub(a, b):
    return XYZ(a.X - b.X, a.Y - b.Y, a.Z - b.Z)


def mul(v, s):
    return XYZ(v.X * s, v.Y * s, v.Z * s)


def dot_xy(a, b):
    return a.X * b.X + a.Y * b.Y


def length_xy(v):
    return math.sqrt(v.X * v.X + v.Y * v.Y)


def dist_xy(a, b):
    dx = a.X - b.X
    dy = a.Y - b.Y
    return math.sqrt(dx * dx + dy * dy)


def normalize_xy(v):
    l = length_xy(v)
    if l < POINT_TOL:
        return XYZ(0, 0, 0)
    return XYZ(v.X / l, v.Y / l, 0)


def point_key_xy(p, tol):
    return (round(p.X / tol), round(p.Y / tol))


def centroid_xy(pts):
    sx = 0.0
    sy = 0.0
    sz = 0.0
    n = float(len(pts))
    for p in pts:
        sx += p.X
        sy += p.Y
        sz += p.Z
    return XYZ(sx / n, sy / n, sz / n)


def sort_clockwise_xy(pts):
    c = centroid_xy(pts)
    return sorted(pts, key=lambda p: math.atan2(p.Y - c.Y, p.X - c.X))


def unique_xy_points(pts, tol):
    seen = {}
    out = []
    for p in pts:
        k = point_key_xy(p, tol)
        if k not in seen:
            seen[k] = True
            out.append(p)
    return out


def farthest_four_points(pts):
    if len(pts) <= 4:
        return pts[:]

    c = centroid_xy(pts)
    arr = sorted(pts, key=lambda p: dist_xy(p, c), reverse=True)

    out = []
    for p in arr:
        ok = True
        for q in out:
            if dist_xy(p, q) < 1e-4:
                ok = False
                break
        if ok:
            out.append(p)
        if len(out) == 4:
            break
    return out


def get_all_solids(elem):
    opts = Options()
    opts.ComputeReferences = False
    opts.IncludeNonVisibleObjects = True

    geo = elem.get_Geometry(opts)
    solids = []

    def walk(gobj):
        if gobj is None:
            return
        for it in gobj:
            if isinstance(it, Solid):
                if it.Volume > 1e-9:
                    solids.append(it)
            elif isinstance(it, GeometryInstance):
                try:
                    inst_geo = it.GetInstanceGeometry()
                    walk(inst_geo)
                except:
                    pass

    walk(geo)
    return solids


def get_main_solid(elem):
    solids = get_all_solids(elem)
    if not solids:
        return None
    solids.sort(key=lambda s: s.Volume, reverse=True)
    return solids[0]


def get_horizontal_face_points(solid, want_top):
    best_face = None
    best_z = None
    best_area = -1.0

    for f in solid.Faces:
        try:
            n = f.FaceNormal
        except:
            continue

        if abs(n.Z) < 0.999:
            continue

        pts = []
        for loop in f.EdgeLoops:
            for edge in loop:
                try:
                    crv = edge.AsCurve()
                    tess = crv.Tessellate()
                    for p in tess:
                        pts.append(p)
                except:
                    pass

        if not pts:
            continue

        zavg = sum([p.Z for p in pts]) / float(len(pts))
        area = f.Area

        if want_top:
            better = (best_z is None) or (zavg > best_z + 1e-6) or (abs(zavg - best_z) <= 1e-6 and area > best_area)
        else:
            better = (best_z is None) or (zavg < best_z - 1e-6) or (abs(zavg - best_z) <= 1e-6 and area > best_area)

        if better:
            best_face = f
            best_z = zavg
            best_area = area

    if best_face is None:
        return None, None

    pts = []
    for loop in best_face.EdgeLoops:
        for edge in loop:
            try:
                crv = edge.AsCurve()
                tess = crv.Tessellate()
                for p in tess:
                    pts.append(p)
            except:
                pass

    pts = unique_xy_points(pts, 1e-5)
    pts = farthest_four_points(pts)
    pts = sort_clockwise_xy(pts)

    if len(pts) != 4:
        return None, None

    return pts, best_z


def get_column_data(col, use_top_face):
    solid = get_main_solid(col)
    if solid is None:
        raise Exception("Khong lay duoc solid cua cot.")

    if use_top_face:
        rect4, top_z = get_horizontal_face_points(solid, True)
        _, bottom_z = get_horizontal_face_points(solid, False)
    else:
        rect4, bottom_z = get_horizontal_face_points(solid, False)
        _, top_z = get_horizontal_face_points(solid, True)

    if rect4 is None or len(rect4) != 4:
        raise Exception("Chi ho tro cot tiet dien chu nhat 4 goc ro rang.")

    return rect4, bottom_z, top_z


def get_rect_axes_from_4pts(rect4):
    pts = sort_clockwise_xy(rect4)
    if len(pts) != 4:
        raise Exception("Khong xac dinh duoc 4 goc tiet dien.")

    p0 = pts[0]
    p1 = pts[1]
    p2 = pts[2]
    p3 = pts[3]

    e01 = sub(p1, p0)
    e12 = sub(p2, p1)

    l01 = length_xy(e01)
    l12 = length_xy(e12)

    if l01 < POINT_TOL or l12 < POINT_TOL:
        raise Exception("Tiet dien cot khong hop le.")

    ux = normalize_xy(e01)
    uy = normalize_xy(e12)

    c = centroid_xy(pts)
    return c, ux, uy


def inward_corners(rect4, offset):
    # Tao 4 diem thep dung theo 4 mep cot,
    # moi mep lui vao trong offset
    if len(rect4) != 4:
        return rect4[:]

    pts = sort_clockwise_xy(rect4)
    c, ux, uy = get_rect_axes_from_4pts(pts)

    us = []
    vs = []
    for p in pts:
        v = sub(p, c)
        us.append(dot_xy(v, ux))
        vs.append(dot_xy(v, uy))

    min_u = min(us)
    max_u = max(us)
    min_v = min(vs)
    max_v = max(vs)

    # Neu cot qua nho thi chan offset lai
    half_u = (max_u - min_u) * 0.5
    half_v = (max_v - min_v) * 0.5

    safe_off_u = min(offset, max(0.0, half_u - mm_to_ft(5.0)))
    safe_off_v = min(offset, max(0.0, half_v - mm_to_ft(5.0)))

    coords = [
        (min_u + safe_off_u, min_v + safe_off_v),
        (max_u - safe_off_u, min_v + safe_off_v),
        (max_u - safe_off_u, max_v - safe_off_v),
        (min_u + safe_off_u, max_v - safe_off_v),
    ]

    out = []
    z = pts[0].Z
    for u, v in coords:
        p = add(add(c, mul(ux, u)), mul(uy, v))
        out.append(XYZ(p.X, p.Y, z))

    return out


def get_column_center_xy_from_rect(rect4):
    c = centroid_xy(rect4)
    return XYZ(c.X, c.Y, 0)