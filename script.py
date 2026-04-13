# -*- coding: utf-8 -*-

import os
import sys

THIS_DIR = os.path.dirname(__file__)
LIB_DIR = os.path.join(THIS_DIR, "lib")

if LIB_DIR not in sys.path:
    sys.path.append(LIB_DIR)

from ui_controller import run_tool

if __name__ == "__main__":
    run_tool()