#!/usr/bin/env python3
# legacy shim
import subprocess,sys,os
subprocess.run([sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),"make_bulletin.py"),"--feed-only"],check=True)
