import sys
import traceback
import re
import _pickle as cPickle
import gzip
import threading  # Add this import

## For Evals
from evaluator.eval_imports import import_namespace
from streamlit.runtime.scriptrunner import add_script_run_ctx
# Custom Imports
from utils.constants import TIMEOUT_SECONDS
from prompts.generate_prompt import generate_system_prompt

# Ignore warnings as LLM tend to use old documentation
import warnings
warnings.filterwarnings("ignore")

def load_zipped_pickle(filename):
    with gzip.open(filename, "rb") as f:
        loaded_object = cPickle.load(f)
        return loaded_object

class PropagatingThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Call the parent constructor

    def run(self):
        self.exc = None
        self.ret = None
        try:
            if hasattr(self, '_Thread__target'):
                self.ret = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
            else:
                self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        return self.ret
    
class GTFS_Eval:
    def __init__(self, file_mapping):
        self.current_loader = None
        self.gtfs = None
        self.system_prompt = None
        self.file_mapping = file_mapping
        self.distance_unit = None
        # Initialize GTFSLoader objects for each GTFS feed in the selectbox with feed_sfmta
        for key in self.file_mapping:
            pickle_file = self.file_mapping[key]["pickle_loc"]
            gtfs_loader = load_zipped_pickle(pickle_file)
            setattr(
                self,
                f"loader_{key.lower()}",
                gtfs_loader,
            )
    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove the evaluate method from the state
        del state['evaluate']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        
    def load_current_feed(self, GTFS):
        if not self.gtfs or self.gtfs != GTFS:
            current_loader = getattr(self, f"loader_{GTFS.lower()}")
            # Load all tables for the selected GTFS feed
            current_loader.load_all_tables()
            self.gtfs = GTFS
            print(f"Loaded feed {self.gtfs}")
        return current_loader

    def get_system_prompt(self, GTFS, distance_unit="m"):
        if (
            self.system_prompt is None
            or self.gtfs != GTFS
            or self.distance_unit != distance_unit
        ):
            if self.gtfs != GTFS:
                self.current_loader = self.load_current_feed(GTFS)
                self.gtfs = GTFS

            self.distance_unit = distance_unit
            loader = self.current_loader
            # Generate the system prompt
            self.system_prompt = generate_system_prompt(loader)

        return self.system_prompt

    def evaluate(self, code):
        """
        Evaluates the given code and returns the result.
        """
        # Extract executable code from the input
        executable_pattern = r"```python\n(.*?)```"
        executable_code = re.findall(executable_pattern, code, re.DOTALL)
        if executable_code:
            code = executable_code[0]
        else:
            return {
                "code_output": code,
                "eval_success": False,
                "error_message": None,
                "only_text": True
            }  # No code block

        nm = globals()  # Keep existing global variables
        nm.update(import_namespace)  # Update with import_namespace
        nm["feed"] = self.current_loader.feed.copy()  # Work on a copy of feed

        try:
            def execute_code():
                global execution_result
                try:
                    exec(code, nm)
                    execution_result = nm.get("result")
                except Exception as inner_e:
                    raise inner_e
            thread = PropagatingThread(target=execute_code)
            add_script_run_ctx(thread)
            thread.daemon = True
            thread.start()
            thread.join(timeout=TIMEOUT_SECONDS)
            if thread.is_alive():
                raise TimeoutError("Code execution timed out")

            return {
                "code_output": execution_result,
                "eval_success": True,
                "error_message": None,
                "only_text": False
            }
        except TimeoutError as te:
            print(f"TimeoutError: {str(te)}")
            return {
                "code_output": None,
                "eval_success": False,
                "error_message": f"TimeoutError: {str(te)}",
                "only_text": False
            }
        except Exception as e:
            error_message = self._get_detailed_error_info(e, code)
            return {
                "code_output": None,
                "eval_success": False,
                "error_message": error_message,
                "only_text": False
            }  # Return actual error message

    def _get_detailed_error_info(self, error: Exception, code: str) -> str:
        """
        Get detailed error information including the full traceback and relevant code snippet.
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.extract_tb(exc_traceback)

        # Find the last frame that refers to our code
        relevant_frame = None
        for frame in reversed(tb):
            if frame.filename == "<string>":
                relevant_frame = frame
                break

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
            # "Traceback (most recent call last):",
        ]

        # for filename, line_num, func_name, text in tb:
        #     if filename == "<string>":
        #         filename = "Executed Code"
        #     error_info.append(f"  File '{filename}', line {line_num}, in {func_name}")
        #     if text:
        #         error_info.append(f"    {text.strip()}")

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
