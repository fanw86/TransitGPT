import sys
import os
import pytest
import pandas as pd
import numpy as np
import datetime

# Add the parent directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gtfs_agent.gtfs_loader import GTFSLoader

@pytest.fixture
def mock_gtfs_loader():
    return GTFSLoader("mock_gtfs", "path/to/mock.zip", "km")

def test_gtfs_loader_initialization(mock_gtfs_loader):
    assert mock_gtfs_loader.gtfs == "mock_gtfs"
    assert mock_gtfs_loader.gtfs_path == "path/to/mock.zip"
    assert mock_gtfs_loader.distance_unit == "km"

def test_parse_time(mock_gtfs_loader):
    assert mock_gtfs_loader.parse_time("12:34:56") == np.float32(45296)
    assert np.isnan(mock_gtfs_loader.parse_time(""))
    assert mock_gtfs_loader.parse_time(45296) == np.float32(45296)

def test_parse_date(mock_gtfs_loader):
    assert mock_gtfs_loader.parse_date("20230101") == datetime.date(2023, 1, 1)
    assert mock_gtfs_loader.parse_date("2023-01-01") == datetime.date(2023, 1, 1)

# Add more tests for other methods in GTFSLoader