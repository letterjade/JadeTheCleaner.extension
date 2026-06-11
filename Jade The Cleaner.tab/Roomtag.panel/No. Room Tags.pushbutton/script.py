# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms

doc = revit.doc
view = doc.ActiveView

room_tags = DB.FilteredElementCollector(doc, view.Id) \
    .OfCategory(DB.BuiltInCategory.OST_RoomTags) \
    .WhereElementIsNotElementType() \
    .ToElements()

forms.alert(
    "Active View: {}\nRoom Tags Found: {}".format(view.Name, len(room_tags)),
    title="Room Tag Test"
)