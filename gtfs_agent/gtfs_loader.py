import gtfs_kit as gk
import pandas as pd
import numpy as np
import zipfile
import datetime
import traceback
from typing import Optional, Any
from functools import lru_cache
from utils.helper import list_files_in_zip
from geopy.distance import geodesic
from shapely.geometry import Point
from scipy.spatial import cKDTree

DATE_FORMAT = "%Y%m%d"
DATE_FORMAT_ALT = "%Y-%m-%d"


@lru_cache(maxsize=None)
def process_stop_sequence(stops, shape_coords, k_neighbors=3):
    geo_const = 6371000 * np.pi / 180
    tree = cKDTree(data=shape_coords)

    if len(stops) <= 1:
        return None

    neighbors = k_neighbors
    while True:
        np_dist, np_inds = tree.query(stops, workers=-1, k=neighbors)
        np_dist = np_dist * geo_const
        prev_point = min(np_inds[0])
        points = [prev_point]

        for i, nps in enumerate(np_inds[1:]):
            condition = (nps > prev_point) & (nps < max(np_inds[i + 1]))
            points_valid = nps[condition]
            if len(points_valid) > 0:
                points_score = (np.power(points_valid - prev_point, 3)) * np.power(
                    np_dist[i + 1, condition], 1
                )
                prev_point = nps[condition][np.argmin(points_score)]
                points.append(prev_point)
            else:
                if neighbors < len(stops):
                    neighbors = min(neighbors + 2, len(stops))
                    break
                else:
                    return None

        if len(points) == len(stops):
            return points


def nearest_points(
    stop_df: pd.DataFrame, shape_points: pd.DataFrame, k_neighbors: int = 3
) -> pd.DataFrame:
    stop_df = stop_df.copy()
    stop_df["snap_start_id"] = -1

    shape_coords = np.array([point.coords[0] for point in shape_points]).reshape(-1, 2)

    failed_trips = []
    total_trips = 0
    defective_trips = 0

    for name, group in stop_df.groupby("trip_id"):
        total_trips += 1
        stops = tuple(x.coords[0] for x in group["geometry"])

        points = process_stop_sequence(
            stops, tuple(map(tuple, shape_coords)), k_neighbors
        )

        if points is None:
            failed_trips.append(name)
            defective_trips += 1
            print(f"Excluding Trip: {name} due to processing failure")
        else:
            stop_df.loc[stop_df.trip_id == name, "snap_start_id"] = points

    if defective_trips > 0:
        percent_defective = (defective_trips / total_trips) * 100
        print(f"Total defective trips: {defective_trips}")
        print(f"Percentage defective trips: {percent_defective:.2f}%")

    stop_df = stop_df[~stop_df.trip_id.isin(failed_trips)].reset_index(drop=True)
    return stop_df


