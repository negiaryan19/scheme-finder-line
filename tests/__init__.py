# Make tests a package so pytest can find src
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
