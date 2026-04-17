# -*- coding: utf-8 -*-

import os
import sys
import codecs

THIS_DIR = os.path.dirname(__file__)
if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

from rb_common import safe_str


def read_utf8_lines(path):
    if not os.path.exists(path):
        return []

    f = codecs.open(path, "r", "utf-8")
    try:
        return [x.rstrip("\r\n") for x in f.readlines()]
    finally:
        f.close()


def parse_run_file(path):
    lines = read_utf8_lines(path)

    general = {}
    segments = []

    current_section = None
    current_seg = None

    for raw in lines:
        s = raw.strip()
        if not s:
            continue

        if s == "[GENERAL]":
            current_section = "GENERAL"
            current_seg = None
            continue

        if s == "[SEGMENT]":
            current_section = "SEGMENT"
            current_seg = {
                "meta": {},
                "DC": [],
                "DK": []
            }
            segments.append(current_seg)
            continue

        if current_section == "GENERAL":
            if "=" in s:
                k, v = s.split("=", 1)
                general[k.strip()] = v.strip()
            continue

        if current_section == "SEGMENT" and current_seg is not None:
            if s.startswith("DC;"):
                current_seg["DC"].append(s)
                continue

            if s.startswith("DK;"):
                current_seg["DK"].append(s)
                continue

            if "=" in s:
                k, v = s.split("=", 1)
                current_seg["meta"][k.strip()] = v.strip()

    return general, segments


def get_value_ci(dct, keys, default_value=None):
    if dct is None:
        return default_value

    lowered = {}
    for k, v in dct.items():
        lowered[safe_str(k).lower()] = v

    for key in keys:
        lk = safe_str(key).lower()
        if lk in lowered and safe_str(lowered[lk]) != "":
            return lowered[lk]

    return default_value