class GTFSLoader:
    def __init__(self, gtfs, gtfs_path: str, distance_unit: str = "km"):
        self.gtfs = gtfs
        self.gtfs_path = gtfs_path
        self.feed: Optional[gk.feed] = None
        self.file_list = list_files_in_zip(gtfs_path)
        self.zipfile = zipfile.ZipFile(gtfs_path)
        self.distance_unit = distance_unit

    def __getstate__(self):
        state = self.__dict__.copy()
        if "zipfile" in state:
            del state["zipfile"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def load_feed(self):
        try:
            feed = gk.read_feed(self.gtfs_path, dist_units=self.distance_unit)
            feed = self._process_feed(feed)
            self.feed = feed
        except Exception as e:
            print(f"Error loading GTFS feed: {e}")
            print(traceback.format_exc())
            return False
        return True

    def _process_feed(self, feed):
        feed = self._append_distances(feed)
        feed = feed.clean()
        feed = self._parse_times_and_dates(feed)
        feed = self._remove_empty_attributes(feed)
        return feed

    def _append_distances(self, feed):
        if (
            "shape_dist_traveled" not in feed.shapes.columns
            or feed.shapes.shape_dist_traveled.isna().any()
        ):
            feed = self._calculate_shape_distances(feed)
        if (
            "shape_dist_traveled" not in feed.stop_times.columns
            or feed.stop_times.shape_dist_traveled.isna().any()
        ):
            feed = self._calculate_stop_distances(feed)
        return feed

    def _calculate_shape_distances(self, feed):
        print("Calculating shape distances")

        results = []
        for _, group in feed.shapes.groupby("shape_id"):
            result = self._calculate_single_shape(group, self.distance_unit)
            results.append(result)

        # Combine the results
        feed.shapes = pd.concat(results)

        return feed

    def _calculate_single_shape(self, group, distance_unit):
        cumulative_distance = 0
        previous_point = None

        for idx, row in group.iterrows():
            current_point = (row["shape_pt_lat"], row["shape_pt_lon"])

            if previous_point is not None:
                distance = geodesic(previous_point, current_point).meters
                if distance_unit == "km":
                    distance /= 1000
                elif distance_unit == "miles":
                    distance *= 0.000621371
                cumulative_distance += distance

            group.at[idx, "shape_dist_traveled"] = cumulative_distance
            previous_point = current_point

        return group

    def _calculate_stop_distances(self, feed):
        print("Calculating stop distances")
        stops = feed.stops
        shapes = feed.shapes.sort_values(["shape_id", "shape_pt_sequence"])
        stops["geometry"] = stops.apply(
            lambda row: Point(row["stop_lon"], row["stop_lat"]), axis=1
        )
        # Create a GeoDataFrame with stop locations
        stops_gdf = feed.stop_times.merge(stops[["stop_id", "geometry"]], on="stop_id")
        stops_gdf = stops_gdf.merge(feed.trips[["trip_id", "shape_id"]], on="trip_id")
        # Group by shape_id and apply nearest_points function
        grouped = stops_gdf.groupby("shape_id")
        results = []
        for shape_id, group in grouped:
            shape_id = shape_id.strip()
            shape_points = shapes[shapes.shape_id == shape_id]
            shape_geometry = shape_points.apply(
                lambda x: Point(x["shape_pt_lon"], x["shape_pt_lat"]), axis=1
            )
            result = nearest_points(group, shape_geometry)
            result["shape_dist_traveled"] = shape_points.iloc[result["snap_start_id"]][
                "shape_dist_traveled"
            ].values
            results.append(result)

        # Combine results
        stop_gdf = pd.concat(results)

        # Update feed.stop_times with calculated shape_dist_traveled
        feed.stop_times = feed.stop_times.merge(
            stop_gdf[["trip_id", "stop_sequence", "shape_dist_traveled"]],
            on=["trip_id", "stop_sequence"],
            how="left",
        )

        return feed

    def _parse_times_and_dates(self, feed):
        vparse_time = np.vectorize(self.parse_time)
        vparse_date = np.vectorize(self.parse_date)

        feed.stop_times[["departure_time", "arrival_time"]] = feed.stop_times[
            ["departure_time", "arrival_time"]
        ].apply(vparse_time)

        if hasattr(feed, "timeframes"):
            feed.timeframes[["start_time", "end_time"]] = feed.timeframes[
                ["start_time", "end_time"]
            ].apply(vparse_time)

        for attr in ["calendar", "calendar_dates", "feed_info"]:
            if hasattr(feed, attr) and isinstance(getattr(feed, attr), pd.DataFrame):
                df = getattr(feed, attr)
                date_columns = [col for col in df.columns if "date" in col.lower()]
                df[date_columns] = df[date_columns].apply(vparse_date)
                setattr(feed, attr, df)

        return feed

    def _remove_empty_attributes(self, feed):
        for attr in dir(feed):
            if not attr.startswith("_"):
                value = getattr(feed, attr)
                if value is None or (isinstance(value, pd.DataFrame) and value.empty):
                    try:
                        delattr(feed, attr)
                    except Exception:
                        pass
        return feed

    @lru_cache(maxsize=None)
    def load_all_tables(self):
        if not self.feed and not self.load_feed():
            return

        for table in self.file_list:
            table_name = table.split(".")[0]
            if not hasattr(self.feed, table_name):
                try:
                    with self.zipfile.open(f"{table_name}.txt", "r") as f:
                        df = pd.read_csv(f, encoding="utf-8")
                        setattr(self.feed, table_name, df)
                except Exception as e:
                    print(f"Could not load {table_name} due to {e}")

        print(f"Loaded all tables: {self.gtfs}")
        if hasattr(self, "zipfile"):
            del self.zipfile

    @lru_cache(maxsize=2**18)
    def parse_time(self, val: Any) -> np.float32:
        if isinstance(val, (float, np.float32)) or pd.isna(val):
            return val
        if not val:
            return np.nan
        try:
            return np.float32(val)
        except ValueError:
            h, m, s = map(float, str(val).strip().split(":"))
            return np.float32(h * 3600 + m * 60 + s)

    @lru_cache(maxsize=2**18)
    def parse_date(self, val: str) -> datetime.date:
        if isinstance(val, datetime.date):
            return val
        for date_format in [DATE_FORMAT, DATE_FORMAT_ALT]:
            try:
                return datetime.datetime.strptime(val, date_format).date()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {val}")
