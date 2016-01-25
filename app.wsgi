import os
import sys

# We run the app
sys.path.append('/home/balmas/workspace/MorphologyServiceAPI')
sys.stdout = sys.stderr
from app import app as application
