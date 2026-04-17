# -*- coding: utf-8 -*-

import os
import sys

THIS_DIR = os.path.dirname(__file__)
if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

import clr
clr.AddReference("RevitAPI")

import Autodesk.Revit.DB as DB
import Autodesk.Revit.DB.Structure as DBS

from pyrevit import revit

from rb_common import mm_to_ft, normalize_or_none, fmt_mm
from rb_geom import get_transform_of_column, get_local_extents_of_column
from rb_types import get_rebar_bar_diameter_ft, set_double_param_if_exists

doc = revit.doc


def get_face_dir(face_name, basis_x, basis_y):
    if face_name == "LEFT":
        return basis_x.Negate()
    if face_name == "RIGHT":
        return basis_x
    if face_name == "BOTTOM":
        return basis_y.Negate()
    return basis_y


def get_m17a_compensated_local_point(px_ft, py_ft, face_name, bar_radius_ft):
    r = bar_radius_ft

    if face_name == "LEFT":
        return px_ft + r, py_ft - r

    if face_name == "RIGHT":
        return px_ft - r, py_ft + r

    if face_name == "TOP":
        return px_ft - (2.0 * r), py_ft

    if face_name == "BOTTOM":
        return px_ft, py_ft + (2.0 * r)

    return px_ft, py_ft


def create_main_rebars_m17a(col, bar_type, rebar_shape, point_items, system_length_ft, lb_ft, debug_lines=None):
    if debug_lines is None:
        debug_lines = []

    host_data = DBS.RebarHostData.GetRebarHostData(col)
    if host_data is None:
        raise Exception("Element duoc chon khong ho tro host rebar.")

    try:
        if not host_data.IsValidHost():
            raise Exception("Cot hien tai chua la valid rebar host.")
    except:
        pass

    t = get_transform_of_column(col)

    basis_x = normalize_or_none(t.BasisX)
    basis_y = normalize_or_none(t.BasisY)
    basis_z = normalize_or_none(t.BasisZ)

    if basis_x is None:
        basis_x = DB.XYZ.BasisX
    if basis_y is None:
        basis_y = DB.XYZ.BasisY
    if basis_z is None:
        basis_z = DB.XYZ.BasisZ

    ext = get_local_extents_of_column(col, t)
    minz = ext["minz"]

    bar_dia_ft = get_rebar_bar_diameter_ft(bar_type)
    bar_radius_ft = bar_dia_ft * 0.5

    created = []

    tx = DB.Transaction(doc, "CUR - Create Main Rebar M_17A")
    tx.Start()
    try:
        for item in point_items:
            px_mm = item["x"]
            py_mm = item["y"]
            face_name = item["face"]

            px_ft = mm_to_ft(px_mm)
            py_ft = mm_to_ft(py_mm)

            ins_x_ft, ins_y_ft = get_m17a_compensated_local_point(
                px_ft, py_ft, face_name, bar_radius_ft
            )

            local_origin = DB.XYZ(ins_x_ft, ins_y_ft, minz)
            world_origin = t.OfPoint(local_origin)

            x_dir = normalize_or_none(get_face_dir(face_name, basis_x, basis_y))
            y_dir = basis_z

            if x_dir is None:
                raise Exception("Khong xac dinh duoc huong rebar.")

            rb = DBS.Rebar.CreateFromRebarShape(
                doc,
                rebar_shape,
                bar_type,
                col,
                world_origin,
                x_dir,
                y_dir
            )

            if rb is None:
                raise Exception("Tao rebar that bai.")

            set_double_param_if_exists(rb, ["B"], system_length_ft)
            set_double_param_if_exists(rb, ["C"], lb_ft)

            created.append(rb)

            debug_lines.append(
                "  create face={} | expected=({}, {})".format(
                    face_name, fmt_mm(px_mm), fmt_mm(py_mm)
                )
            )

        tx.Commit()
    except:
        tx.RollBack()
        raise

    return created