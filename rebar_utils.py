# -*- coding: utf-8 -*-

from pyrevit import revit
from Autodesk.Revit.DB import (
    BuiltInParameter,
    ElementId,
    FilteredElementCollector
)
from Autodesk.Revit.DB.Structure import RebarBarType, RebarCoverType

from geom_utils import mm_to_ft
from config import BAR_DIAMETER_MM, DEFAULT_COVER_MM

doc = revit.doc


def get_cover_distance(elem):
    param_ids = [
        BuiltInParameter.CLEAR_COVER_OTHER,
        BuiltInParameter.CLEAR_COVER_EXTERIOR,
        BuiltInParameter.CLEAR_COVER_INTERIOR
    ]

    for bip in param_ids:
        try:
            p = elem.get_Parameter(bip)
            if p and p.HasValue:
                eid = p.AsElementId()
                if eid and eid != ElementId.InvalidElementId:
                    ct = doc.GetElement(eid)
                    if isinstance(ct, RebarCoverType):
                        dist = ct.CoverDistance
                        if dist > 0:
                            return dist
        except:
            pass

    return mm_to_ft(DEFAULT_COVER_MM)


def get_all_bar_types():
    return list(FilteredElementCollector(doc).OfClass(RebarBarType).ToElements())


def get_bar_diameter_safe(bar_type):
    # Cach 1
    try:
        d = bar_type.BarDiameter
        if d and d > 0:
            return d
    except:
        pass

    # Cach 2
    try:
        p = bar_type.get_Parameter(BuiltInParameter.REBAR_BAR_DIAMETER)
        if p and p.HasValue:
            d = p.AsDouble()
            if d and d > 0:
                return d
    except:
        pass

    # Cach 3
    try:
        p = bar_type.LookupParameter("Bar Diameter")
        if p and p.HasValue:
            d = p.AsDouble()
            if d and d > 0:
                return d
    except:
        pass

    # Cach 4
    try:
        p = bar_type.LookupParameter("Diameter")
        if p and p.HasValue:
            d = p.AsDouble()
            if d and d > 0:
                return d
    except:
        pass

    return None


def get_best_bar_type(target_mm=None):
    if target_mm is None:
        target_mm = BAR_DIAMETER_MM

    target_ft = mm_to_ft(target_mm)
    types = get_all_bar_types()
    if not types:
        return None

    best = None
    best_diff = None

    for t in types:
        d = get_bar_diameter_safe(t)
        if d is None:
            continue

        diff = abs(d - target_ft)
        if best is None or diff < best_diff:
            best = t
            best_diff = diff

    # Neu khong doc duoc duong kinh tren tat ca type, lay type dau tien
    if best is None and types:
        return types[0]

    return best


def get_bar_type_name(bar_type):
    try:
        p = bar_type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if p and p.HasValue:
            return p.AsString()
    except:
        pass

    try:
        return bar_type.Name
    except:
        return "Unknown"