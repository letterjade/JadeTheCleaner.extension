# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms

sel = revit.get_selection()
if not sel:
    forms.alert("Nothing selected. Click ONE of the 'test' tags first, then run this.",
                title="What Is This")
else:
    lines = []
    for e in sel:
        lines.append("=== element id {} ===".format(e.Id.IntegerValue))
        try: lines.append("Category: " + e.Category.Name)
        except: lines.append("Category: ?")
        try: lines.append("BuiltInCategory id: " + str(e.Category.Id.IntegerValue))
        except: pass
        try: lines.append("Class: " + e.GetType().Name)
        except: pass
        # what does it tag?
        try:
            ids = list(e.GetTaggedLocalElementIds())
            lines.append("Tags element id(s): " + str([i.IntegerValue for i in ids]))
        except Exception as ex:
            lines.append("GetTaggedLocalElementIds: n/a (" + str(ex) + ")")
        try:
            lines.append("TaggedLocalElementId: " + str(e.TaggedLocalElementId.IntegerValue))
        except: pass
        try: lines.append("TagText: " + str(e.TagText))
        except: pass
        lines.append("")
    forms.alert("\n".join(lines), title="What Is This")