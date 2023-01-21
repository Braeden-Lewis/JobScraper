# Standard Library Imports
import json
import os
import sys

from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------- #
# --------------------------------- CLASSES ---------------------------------- #
# ---------------------------------------------------------------------------- #

class Configuration:
    __slots__ = (
        "version",
        "driver",
        "url",
        "job",
        "location"
    )

    def __init__(self, driver):
        self.driver = driver

        try:
            config = sys.argv[1]
            active_settings = json.load(open(config, 'r'))
            for active_setting in active_settings:
                setattr(self, active_setting, active_settings[active_setting])
            all_settings = list(getattr(self, attr) for attr in self.__slots__)

        except IndexError as exc:
            print("Configurations not found. Exception: ", exc)
            exit(-1)
        except FileNotFoundError as exc:
            print("Configuration argument detected, but no such file exists. Exception: ", exc)
            return
            exit(-1)
        except AttributeError as exc:
            print("Wrong settings provided or missing in configuration file. Exception: ", exc)
            exit(-1)


class Directories:
    ROOT = os.path.dirname(os.path.abspath(__file__))
