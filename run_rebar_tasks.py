# -*- coding: utf-8 -*-

import os
import imp


def _pushbutton_dir():
    return os.path.dirname(os.path.dirname(__file__))


def _rebarrun_dir():
    return os.path.join(_pushbutton_dir(), "rebarrun")


def _get_py_files():
    folder = _rebarrun_dir()
    if not os.path.exists(folder):
        raise Exception(u"Khong tim thay thu muc rebarrun")

    files = []
    for name in os.listdir(folder):
        if not name.lower().endswith(".py"):
            continue
        if name.startswith("_"):
            continue
        files.append(name)

    files.sort()
    return files


def _load_module(script_filename, unique_module_name):
    script_path = os.path.join(_rebarrun_dir(), script_filename)
    if not os.path.exists(script_path):
        raise Exception(u"Khong tim thay file: {}".format(script_filename))
    return imp.load_source(unique_module_name, script_path)


def run_script_file(script_filename, unique_module_name):
    mod = _load_module(script_filename, unique_module_name)

    if not hasattr(mod, "main"):
        raise Exception(u"File {} khong co ham main()".format(script_filename))

    return mod.main()


def run_all_rebar_tasks():
    """
    Chay lan luot cac file trong rebarrun.
    Hien tai uu tien MainrebarCC.py neu ton tai.
    """
    folder = _rebarrun_dir()
    if not os.path.exists(folder):
        raise Exception(u"Khong tim thay thu muc rebarrun")

    main_file = "MainrebarCC.py"
    main_path = os.path.join(folder, main_file)

    if os.path.exists(main_path):
        return run_script_file(main_file, "MainrebarCC_runtime")

    files = _get_py_files()
    if not files:
        raise Exception(u"Thu muc rebarrun khong co file .py nao")

    last_result = None
    for i, filename in enumerate(files):
        module_name = "rebarrun_runtime_{}_{}".format(i, os.path.splitext(filename)[0])
        last_result = run_script_file(filename, module_name)

    return last_result