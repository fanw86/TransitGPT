import os
import pickle
import gtfs_kit as gk
import pandas as pd
import numpy as np
import zipfile
import datetime
import traceback
import json
from typing import Optional
from functools import lru_cache
from utils.helper import list_files_in_zip

DATE_FORMAT = "%Y%m%d"


def pickle_gtfs_loaders(file_mapping, output_directory, mapping_file_path):
    """
    Create, pickle, and store GTFSLoader objects based on the provided file mapping.
    Update the file_mapping with pickle locations and save it to a specified path.

    Args:
    file_mapping (dict): A dictionary containing agency names as keys and dictionaries
                         with 'file_loc' and 'distance_unit' as values.
    output_directory (str): The directory where pickled objects will be stored.
    mapping_file_path (str): The file path where the updated file_mapping will be saved.

    Returns:
    None
    """
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for agency_name, agency_data in file_mapping.items():
        try:
            # Create GTFSLoader object
            loader = GTFSLoader(
                gtfs=agency_name,
                gtfs_path=agency_data['file_loc'],
                distance_unit=agency_data['distance_unit'] or 'km'  # Default to 'km' if None
            )

            # Load all tables
            loader.load_all_tables()

            # Create a filename based on the agency name
            filename = f"{agency_name}_gtfs_loader.pkl"
            filepath = os.path.join(output_directory, filename)

            # Pickle and save the loader
            with open(filepath, 'wb') as f:
                pickle.dump(loader, f)

            print(f"Pickled and stored {agency_name} at {filepath}")

            # Add pickle location to file_mapping
            agency_data['pickle_loc'] = filepath

        except Exception as e:
            print(f"Error processing {agency_name}: {str(e)}")
            # Add error information to file_mapping
            agency_data['error'] = str(e)

    # Save updated file_mapping
    with open(mapping_file_path, 'w') as f:
        json.dump(file_mapping, f, indent=2)

    print(f"Updated file mapping saved to {mapping_file_path}")

class GTFSLoader:
    def __init__(self, gtfs, gtfs_path: str, distance_unit: str = "km"):
        self.gtfs = gtfs
        self.gtfs_path = gtfs_path
        self.feed: Optional[gk.feed] = None
        self.file_list = list_files_in_zip(gtfs_path)
        self.zipfile = zipfile.ZipFile(gtfs_path)
        self.distance_unit = distance_unit

    def __getstate__(self):
        # This method is called when pickling
        state = self.__dict__.copy()
        # Don't pickle the 'feed' and 'zipfile' attributes
        # if "feed" in state:
        #     del state["feed"]
        if "zipfile" in state:
            del state["zipfile"]
        return state

    def __setstate__(self, state):
        # This method is called when unpickling
        self.__dict__.update(state)
        # Recreate the zipfile object if needed
        if hasattr(self, "gtfs_path"):
            self.zipfile = zipfile.ZipFile(self.gtfs_path)

    def load_feed(self):
        """Load the GTFS feed using GTFS Kit."""
        try:
            feed = gk.read_feed(self.gtfs_path, dist_units=self.distance_unit)
            if (
                "shape_dist_traveled" not in feed.stop_times.columns
                or sum(feed.stop_times.shape_dist_traveled.isna()) > 0
            ):
                feed = feed.append_dist_to_stop_times()
            if (
                "shape_dist_traveled" not in feed.shapes.columns
                or sum(feed.shapes.shape_dist_traveled.isna()) > 0
            ):
                feed = feed.append_dist_to_shapes()
            feed = feed.clean()
            vparse_time = np.vectorize(self.parse_time)
            feed.stop_times["departure_time"] = vparse_time(
                feed.stop_times["departure_time"]
            )
            feed.stop_times["arrival_time"] = vparse_time(
                feed.stop_times["arrival_time"]
            )
            if hasattr(feed, "timeframes"):
                feed.timeframes["start_time"] = vparse_time(
                    feed.timeframes["start_time"]
                )
                feed.timeframes["end_time"] = vparse_time(feed.timeframes["end_time"])
            vparse_date = np.vectorize(self.parse_date)
            feed.calendar["start_date"] = vparse_date(feed.calendar["start_date"])
            feed.calendar["end_date"] = vparse_date(feed.calendar["end_date"])
            feed.calendar_dates["date"] = vparse_date(feed.calendar_dates["date"])
            if hasattr(feed, "feed_info") and isinstance(feed.feed_info, pd.DataFrame):
                feed.feed_info["feed_start_date"] = vparse_date(
                    feed.feed_info["feed_start_date"]
                )
                feed.feed_info["feed_end_date"] = vparse_date(
                    feed.feed_info["feed_end_date"]
                )
            self.feed = feed
            # self.feed = ptg.load_feed(self.gtfs_path)
        except Exception as e:
            print(f"Error loading GTFS feed: {e}")
            print(traceback.format_exc())
            return False
        return True

    @lru_cache(maxsize=None)
    def load_all_tables(self):
        """Load all available GTFS tables as attributes."""
        if not self.feed:
            if not self.load_feed():
                return

        for table in self.file_list:
            table = table.split(".")[0]
            if not hasattr(self.feed, table):
                try:
                    with self.zipfile.open(table + ".txt", "r") as f:
                        df = pd.read_csv(f, encoding="utf-8")
                        setattr(self.feed,table,df) 
                except Exception as e:
                    print(f"Could not load {table} due to {e}")

        print(f"Loaded all tables: {self.gtfs}")
        # if hasattr(self, "feed"):
        #     del (
        #         self.feed
        #     )  # Remove the feed object to free up memory and make it picklable
        if hasattr(self, "zipfile"):
            del self.zipfile

    @lru_cache(maxsize=2**18)
    def parse_time(self, val: str) -> np.float32:
        """
        The function `parse_time` takes a string representing a time value in the format "hh:mm:ss" and
        returns the equivalent time in seconds as a numpy int, or returns the input value if it is
        already a numpy int or int.

        Args:
        val (str): The parameter `val` is a string representing a time value in the format "hh:mm:ss".

        Returns:
        a value of type np.float32.
        """
        if isinstance(val, float) or (
            isinstance(val, float) and np.isnan(val)
        ):  # Corrected handling for np.nan
            return val
        if str(val) == "":
            return np.nan
        val = str(val).strip()

        h, m, s = map(float, val.split(":"))
        return np.float32(h * 3600 + m * 60 + s)

    @lru_cache(maxsize=2**18)
    def parse_date(self, val: str) -> datetime.date:
        """
        The function `parse_date` takes a string or a `datetime.date` object as input and returns a
        `datetime.date` object.

        Args:
        val (str): The `val` parameter is a string representing a date.

        Returns:
        a `datetime.date` object.
        """
        if isinstance(val, datetime.date):
            return val
        return datetime.datetime.strptime(val, DATE_FORMAT).date()
