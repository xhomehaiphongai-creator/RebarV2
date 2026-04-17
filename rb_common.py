# -*- coding: utf-8 -*-

import os
import sys

THIS_DIR = os.path.dirname(__file__)
if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

import clr
clr.AddReference("RevitAPI")
clr.AddReference("System")

from System import Int64
import Autodesk.Revit.DB as DB


def mm_to_ft(mm):
    try:
        return DB.UnitUtils.ConvertToInternalUnits(float(mm), DB.UnitTypeId.Millimeters)
    except:
        return float(mm) / 304.8


def ft_to_mm(ft):
    try:
        return DB.UnitUtils.ConvertFromInternalUnits(float(ft), DB.UnitTypeId.Millimeters)
    except:
        return float(ft) * 304.8


def safe_str(v):
    try:
        if v is None:
            return ""
        return str(v).strip()
    except:
        return ""


def parse_float(v, default_value):
    try:
        return float(str(v).replace(",", "."))
    except:
        return float(default_value)


def parse_int(v, default_value):
    try:
        return int(round(parse_float(v, default_value)))
    except:
        return int(default_value)


def make_element_id(v):
    return DB.ElementId(Int64(int(v)))


def normalize_or_none(v):
    try:
        if v is None:
            return None
        if v.GetLength() < 1e-9:
            return None
        return v.Normalize()
    except:
        return None


def fmt_mm(v):
    try:
        return "{0:.3f}".format(float(v))
    except:
        return safe_str(v)