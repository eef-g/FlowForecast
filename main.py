import subprocess
from importlib.metadata import distribution 
REQUIRED_PACKAGES = ['hydrofunctions', 'tkcalendar','matplotlib',
                     'pandas', 'numpy']

for package in REQUIRED_PACKAGES:
    try:
        dist = distribution(package)
    except:
        subprocess.call(['pip', 'install', package])

import GUI
import warnings

if __name__ == "__main__":
    warnings.simplefilter(action='ignore', category=FutureWarning)
    GUI.create_gui()