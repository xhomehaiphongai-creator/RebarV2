# -*- coding: utf-8 -*-

from pyrevit import revit
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInParameter
from Autodesk.Revit.DB.Structure import RebarBarType

doc = revit.doc


def safe_string(value):
    try:
        if value is None:
            return u""
        return unicode(value)
    except:
        try:
            return str(value)
        except:
            return u""


def get_bar_type_name(bar_type):
    try:
        p = bar_type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if p and p.HasValue:
            s = p.AsString()
            if s:
                return safe_string(s)
    except:
        pass

    try:
        return safe_string(bar_type.Name)
    except:
        return u""


def get_rebar_types_start_with_d():
    items = []
    seen = set()

    try:
        bar_types = list(FilteredElementCollector(doc).OfClass(RebarBarType).ToElements())
    except:
        bar_types = []

    for bt in bar_types:
        name = get_bar_type_name(bt)
        if not name:
            continue

        check_name = name.strip()
        if not check_name:
            continue

        if not check_name.upper().startswith("D"):
            continue

        if check_name in seen:
            continue

        seen.add(check_name)
        items.append({
            "name": check_name,
            "element": bt
        })

    items.sort(key=lambda x: x["name"])
    return items


def get_bar_type_names_start_with_d():
    return [x["name"] for x in get_rebar_types_start_with_d()]