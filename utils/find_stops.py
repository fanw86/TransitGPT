import re
import pandas as pd
from thefuzz import fuzz, process
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import streamlit as st
import googlemaps


def remove_text_in_braces(text):
    # Remove text in braces and any extra spaces left behind
    return re.sub(r"\s*\(.*?\)\s*", " ", text).strip()


def get_geo_location(location_info):
    """
    Retrieve geographical coordinates and formatted address for a given location.

    This function attempts to obtain the latitude and longitude of a specified location
    using either the Google Maps API or the Nominatim geocoding service. If the Google Maps
    API key is available in the Streamlit secrets, it will use that service; otherwise, it
    will fall back to Nominatim.

    Args:
        location_info (str): The location information (e.g., address) to geocode.

    Returns:
        tuple: A tuple containing:
            - (float, float): The latitude and longitude of the location.
            - str: The formatted address of the location, or None if not found.
    """
    if "GMAP_API" in st.secrets:
        try:
            gmaps = googlemaps.Client(key=st.secrets["GMAP_API"])
            location = gmaps.geocode(location_info)
            geometry = location[0]["geometry"]["location"]
            formatted_address = location[0]["formatted_address"]
            return (geometry["lat"], geometry["lng"]), formatted_address
        except Exception:
            return None, None
    else:
        geolocator = Nominatim(user_agent="gtfs2code")
        location = geolocator.geocode(location_info)
        if location:
            return (location.latitude, location.longitude), location.address
        else:
            return None, None

def fuzzy_match(string: str, pattern: str, threshold: int = 80) -> bool:
    """
    Perform a fuzzy string match using partial ratio comparison.

    This function compares two strings using the fuzz.partial_ratio method
    from the fuzzywuzzy library. It returns True if the partial ratio
    between the lowercase versions of the strings is greater than or equal
    to the specified threshold.

    Args:
        string (str): The main string to compare against.
        pattern (str): The pattern string to look for in the main string.
        threshold (int, optional): The minimum partial ratio score required
                                   for a match. Defaults to 80.

    Returns:
        bool: True if the partial ratio is greater than or equal to the
              threshold, False otherwise.
    """
    return fuzz.partial_ratio(string.lower(), pattern.lower()) >= threshold


def find_stops_by_full_name(feed, name: str, threshold: int = 80) -> pd.DataFrame:
    """
    Find stops by fuzzy matching their full names, with and without text in braces.

    This function searches for stops in the provided feed whose names
    fuzzy match the given name parameter. It checks both the original name
    and the name with text in braces removed, returning the best match.

    Args:
        feed: An object containing stop information. Must have a 'stops'
              attribute that is a DataFrame with a 'stop_name' column.
        name (str): The name to search for in stop names.
        threshold (int, optional): The fuzzy matching threshold to use.
                                   Defaults to 80.

    Returns:
        pd.DataFrame: A DataFrame containing all stops whose names fuzzy
                      match the provided name, with the best match score.
    """
    stops_df = feed.stops.copy()
    stops_df["stop_name_cleaned"] = stops_df["stop_name"].apply(remove_text_in_braces)

    stops_df["match_score_original"] = stops_df["stop_name"].apply(
        lambda x: fuzz.partial_ratio(x.lower(), name.lower())
    )
    stops_df["match_score_cleaned"] = stops_df["stop_name_cleaned"].apply(
        lambda x: fuzz.partial_ratio(x.lower(), name.lower())
    )

    stops_df["match_score"] = stops_df[
        ["match_score_original", "match_score_cleaned"]
    ].max(axis=1)

    matching_stops = stops_df[stops_df["match_score"] >= threshold]
    matching_stops = matching_stops.sort_values("match_score", ascending=False)
    best_match = matching_stops["match_score"].max() if not matching_stops.empty else 0
    best_matches = matching_stops[matching_stops["match_score"] == best_match]
    best_matches = best_matches.drop(
        columns=["stop_name_cleaned", "match_score_original", "match_score_cleaned"]
    )

    return best_matches


def find_stops_by_street(feed, street_root: str, threshold: int = 80) -> pd.DataFrame:
    """
    Find stops by fuzzy matching a street name.

    This function searches for stops in the provided feed whose names
    contain a fuzzy match to the given street_root. It normalizes the
    input street name to lowercase before performing the comparison.

    Args:
        feed: An object containing stop information. Must have a 'stops'
              attribute that is a DataFrame with a 'stop_name' column.
        street_root (str): The root word within the street name to search for in stop names. Example: "Main" for "Main St" or "Main Street"
        threshold (int, optional): The fuzzy matching threshold to use.
                                   Defaults to 80.

    Returns:
        pd.DataFrame: A DataFrame containing all stops whose names contain
                      a fuzzy match to the provided street name.
    """

    street_root = street_root.lower()
    stops_df = feed.stops.copy()
    stops_df["stop_name_cleaned"] = stops_df["stop_name"].apply(remove_text_in_braces)
    stops_df["match_score"] = stops_df["stop_name_cleaned"].apply(
        lambda x: fuzz.token_set_ratio(x, street_root)
    )

    matching_stops = stops_df[stops_df["match_score"] >= threshold]
    matching_stops = matching_stops.sort_values("match_score", ascending=False)
    highest_score = (
        matching_stops["match_score"].max() if not matching_stops.empty else 0
    )
    best_matches = matching_stops[matching_stops["match_score"] == highest_score]
    best_matches.drop(columns=["stop_name_cleaned"], inplace=True)
    return best_matches


