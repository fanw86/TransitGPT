import sys
import os
import pytest

# Add the parent directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluator.eval_code import GTFS_Eval, load_zipped_pickle

@pytest.fixture
def gtfs_evaluator():
    mock_file_mapping = {
        "CUMTD": {
            "pickle_loc": "tests/test_pickle_feed/CUMTD_gtfs_loader.pkl"
        }
    }
    evaluator = GTFS_Eval(mock_file_mapping)
    evaluator.get_system_prompt("CUMTD")
    return evaluator

def test_gtfs_eval_evaluate_timeout(gtfs_evaluator):
    mock_file_mapping = {
        "CUMTD": {
            "pickle_loc": "tests/test_pickle_feed/CUMTD_gtfs_loader.pkl"
        }
    }
        
    evaluator = GTFS_Eval(mock_file_mapping)
    evaluator.get_system_prompt("CUMTD")
    long_running_code = """
```python
import time
time.sleep(15)  # Sleep for 15 seconds to trigger timeout
result = "This should not be reached"
print(result)
```
"""
    result = evaluator.evaluate(long_running_code, timeout_seconds=1)
    print(result)
    assert result["eval_success"] == False
    assert "TimeoutError" in result["error_message"]
    
    long_for_loop = """
```python
import time
for i in range(100):
    time.sleep(1)
```
"""
    result = evaluator.evaluate(long_for_loop, timeout_seconds=1)
    print(result)
    assert result["eval_success"] == False
    assert "TimeoutError" in result["error_message"]
    
    long_dataframe_operation = """
```python
import time
import math
import pandas as pd
df = pd.DataFrame({'A': range(1000000000)})
result = df['A'].apply(lambda x: math.sqrt(x))
```
"""
    result = evaluator.evaluate(long_dataframe_operation, timeout_seconds=1)
    print(result)
    assert result["eval_success"] == False
    assert "TimeoutError" in result["error_message"]

def test_import_error(gtfs_evaluator):
    code_with_import_error = """
```python
import non_existent_module
print("This should not be reached")
```
"""
    result = gtfs_evaluator.evaluate(code_with_import_error)
    assert result["eval_success"] == False
    assert "ModuleNotFoundError" in result["error_message"]

def test_index_error(gtfs_evaluator):
    code_with_index_error = """
```python
my_list = [1, 2, 3]
print(my_list[10])
```
"""
    result = gtfs_evaluator.evaluate(code_with_index_error)
    assert result["eval_success"] == False
    assert "IndexError" in result["error_message"]

def test_key_error(gtfs_evaluator):
    code_with_key_error = """
```python
my_dict = {"a": 1, "b": 2}
print(my_dict["c"])
```
"""
    result = gtfs_evaluator.evaluate(code_with_key_error)
    assert result["eval_success"] == False
    assert "KeyError" in result["error_message"]

def test_name_error(gtfs_evaluator):
    code_with_name_error = """
```python
print(fuzzywuzzy.process.extractOne("hello", ["hello", "world"]))
```
"""
    result = gtfs_evaluator.evaluate(code_with_name_error)
    assert result["eval_success"] == False
    assert "NameError" in result["error_message"]