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
            "pickle_loc": "test_pickle_feed/CUMTD_gtfs_loader.pkl"
        }
    }
    
    # Mock the load_zipped_pickle function
    def mock_load_zipped_pickle(filename):
        return type('MockGTFSLoader', (), {'load_all_tables': lambda: None})()
    
    # Correct the usage of monkeypatch
    with pytest.MonkeyPatch.context() as m:
        m.setattr("utils.eval_code.load_zipped_pickle", mock_load_zipped_pickle)
        
        eval_instance = GTFS_Eval(mock_file_mapping)
        assert hasattr(eval_instance, "loader_test_feed")

def test_gtfs_eval_load_current_feed():
    mock_file_mapping = {
        "test_feed": {
            "pickle_loc": "test_pickle_feed/CUMTD_gtfs_loader.pkl"
        }
    }
    
    def mock_load_zipped_pickle(filename):
        return type('MockGTFSLoader', (), {
            'load_all_tables': lambda: None,
            'load_current_feed': lambda: "current_feed_data"
        })()
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("utils.eval_code.load_zipped_pickle", mock_load_zipped_pickle)
        
        eval_instance = GTFS_Eval(mock_file_mapping)
        current_feed = eval_instance.loader_test_feed.load_current_feed()
        assert current_feed == "current_feed_data"

def test_gtfs_eval_get_system_prompt():
    mock_file_mapping = {
        "test_feed": {
            "pickle_loc": "test_pickle_feed/CUMTD_gtfs_loader.pkl"
        }
    }
    
    def mock_load_zipped_pickle(filename):
        return type('MockGTFSLoader', (), {
            'load_all_tables': lambda: None,
            'get_system_prompt': lambda: "System prompt"
        })()
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("utils.eval_code.load_zipped_pickle", mock_load_zipped_pickle)
        
        eval_instance = GTFS_Eval(mock_file_mapping)
        system_prompt = eval_instance.loader_test_feed.get_system_prompt()
        assert system_prompt == "System prompt"

def test_gtfs_eval_evaluate():
    mock_file_mapping = {
        "test_feed": {
            "pickle_loc": "test_pickle_feed/CUMTD_gtfs_loader.pkl"
        }
    }
    
    def mock_load_zipped_pickle(filename):
        return type('MockGTFSLoader', (), {
            'load_all_tables': lambda: None,
            'evaluate': lambda x: x * 2  # Example evaluation logic
        })()
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("utils.eval_code.load_zipped_pickle", mock_load_zipped_pickle)
        
        eval_instance = GTFS_Eval(mock_file_mapping)
        result = eval_instance.loader_test_feed.evaluate(5)
        assert result == 10  # Expecting the evaluation to double the input

def test_gtfs_eval_evaluate_timeout():
    mock_file_mapping = {
        "test_feed": {
            "pickle_loc": "test_pickle_feed/CUMTD_gtfs_loader.pkl"
        }
    }
    
    def mock_load_zipped_pickle(filename):
        return type('MockGTFSLoader', (), {
            'load_all_tables': lambda: None,
            'evaluate': lambda code: "Timeout" if "time.sleep(15)" in code else "Executed"
        })()
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("utils.eval_code.load_zipped_pickle", mock_load_zipped_pickle)
        
        eval_instance = GTFS_Eval(mock_file_mapping)
        long_running_code = """```python
import time
time.sleep(15)  # Sleep for 15 seconds to trigger timeout
result = "This should not be reached"
print(result)
```
"""
        result = eval_instance.loader_test_feed.evaluate(long_running_code)
        assert result == "Timeout"

# Add more tests for other methods in GTFS_Eval class