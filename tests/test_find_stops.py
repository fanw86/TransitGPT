import sys
import os
import pandas as pd
from unittest.mock import patch

# Add the parent directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.find_stops import (
    remove_text_in_braces,
    fuzzy_match,
    find_stops_by_full_name,
    find_stops_by_street,
    find_stops_by_intersection,
    find_nearby_stops,
    find_stops_by_address,
    find_route
)

def test_remove_text_in_braces():
    assert remove_text_in_braces("Test (remove) this") == "Test this"
    assert remove_text_in_braces("No braces here") == "No braces here"

def test_fuzzy_match():
    assert fuzzy_match("hello world", "hello", threshold=80)
    assert not fuzzy_match("hello world", "goodbye", threshold=80)

def test_find_stops_by_full_name():
    mock_feed = type('MockFeed', (), {
        'stops': pd.DataFrame({
            'stop_name': ['Test Stop', 'Another Stop', 'Test Station'],
            'stop_id': ['1', '2', '3']
        })
    })()
    result = find_stops_by_full_name(mock_feed, "Test Stop")
    assert len(result) == 1
    assert result.iloc[0]['stop_id'] == '1'

def test_find_stops_by_street():
    mock_feed = type('MockFeed', (), {
        'stops': pd.DataFrame({
            'stop_name': ['123 Main St', '456 Elm St', '789 Oak Ave'],
            'stop_id': ['1', '2', '3']
        })
    })()
    result = find_stops_by_street(mock_feed, "Main St")
    assert len(result) == 1
    assert result.iloc[0]['stop_id'] == '1'

def test_find_stops_by_intersection():
    mock_feed = type('MockFeed', (), {
        'stops': pd.DataFrame({
            'stop_name': ['Main St & Elm St', 'Oak Ave & Pine St', 'Maple Rd & Cedar Ln'],
            'stop_id': ['1', '2', '3']
        })
    })()
    result = find_stops_by_intersection(mock_feed, "Main", "Elm")
    assert len(result) == 1
    assert result.iloc[0]['stop_id'] == '1'

def test_find_nearby_stops():
    mock_stops_df = pd.DataFrame({
        'stop_lat': [40.7128, 40.7130, 40.7135],
        'stop_lon': [-74.0060, -74.0059, -74.0058],
        'stop_name': ['Stop A', 'Stop B', 'Stop C']
    })
    result = find_nearby_stops(40.7129, -74.0061, mock_stops_df, max_distance=200)
    assert len(result) > 0

def test_find_stops_by_address():
    mock_feed = type('MockFeed', (), {
        'stops': pd.DataFrame({
            'stop_name': ['123 Main St', '456 Elm St', '789 Oak Ave'],
            'stop_id': ['1', '2', '3'],
            'stop_lat': [40.7128, 40.7130, 40.7135],
            'stop_lon': [-74.0060, -74.0059, -74.0058]
        })
    })()

    # Mock the get_geo_location function
    with patch('utils.find_stops.get_geo_location') as mock_geo:
        mock_geo.return_value = (40.7129, -74.0061)  # Example coordinates
        
        # Provide the 'city' argument
        result = find_stops_by_address(mock_feed, "123 Main St", "New York")
        
        assert len(result) > 0
        assert result.iloc[0]['stop_id'] == '1'
        
        # Update the expected call to include the city
        mock_geo.assert_called_once_with("123 Main St, New York")

    # Test case when no stops are found
    with patch('utils.find_stops.get_geo_location') as mock_geo:
        mock_geo.return_value = (41.0, -75.0)  # Coordinates far from any mock stop
        
        # Provide the 'city' argument here as well
        result = find_stops_by_address(mock_feed, "999 Far Away St", "New York")
        
        assert len(result) == 0

def test_find_route():
    mock_feed = type('MockFeed', (), {
        'routes': pd.DataFrame({
            'route_id': ['1', '2', '3'],
            'route_short_name': ['A', 'B', 'C'],
            'route_long_name': ['Route A', 'Route B', 'Route C']
        })
    })()
    result = find_route(mock_feed, "Route A")
    assert result is not None
    assert result['route_id'] == '1'

# Add more tests as needed