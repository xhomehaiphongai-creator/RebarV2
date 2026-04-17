# -*- coding: utf-8 -*-

import os
import sys

THIS_DIR = os.path.dirname(__file__)
if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

import clr
clr.AddReference("RevitAPI")

import Autodesk.Revit.DB as DB

from pyrevit import revit
from rb_common import make_element_id, ft_to_mm, safe_str

doc = revit.doc


def get_bbox(el):
    bb = el.get_BoundingBox(None)
    if bb is None:
        try:
            bb = el.get_BoundingBox(doc.ActiveView)
        except:
            bb = None
    return bb


def get_hosts_from_general(general):
    hosts = []
    raw_ids = general.get("COLUMN_IDS", "")
    seen = set()

    for s in safe_str(raw_ids).split(","):
        sid = s.strip()
        if not sid:
            continue

        try:
            eid_int = int(sid)
        except:
            continue

        if eid_int in seen:
            continue
        seen.add(eid_int)

        try:
            e = doc.GetElement(make_element_id(eid_int))
            if e is not None:
                hosts.append(e)
        except:
            pass

    return hosts


def get_host_id_text(host):
    try:
        return str(host.Id.Value)
    except:
        try:
            return str(host.Id.IntegerValue)
        except:
            return str(host.Id)


def get_transform_of_column(col):
    try:
        t = col.GetTransform()
        if t:
            return t
    except:
        pass

    try:
        loc = col.Location
        if isinstance(loc, DB.LocationPoint):
            rot = loc.Rotation
            pt = loc.Point
            return DB.Transform.CreateRotationAtPoint(DB.XYZ.BasisZ, rot, pt)
    except:
        pass

    return DB.Transform.Identity


def _update_minmax(p, data):
    if p.X < data["minx"]:
        data["minx"] = p.X
    if p.Y < data["miny"]:
        data["miny"] = p.Y
    if p.Z < data["minz"]:
        data["minz"] = p.Z
    if p.X > data["maxx"]:
        data["maxx"] = p.X
    if p.Y > data["maxy"]:
        data["maxy"] = p.Y
    if p.Z > data["maxz"]:
        data["maxz"] = p.Z


def _scan_geom_local_extents(geom_elem, inv_t, data):
    for g in geom_elem:
        solid = g if isinstance(g, DB.Solid) else None

        if solid and solid.Volume > 1e-9:
            try:
                for edge in solid.Edges:
                    pts = edge.Tessellate()
                    for p in pts:
                        lp = inv_t.OfPoint(p)
                        _update_minmax(lp, data)
            except:
                pass

        elif isinstance(g, DB.GeometryInstance):
            try:
                inst_geom = g.GetInstanceGeometry()
                _scan_geom_local_extents(inst_geom, inv_t, data)
            except:
                pass


def get_local_extents_of_column(col, t):
    inv_t = t.Inverse

    data = {
        "minx": 1e100, "miny": 1e100, "minz": 1e100,
        "maxx": -1e100, "maxy": -1e100, "maxz": -1e100
    }

    opt = DB.Options()
    opt.ComputeReferences = False
    opt.IncludeNonVisibleObjects = True
    opt.DetailLevel = DB.ViewDetailLevel.Fine

    geom = col.get_Geometry(opt)
    if geom:
        _scan_geom_local_extents(geom, inv_t, data)

    if data["minx"] > data["maxx"]:
        bb = col.get_BoundingBox(None)
        if bb is None:
            raise Exception("Khong doc duoc bounding box cua cot.")

        corners = [
            DB.XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z),
            DB.XYZ(bb.Min.X, bb.Min.Y, bb.Max.Z),
            DB.XYZ(bb.Min.X, bb.Max.Y, bb.Min.Z),
            DB.XYZ(bb.Min.X, bb.Max.Y, bb.Max.Z),
            DB.XYZ(bb.Max.X, bb.Min.Y, bb.Min.Z),
            DB.XYZ(bb.Max.X, bb.Min.Y, bb.Max.Z),
            DB.XYZ(bb.Max.X, bb.Max.Y, bb.Min.Z),
            DB.XYZ(bb.Max.X, bb.Max.Y, bb.Max.Z),
        ]

        for p in corners:
            lp = inv_t.OfPoint(p)
            _update_minmax(lp, data)

    return data


def get_system_length_ft(col):
    try:
        p = col.LookupParameter("System Length")
        if p and p.StorageType == DB.StorageType.Double:
            val = p.AsDouble()
            if val and val > 0:
                return val
    except:
        pass

    for bip in [
        DB.BuiltInParameter.CURVE_ELEM_LENGTH,
        DB.BuiltInParameter.INSTANCE_LENGTH_PARAM
    ]:
        try:
            p = col.get_Parameter(bip)
            if p and p.StorageType == DB.StorageType.Double:
                val = p.AsDouble()
                if val and val > 0:
                    return val
        except:
            pass

    bb = get_bbox(col)
    if bb is not None:
        h = bb.Max.Z - bb.Min.Z
        if h > 0:
            return h

    raise Exception("Khong doc duoc System Length cua cot.")


def get_axis_mapping(extents, seg_meta, width_mm, depth_mm):
    len_x_mm = ft_to_mm(extents["maxx"] - extents["minx"])
    len_y_mm = ft_to_mm(extents["maxy"] - extents["miny"])

    direct = abs(len_x_mm - width_mm) + abs(len_y_mm - depth_mm)
    swapped = abs(len_x_mm - depth_mm) + abs(len_y_mm - width_mm)

    if swapped + 1e-6 < direct:
        return "SWAP"
    return "DIRECT"