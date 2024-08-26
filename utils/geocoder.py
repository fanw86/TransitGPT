import streamlit as st
import googlemaps
gmaps = googlemaps.Client(key=st.secrets["GMAP_API"])
def get_geo_location(location_info):
    try:
        location = gmaps.geocode(location_info)
        geometry = location[0]['geometry']["location"]
        return (geometry["lat"], geometry["lng"]) if location else None
    except:
        return None