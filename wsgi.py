import sys
import os

# Add the project directory to sys.path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# Import the Flask application object
# PythonAnywhere's WSGI server hooks into 'application' by default
from app import app as application
