import gtfs_kit as gk
from typing import Optional
from utils.helper import list_files_in_zip
import pandas as pd
import numpy as np
import zipfile
import datetime
from functools import lru_cache
import traceback

DATE_FORMAT = "%Y%m%d"


class GTFSLoader:
    def __init__(self, name, gtfs_path: str, distance_unit: str = "km"):
        self.name = name
        self.gtfs_path = gtfs_path
        self.feed: Optional[gk.feed] = None
        self.file_list = list_files_in_zip(gtfs_path)
        self.zipfile = zipfile.ZipFile(gtfs_path)
        self.distance_unit = distance_unit

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
            try:
                setattr(self, table, getattr(self.feed, table))
                # print(f"Loaded {table}")
            except AttributeError:
                try:
                    with self.zipfile.open(table + ".txt", "r") as f:
                        df = pd.read_csv(
                            f,
                            encoding="utf-8",
                        )
                        setattr(self, table, df)
                        # print(f"Loaded {table}")
                except Exception as e:
                    print(f"Could not load {table} due to {e}")

        print(f"Loaded all tables: {self.name}")
        if hasattr(self, "feed"):
            del (
                self.feed
            )  # Remove the feed object to free up memory and make it picklable
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
