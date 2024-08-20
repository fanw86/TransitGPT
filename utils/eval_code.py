import datetime
import sys
import time
import traceback

## For Evals
import folium
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import shapely
from shapely.geometry import LineString, Point, Polygon

from prompts.generate_prompt import generate_system_prompt
from utils.gtfs_loader import GTFSLoader


class GTFS_Eval:
    def __init__(self, file_mapping):
        self.feed_main = None
        self.gtfs = None
        self.system_prompt = None
        self.file_mapping = file_mapping
        self.distance_unit = None
        # Initialize GTFSLoader objects for each GTFS feed in the selectbox with feed_sfmta
        for key in self.file_mapping:
            file_location = self.file_mapping[key]["file_loc"]
            distance_unit = self.file_mapping[key]["distance_unit"]
            setattr(
                self,
                f"feed_{key.lower()}",
                GTFSLoader(key, file_location, distance_unit),
            )

    def load_current_feed(self, GTFS):
        if not self.gtfs or self.gtfs != GTFS:
            feed_main = getattr(self, f"feed_{GTFS.lower()}")
            # Load all tables for the selected GTFS feed
            feed_main.load_all_tables()
            self.gtfs = GTFS
            print(f"Loaded feed {self.gtfs}")
        return feed_main

    def load_system_prompt(self, GTFS, distance_unit="m"):
        if (
            self.system_prompt is None
            or self.gtfs != GTFS
            or self.distance_unit != distance_unit
        ):
            if self.gtfs != GTFS:
                self.feed_main = self.load_current_feed(GTFS)
                self.gtfs = GTFS

            self.distance_unit = distance_unit
            self.system_prompt = generate_system_prompt(
                self.gtfs, self.feed_main, self.distance_unit
            )

        return self.system_prompt

    def evaluate(self, code):
        """
        Evaluates the given code and returns the result.

        Parameters:
            code (str): The code to be evaluated.

        Returns:
            tuple: A tuple containing the result of the evaluation, a boolean indicating if the evaluation was successful,
                   detailed error information if the evaluation failed, and a boolean indicating if response is only text.
        """
        # Format string input to extract only the code
        if "```python" in code:
            code = (
                code.split("```python")[1].split("```")[0]
                if "```python" in code
                else code
            )
        else:
            # Has no code block. Send back with only text response
            return (None, True, None, True)
        nm = globals()
        locals_dict = {
            "result": None,
        }
        nm.update(locals_dict)
        nm.update({"feed": self.feed_main})
        try:
            exec(code, nm)
            return (nm.get("result"), True, None, False)
        except Exception as e:
            error_info = self._get_detailed_error_info(e, code)
            return (None, False, error_info, False)

    def _get_detailed_error_info(self, error: Exception, code: str) -> str:
        """
        Get detailed error information including the full traceback and relevant code snippet.
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.extract_tb(exc_traceback)
        
        # Find the last frame that refers to our code
        relevant_frame = None
        for frame in reversed(tb):
            if frame.filename == '<string>':
                relevant_frame = frame
                break
        
        if relevant_frame:
            line_no = relevant_frame.lineno
            code_lines = code.split('\n')
            start_line = max(0, line_no - 3)
            end_line = min(len(code_lines), line_no + 2)
            relevant_code = '\n'.join(f"{i+1}: {line}" for i, line in enumerate(code_lines[start_line:end_line]))
        else:
            relevant_code = "Unable to locate relevant code snippet"

        error_info = [
            f"Error Type: {exc_type.__name__}",
            f"Error Message: {str(error)}",
            "Relevant Code:",
            relevant_code+"\n",
            "Traceback (most recent call last):",
        ]

        for filename, line_num, func_name, text in tb:
            if filename == '<string>':
                filename = 'Executed Code'
            error_info.append(f"  File '{filename}', line {line_num}, in {func_name}")
            if text:
                error_info.append(f"    {text.strip()}")
        
        return "\n".join(error_info)
    
    def reset(self):
        """
        Resets the GTFS_Eval instance by clearing the current feed and system prompt.
        """
        self.feed_main = None
        self.gtfs = None
        self.system_prompt = None
        self.distance_unit = None
        print("GTFS_Eval instance has been reset.")
