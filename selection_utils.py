# -*- coding: utf-8 -*-

from pyrevit import revit
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from Autodesk.Revit.DB import BuiltInCategory, ElementId, FamilyInstance

doc = revit.doc
uidoc = revit.uidoc


class ColumnFilter(ISelectionFilter):
    def AllowElement(self, e):
        try:
            if e is None:
                return False

            cat = e.Category
            if cat is None:
                return False

            if cat.Id.Equals(ElementId(BuiltInCategory.OST_StructuralColumns)):
                return True

            if isinstance(e, FamilyInstance):
                try:
                    if e.StructuralType.ToString() == "Column":
                        return True
                except:
                    pass

            try:
                cat_name = cat.Name or ""
                if "Column" in cat_name or "Cot" in cat_name:
                    return True
            except:
                pass

            return False
        except:
            return False

    def AllowReference(self, reference, point):
        return False


def pick_columns():
    refs = uidoc.Selection.PickObjects(
        ObjectType.Element,
        ColumnFilter(),
        "Chon cac cot"
    )

    cols = [doc.GetElement(r.ElementId) for r in refs if r is not None]
    if not cols:
        raise Exception("Chua chon cot nao.")
    return cols