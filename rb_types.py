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
from rb_common import safe_str

doc = revit.doc


def get_param_str(elem, bip=None, pname=None):
    try:
        p = None
        if bip is not None:
            p = elem.get_Parameter(bip)
        elif pname:
            p = elem.LookupParameter(pname)

        if p is None:
            return ""

        try:
            s = p.AsString()
            if s:
                return s.strip()
        except:
            pass

        try:
            s = p.AsValueString()
            if s:
                return s.strip()
        except:
            pass
    except:
        pass
    return ""


def get_rebar_shape_labels(rs):
    vals = []

    try:
        vals.append(safe_str(rs.Name))
    except:
        pass

    vals.append(get_param_str(rs, DB.BuiltInParameter.SYMBOL_NAME_PARAM))
    vals.append(get_param_str(rs, DB.BuiltInParameter.ALL_MODEL_TYPE_NAME))
    vals.append(get_param_str(rs, pname="Shape"))
    vals.append(get_param_str(rs, pname="Shape Name"))
    vals.append(get_param_str(rs, pname="Type Name"))

    out = []
    seen = set()
    for v in vals:
        key = safe_str(v).lower()
        if key and key not in seen:
            seen.add(key)
            out.append(v)
    return out


def find_rebar_shape_flexible(target_name):
    target = safe_str(target_name).lower()
    all_shapes = list(DB.FilteredElementCollector(doc).OfClass(DBS.RebarShape))

    for rs in all_shapes:
        labels = get_rebar_shape_labels(rs)
        for lb in labels:
            if safe_str(lb).lower() == target:
                return rs

    for rs in all_shapes:
        labels = get_rebar_shape_labels(rs)
        for lb in labels:
            if target in safe_str(lb).lower():
                return rs

    return None


def find_bar_type_by_name_exact(name):
    target = safe_str(name).upper()
    if not target:
        return None

    bars = list(DB.FilteredElementCollector(doc).OfClass(DBS.RebarBarType))
    for bt in bars:
        try:
            p = bt.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
            if p and safe_str(p.AsString()).upper() == target:
                return bt
        except:
            pass

    for bt in bars:
        try:
            if safe_str(bt.Name).upper() == target:
                return bt
        except:
            pass

    return None


def find_bar_type_by_name_contains(name):
    target = safe_str(name).upper()
    if not target:
        return None

    bars = list(DB.FilteredElementCollector(doc).OfClass(DBS.RebarBarType))
    for bt in bars:
        try:
            p = bt.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
            if p and target in safe_str(p.AsString()).upper():
                return bt
        except:
            pass

    for bt in bars:
        try:
            if target in safe_str(bt.Name).upper():
                return bt
        except:
            pass

    return None


def get_rebar_bar_diameter_ft(bar_type):
    try:
        p = bar_type.get_Parameter(DB.BuiltInParameter.REBAR_BAR_DIAMETER)
        if p and p.StorageType == DB.StorageType.Double:
            d = p.AsDouble()
            if d and d > 0:
                return d
    except:
        pass

    try:
        p = bar_type.get_Parameter(DB.BuiltInParameter.REBAR_MODEL_BAR_DIAMETER)
        if p and p.StorageType == DB.StorageType.Double:
            d = p.AsDouble()
            if d and d > 0:
                return d
    except:
        pass

    raise Exception("Khong doc duoc duong kinh RebarBarType.")


def parse_bar_name_and_diameter_mm(raw_value):
    s = safe_str(raw_value).upper()
    if not s:
        return None, None

    if s.startswith("D"):
        try:
            return s, float(s[1:].strip())
        except:
            return s, None

    digits = []
    for ch in s:
        if ch.isdigit() or ch == ".":
            digits.append(ch)

    if digits:
        try:
            return None, float("".join(digits))
        except:
            pass

    return s, None


def find_bar_type_by_diameter_mm(dia_mm, tol_mm=1.0):
    if dia_mm is None:
        return None

    bars = list(DB.FilteredElementCollector(doc).OfClass(DBS.RebarBarType))
    best = None
    best_diff = None

    for bt in bars:
        try:
            d_ft = get_rebar_bar_diameter_ft(bt)
            d_mm = DB.UnitUtils.ConvertFromInternalUnits(d_ft, DB.UnitTypeId.Millimeters)
        except:
            continue

        diff = abs(d_mm - dia_mm)
        if best is None or diff < best_diff:
            best = bt
            best_diff = diff

    if best is not None and best_diff <= tol_mm:
        return best

    return best


def get_main_bar_type(raw_value, debug_lines=None):
    if debug_lines is None:
        debug_lines = []

    debug_lines.append("BAR SEARCH:")
    debug_lines.append("  raw = {}".format(safe_str(raw_value)))

    bar_name, dia_mm = parse_bar_name_and_diameter_mm(raw_value)
    debug_lines.append("  parsed_name = {}".format(bar_name))
    debug_lines.append("  parsed_dia  = {}".format(dia_mm))

    if bar_name:
        bt = find_bar_type_by_name_exact(bar_name)
        if bt is not None:
            debug_lines.append("  SELECT = exact name match")
            return bt

        bt = find_bar_type_by_name_contains(bar_name)
        if bt is not None:
            debug_lines.append("  SELECT = contains name match")
            return bt

    if dia_mm is not None:
        bt = find_bar_type_by_diameter_mm(dia_mm)
        if bt is not None:
            debug_lines.append("  SELECT = nearest diameter match")
            return bt

    debug_lines.append("  SELECT = NONE")
    return None


def set_double_param_if_exists(elem, param_names, value):
    for n in param_names:
        try:
            p = elem.LookupParameter(n)
            if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                p.Set(value)
                return True
        except:
            pass
    return False