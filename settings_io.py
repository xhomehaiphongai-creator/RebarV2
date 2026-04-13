# -*- coding: utf-8 -*-

import os
import codecs


def _lib_dir():
    return os.path.dirname(__file__)


def get_inf_path():
    return os.path.join(_lib_dir(), "Inf.txt")


def get_run_path():
    return os.path.join(_lib_dir(), "Run.txt")


def load_inf_defaults():
    path = get_inf_path()
    data = {}
    if not os.path.exists(path):
        return data

    try:
        f = codecs.open(path, "r", "utf-8")
        try:
            for line in f:
                s = line.strip()
                if not s or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                data[k.strip()] = v.strip()
        finally:
            f.close()
    except:
        pass
    return data


def save_inf_defaults(data):
    path = get_inf_path()
    keys = [
        "cx_count",
        "cy_count",
        "main_bar",
        "tie_bar",
        "hook_bar",
        "layout",
        "top_cover_mm",

        "fixed_length_L",
        "top_hook_upper",
        "continue_wait_top",
        "auto_partition",
        "splice_length_Ln",
        "splice_from_bottom_L",
        "split_rebar_at_foundation_wait",
        "enable_tie_spacing",
        "tie_spacing_mm",
        "Hm_mm",
        "Lb_mm"
    ]

    lines = []
    for k in keys:
        lines.append(u"{}={}".format(k, data.get(k, u"")))

    f = codecs.open(path, "w", "utf-8")
    try:
        f.write(u"\n".join(lines))
    finally:
        f.close()


def save_run_text(text):
    path = get_run_path()
    f = codecs.open(path, "w", "utf-8")
    try:
        f.write(text)
    finally:
        f.close()