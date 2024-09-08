import sys
import os
import pytest

# Add the parent directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.eval_code import GTFS_Eval, load_zipped_pickle

def test_load_zipped_pickle(tmp_path):
    # Create a mock pickle file for testing
    import pickle
    import gzip
    mock_data = {"test": "data"}
    mock_file = tmp_path / "mock.pkl.gz"
    with gzip.open(mock_file, "wb") as f:
        pickle.dump(mock_data, f)
    
    # Test loading the pickle file
    loaded_data = load_zipped_pickle(mock_file)
    assert loaded_data == mock_data

def test_gtfs_eval_initialization():
    mock_file_mapping = {
        "test_feed": {
            "pickle_loc": "path/to/mock_pickle.pkl.gz"
        }
    }
    
    # Mock the load_zipped_pickle function
    def mock_load_zipped_pickle(filename):
        return type('MockGTFSLoader', (), {'load_all_tables': lambda: None})()
    
    # Patch the load_zipped_pickle function
    with pytest.monkeypatch.context() as m:
        m.setattr("utils.eval_code.load_zipped_pickle", mock_load_zipped_pickle)
        
        eval_instance = GTFS_Eval(mock_file_mapping)
        assert hasattr(eval_instance, "loader_test_feed")

def test_gtfs_eval_load_current_feed():
    # Similar to the initialization test, but test load_current_feed method
    pass

def test_gtfs_eval_get_system_prompt():
    # Test the get_system_prompt method
    pass

def test_gtfs_eval_evaluate():
    # Test the evaluate method with various inputs
    pass

# Add more tests for other methods in GTFS_Eval class