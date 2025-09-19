# -*- coding: utf-8 -*-
"""Add paths for unittest"""

import os
import sys
PROJECT_PATH = os.getcwd()
SOURCE_PATH = os.path.join(PROJECT_PATH, 'lib')
TESTS_PATH = os.path.join(PROJECT_PATH, 'tests')
sys.path.append(SOURCE_PATH)
sys.path.append(TESTS_PATH)
