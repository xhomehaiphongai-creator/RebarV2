# -*- coding: utf-8 -*-

import os

from pyrevit import forms

from selection_utils import pick_columns
import column_model
from ui_window import MainWindow
from run_rebar_tasks import run_all_rebar_tasks


def show_main_dialog(column_infos):
    this_dir = os.path.dirname(os.path.dirname(__file__))
    xaml_path = os.path.join(this_dir, "ui.xaml")

    if not os.path.exists(xaml_path):
        forms.alert(u"Khong tim thay file ui.xaml", exitscript=True)
        return

    win = MainWindow(xaml_path, column_infos)
    win.ui.ShowDialog()

    if getattr(win, "run_after_close", False):
        try:
            run_all_rebar_tasks()
        except Exception as ex:
            forms.alert(
                u"Loi khi chay cac code trong rebarrun:\n{}".format(unicode(ex)),
                title=u"THÉP CỘT CUR"
            )


def run_tool():
    try:
        cols = pick_columns()
    except Exception as ex:
        forms.alert(unicode(ex), title=u"THÉP CỘT CUR", exitscript=True)
        return

    infos = column_model.sort_column_infos(cols)
    show_main_dialog(infos)