def find_stops_by_intersection(
    feed, street1_root: str, street2_root: str, threshold: int = 80
) -> pd.DataFrame:
    """
    Find stops by fuzzy matching two intersecting street names.

    This function searches for stops in the provided feed whose names
    contain fuzzy matches to both of the given street names. It's designed
    to find stops at or near intersections.

    Args:
        feed: An object containing stop information. Must have a 'stops'
              attribute that is a DataFrame with a 'stop_name' column.
        street1_root (str): The root word within the first street name to search for in stop names.
        street2_root (str): The root word within the second street name to search for in stop names.
        threshold (int, optional): The fuzzy matching threshold to use.
                                   Defaults to 80.

    Returns:
        pd.DataFrame: A DataFrame containing all stops whose names contain
                      fuzzy matches to both provided street names.
    """
    return feed.stops[
        feed.stops["stop_name"].apply(lambda x: fuzzy_match(x, street1_root, threshold))
        & feed.stops["stop_name"].apply(
            lambda x: fuzzy_match(x, street2_root, threshold)
        )
    ]


def find_nearby_stops(
    lat: float,
    lon: float,
    stops_df: pd.DataFrame,
    max_distance: float = 200,
    max_stops: int = 5,
) -> pd.DataFrame:
    """
    Find stops within a specified distance of a given location.

    This function calculates the distance between a given point (latitude, longitude)
    and all stops in the provided DataFrame. It returns stops within the specified
    maximum distance, sorted by distance from nearest to farthest.

    Args:
        lat (float): Latitude of the location to search from.
        lon (float): Longitude of the location to search from.
        stops_df (pd.DataFrame): DataFrame containing stop information. Must include
                                 'stop_lat' and 'stop_lon' columns.
        max_distance (float): Maximum distance in `meters` to search for stops.

    Returns:
        pd.DataFrame: A DataFrame of stops within the specified distance, sorted by
                      distance. If no stops are within max_distance, returns the 5
                      nearest stops.

    Note:
        This function adds a 'distance' column to the returned DataFrame, representing
        the distance in meters from the given location to each stop.
    """
    stops_df = stops_df.copy()
    stops_df["distance"] = stops_df.apply(
        lambda row: geodesic((lat, lon), (row["stop_lat"], row["stop_lon"])).meters,
        axis=1,
    )
    stops_within_threshold = stops_df[stops_df["distance"] <= max_distance].sort_values(
        "distance"
    )
    if not stops_within_threshold.empty:
        return stops_within_threshold
    else:
        # If no stops within the max_distance, return the 5 nearest stops
        return stops_df.nsmallest(max_stops, "distance")


def find_stops_by_address(
    feed, address: str, radius_meters: float = 200, max_stops: int = 5
) -> pd.DataFrame:
    """
    Find stops near a specified address within a defined radius.

    This function takes an address, converts it to geographic coordinates using
    the get_geo_location function, and then identifies all stops within the specified
    radius of that location.

    Args:
        feed: An object containing stop information. Must have a 'stops' attribute
              that is a DataFrame with 'stop_lat' and 'stop_lon' columns.
        address (str): The address to search near. This will be passed to the
                       get_geo_location function for geocoding. Example: "1004 Main St, Urbana, IL"
        radius_meters (float, optional): The radius in `meters` within which to
                                         search for stops. Defaults to 200 meters.
        max_stops (int, optional): The maximum number of stops to return if no stops
                                    are found within the radius. Defaults to 5.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: A DataFrame of stops within the specified radius of the
                            given address, sorted by distance. If no stops are found
                            within the radius, returns the 5 nearest stops.
            - str: The matched address returned by the geocoding function, or None if not found.
                   Returns an empty DataFrame if the address cannot be geocoded.

    Note:
        This function relies on an external get_geo_location function to convert
        addresses to coordinates. Ensure this function is available in your environment.
    """
    location, matched_address = get_geo_location(address)

    if not location:
        return pd.DataFrame()  # Return empty DataFrame if location not found

    lat, lon = location
    matched_stops = find_nearby_stops(lat, lon, feed.stops, radius_meters, max_stops)

    return matched_stops, matched_address


def find_route(feed, search_term, threshold=80):
    route_fields = ["route_id", "route_short_name", "route_long_name"]

    # Create a long Series with all fields
    long_series = pd.concat([feed.routes[field].astype(str) for field in route_fields])

    # Perform the fuzzy matching on the long series
    match = process.extractOne(search_term, long_series, scorer=fuzz.ratio)

    if match[1] >= threshold:
        route_row = feed.routes.iloc[match[2]]
        return route_row
    else:
        return None  # No match found above the threshold
