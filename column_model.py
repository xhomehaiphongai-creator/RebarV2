# -*- coding: utf-8 -*-

from pyrevit import revit
from Autodesk.Revit.DB import (
    BuiltInParameter,
    Options,
    Solid,
    GeometryInstance
)

doc = revit.doc


def _get_param(elem, bip):
    try:
        return elem.get_Parameter(bip)
    except:
        return None


def _safe_unicode(value):
    try:
        if value is None:
            return u""
        return unicode(value)
    except:
        try:
            return str(value)
        except:
            return u""


def _ft_to_mm(val_ft):
    try:
        return val_ft * 304.8
    except:
        return 0.0


def _get_level_name_from_param(elem, bip):
    try:
        p = _get_param(elem, bip)
        if p and p.HasValue:
            eid = p.AsElementId()
            if eid:
                lv = doc.GetElement(eid)
                if lv:
                    return _safe_unicode(lv.Name)
    except:
        pass
    return u""


def _get_offset_mm(elem, bip):
    try:
        p = _get_param(elem, bip)
        if p and p.HasValue:
            return _ft_to_mm(p.AsDouble())
    except:
        pass
    return 0.0


def _get_mark(elem):
    try:
        p = elem.LookupParameter("Mark")
        if p and p.HasValue:
            s = p.AsString()
            if s:
                return _safe_unicode(s)
    except:
        pass
    return u"<not set>"


def _get_bbox(elem):
    try:
        return elem.get_BoundingBox(None)
    except:
        return None


def _get_bbox_data(elem):
    bb = _get_bbox(elem)
    if bb is None:
        return {
            "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
            "max_x": 0.0, "max_y": 0.0, "max_z": 0.0,
            "cx": 0.0, "cy": 0.0, "cz": 0.0,
            "sx": 0.0, "sy": 0.0, "sz": 0.0
        }

    min_x = bb.Min.X
    min_y = bb.Min.Y
    min_z = bb.Min.Z
    max_x = bb.Max.X
    max_y = bb.Max.Y
    max_z = bb.Max.Z

    return {
        "min_x": min_x,
        "min_y": min_y,
        "min_z": min_z,
        "max_x": max_x,
        "max_y": max_y,
        "max_z": max_z,
        "cx": (min_x + max_x) * 0.5,
        "cy": (min_y + max_y) * 0.5,
        "cz": (min_z + max_z) * 0.5,
        "sx": abs(max_x - min_x),
        "sy": abs(max_y - min_y),
        "sz": abs(max_z - min_z)
    }


def _get_all_solids(elem):
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
                    walk(it.GetInstanceGeometry())
                except:
                    pass

    walk(geo)
    return solids


def _get_main_solid(elem):
    solids = _get_all_solids(elem)
    if not solids:
        return None
    solids.sort(key=lambda s: s.Volume, reverse=True)
    return solids[0]


def _get_section_size_mm(elem):
    solid = _get_main_solid(elem)
    if solid is None:
        bb = _get_bbox_data(elem)
        return _ft_to_mm(bb["sx"]), _ft_to_mm(bb["sy"])

    try:
        bb = solid.GetBoundingBox()
        t = bb.Transform
        mn = bb.Min
        mx = bb.Max

        p0 = t.OfPoint(mn)
        p1 = t.OfPoint(mx)

        sx = abs(p1.X - p0.X)
        sy = abs(p1.Y - p0.Y)

        if sx <= 0 or sy <= 0:
            bb2 = _get_bbox_data(elem)
            return _ft_to_mm(bb2["sx"]), _ft_to_mm(bb2["sy"])

        return _ft_to_mm(sx), _ft_to_mm(sy)
    except:
        bb2 = _get_bbox_data(elem)
        return _ft_to_mm(bb2["sx"]), _ft_to_mm(bb2["sy"])


def get_column_info(col):
    width_mm, depth_mm = _get_section_size_mm(col)
    bb = _get_bbox_data(col)

    base_level = _get_level_name_from_param(col, BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)
    top_level = _get_level_name_from_param(col, BuiltInParameter.FAMILY_TOP_LEVEL_PARAM)

    base_offset_mm = _get_offset_mm(col, BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM)
    top_offset_mm = _get_offset_mm(col, BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM)

    mark = _get_mark(col)

    return {
        "element": col,
        "id": col.Id,
        "name": _safe_unicode(col.Name) if hasattr(col, "Name") else u"",
        "mark": mark,
        "width_mm": round(width_mm, 1),
        "depth_mm": round(depth_mm, 1),
        "height_mm": round(_ft_to_mm(bb["sz"]), 1),
        "base_level": base_level,
        "top_level": top_level,
        "base_offset_mm": round(base_offset_mm, 1),
        "top_offset_mm": round(top_offset_mm, 1),

        "z_mid": bb["cz"],
        "z_min_ft": bb["min_z"],
        "z_max_ft": bb["max_z"],

        "center_x_ft": bb["cx"],
        "center_y_ft": bb["cy"],

        "min_x_ft": bb["min_x"],
        "max_x_ft": bb["max_x"],
        "min_y_ft": bb["min_y"],
        "max_y_ft": bb["max_y"]
    }


def sort_column_infos(cols):
    infos = [get_column_info(c) for c in cols]
    infos.sort(key=lambda x: (x["z_min_ft"], x["z_max_ft"], x["center_x_ft"], x["center_y_ft"]))
    return infos