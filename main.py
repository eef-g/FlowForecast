import subprocess
from importlib.metadata import distribution 
REQUIRED_PACKAGES = ['hydrofunctions', 'tkcalendar','matplotlib',
                     'pandas', 'numpy']

# Check and make sure all of the required packages are installed on the computer & install any uninstalled packages
for package in REQUIRED_PACKAGES:
    try:
        dist = distribution(package)
    except:
        subprocess.call(['pip', 'install', package])

# Now import the files that are used in the project to avoid any missing dependencies
import GUI
import warnings

if __name__ == "__main__":
    warnings.simplefilter(action='ignore', category=FutureWarning) # Mute the warning about sorting by keys
    GUI.create_gui()