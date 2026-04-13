# -*- coding: utf-8 -*-

import os
import clr

clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")
clr.AddReference("System")
clr.AddReference("System.Core")

from System.Windows.Markup import XamlReader
from System.IO import FileStream, FileMode, FileAccess


def load_xaml(path):
    if not os.path.exists(path):
        return None

    stream = FileStream(path, FileMode.Open, FileAccess.Read)
    try:
        return XamlReader.Load(stream)
    finally:
        stream.Close()


def load_count_combobox(cbo):
    if cbo is None:
        return
    cbo.Items.Clear()
    for i in [2, 3, 4, 5, 6, 7, 8]:
        cbo.Items.Add(str(i))


def load_text_combobox(cbo, values):
    if cbo is None:
        return
    cbo.Items.Clear()
    for v in values:
        cbo.Items.Add(v)


def set_combo_by_text(cbo, text_value):
    if cbo is None or text_value is None:
        return

    for i in range(cbo.Items.Count):
        try:
            if unicode(cbo.Items[i]) == unicode(text_value):
                cbo.SelectedIndex = i
                return
        except:
            pass

    if cbo.Items.Count > 0 and cbo.SelectedIndex < 0:
        cbo.SelectedIndex = 0


def get_selected_text(cbo, default_value):
    try:
        if cbo is None or cbo.SelectedItem is None:
            return default_value
        return unicode(cbo.SelectedItem)
    except:
        return default_value


def get_selected_int(cbo, default_value):
    try:
        if cbo is None or cbo.SelectedItem is None:
            return default_value
        return int(str(cbo.SelectedItem))
    except:
        return default_value


def to_bool(value, default_value):
    try:
        s = unicode(value).strip().lower()
        if s in ["1", "true", "yes", "y"]:
            return True
        if s in ["0", "false", "no", "n", ""]:
            return False
    except:
        pass
    return default_value


def bool_to_text(value):
    return u"1" if value else u"0"


def find_preferred_bar(bar_names, preferred_name, fallback_name=None):
    if not bar_names:
        return u""

    pref_upper = (preferred_name or u"").strip().upper()
    if pref_upper:
        for n in bar_names:
            if unicode(n).strip().upper() == pref_upper:
                return unicode(n)

    fb_upper = (fallback_name or u"").strip().upper()
    if fb_upper:
        for n in bar_names:
            if unicode(n).strip().upper() == fb_upper:
                return unicode(n)

    return unicode(bar_names[0])