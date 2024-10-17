import sys
import traceback
import re
import _pickle as cPickle
import gzip
import threading
import copy
import warnings
from typing import Dict, Any

## For Evals
from evaluator.eval_imports import import_namespace
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Custom Imports
from utils.constants import TIMEOUT_SECONDS
from prompts.generate_prompt import generate_system_prompt

warnings.filterwarnings("ignore")


def load_zipped_pickle(filename: str) -> Any:
    with gzip.open(filename, "rb") as f:
        return cPickle.load(f)


class PropagatingThread(threading.Thread):
    def run(self):
        self.exc = None
        self.ret = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        super().join(timeout)
        if self.exc:
            raise self.exc
        return self.ret


class GTFS_Eval:
    def __init__(self, file_mapping: Dict[str, Dict[str, str]]):
        self.file_mapping = file_mapping
        self.current_loader = None
        self.gtfs = None
        self.system_prompt = None
        self.distance_unit = None
        self.allow_viz = None
        # Initialize GTFSLoader objects for each GTFS feed in the selectbox with feed_sfmta
        for key, value in self.file_mapping.items():
            setattr(
                self, f"loader_{key.lower()}", load_zipped_pickle(value["pickle_loc"])
            )

    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove the evaluate method from the state
        del state["evaluate"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def load_current_feed(self, GTFS: str):
        current_loader = getattr(self, f"loader_{GTFS.lower()}")
        if self.gtfs != GTFS:
            # Load all tables for the selected GTFS feed
            # current_loader.load_all_tables()
            self.gtfs = GTFS
            print(f"Loaded feed {self.gtfs}")
        return current_loader

    def get_system_prompt(self, GTFS, distance_unit, allow_viz):
        if (
            self.system_prompt is None
            or self.gtfs != GTFS
            or self.distance_unit != distance_unit
            or self.allow_viz != allow_viz
        ):
            self.current_loader = self.load_current_feed(GTFS)
            self.distance_unit = distance_unit
            self.allow_viz = allow_viz
            # Generate the system prompt
            self.system_prompt = generate_system_prompt(self.current_loader, allow_viz)
        return self.system_prompt

    def evaluate(
        self, code: str, timeout_seconds: int = TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """
        Evaluates the given code and returns the result.
        """
        # Extract executable code from the input
        executable_code = re.findall(r"```python\n(.*?)```", code, re.DOTALL)

        # For text only responses
        if not executable_code:
            return {
                "code_output": code,
                "eval_success": False,
                "error_message": None,
                "only_text": True,
            }

        code = executable_code[0]
        nm = {
            **globals(),
            **import_namespace,
            "feed": copy.deepcopy(self.current_loader.feed),
        }  # Deep copy of feed

        try:

            def execute_code():
                global execution_result
                exec(code, nm)
                execution_result = nm.get("result")

            thread = PropagatingThread(target=execute_code)
            add_script_run_ctx(thread)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout_seconds)

            if thread.is_alive():
                raise TimeoutError("Code execution timed out")
            if execution_result is None:
                raise Exception(
                    "Code execution did not return a result. Please ensure the `result` variable is assigned"
                )
            return {
                "code_output": execution_result,
                "eval_success": True,
                "error_message": None,
                "only_text": False,
            }

        except TimeoutError as te:
            print(f"TimeoutError: {str(te)}")
            return {
                "code_output": None,
                "eval_success": False,
                "error_message": f"TimeoutError: {str(te)}",
                "only_text": False,
            }

        except Exception as e:
            error_message = self._get_detailed_error_info(e, code)
            return {
                "code_output": None,
                "eval_success": False,
                "error_message": error_message,
                "only_text": False,
            }

    def _get_detailed_error_info(self, error: Exception, code: str) -> str:
        """
        Get detailed error information including the full traceback and relevant code snippet.
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.extract_tb(exc_traceback)

        # Find the last frame that refers to our code
        relevant_frame = next(
            (frame for frame in reversed(tb) if frame.filename == "<string>"), None
        )

        if relevant_frame:
            line_no = relevant_frame.lineno
            code_lines = code.split("\n")
            start_line = max(0, line_no - 3)
            end_line = min(len(code_lines), line_no + 2)
            relevant_code = "\n".join(
                f"{i+1}: {line}"
                for i, line in enumerate(code_lines[start_line:end_line])
            )
        else:
            relevant_code = "Unable to locate relevant code snippet"

        error_info = [
            f"Error Type: {exc_type.__name__}",
            f"Error Message: {str(error)}",
            "Relevant Code:",
            relevant_code + "\n",
        ]

        return "\n".join(error_info)

    def reset(self):
        """
        Resets the GTFS_Eval instance by clearing the current feed and system prompt.
        """
        self.current_loader = None
        self.gtfs = None
        self.system_prompt = None
        self.distance_unit = None
        print("GTFS_Eval instance has been reset.")
