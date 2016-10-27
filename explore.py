import os
import sys

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import rawparse
from rawid import Robject, Rnamespace

rawpath = os.path.join(libdir, '../../latest/raw/objects/')
rns = Rnamespace(rawparse.readraw(os.path.join(rawpath, 'creature_mountain_new.txt'), verbosity=1))

