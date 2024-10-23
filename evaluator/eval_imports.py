# Imports for Evals
import datetime
import time
import pytz
import geopy
import folium
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import shapely
import streamlit as st
from shapely.geometry import LineString, Point, Polygon
from thefuzz import process, fuzz
from stqdm import stqdm
from utils.find_stops import (
    get_geo_location,
    find_stops_by_full_name,
    find_stops_by_street,
    find_stops_by_intersection,
    find_nearby_stops,
    find_stops_by_address,
    find_route,
)

# Create a dictionary for namespace with imported modules
import_namespace = {
    "datetime": datetime,
    "time": time,
    "pytz": pytz,
    "geopy": geopy,
    "folium": folium,
    "gpd": gpd,
    "matplotlib": matplotlib,
    "plt": plt,
    "np": np,
    "pd": pd,
    "plotly": plotly,
    "px": px,
    "shapely": shapely,
    "LineString": LineString,
    "Point": Point,
    "Polygon": Polygon,
    "process": process,
    "fuzz": fuzz,
    "stqdm": stqdm,
    "get_geo_location": get_geo_location,
    "find_stops_by_full_name": find_stops_by_full_name,
    "find_stops_by_street": find_stops_by_street,
    "find_stops_by_intersection": find_stops_by_intersection,
    "find_nearby_stops": find_nearby_stops,
    "find_stops_by_address": find_stops_by_address,
    "find_route": find_route,
    "st": st,
    "result": None,
}
