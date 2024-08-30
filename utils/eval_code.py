import sys
import traceback
import re
import _pickle as cPickle
import gzip
## For Evals
from utils.eval_imports import import_namespace

# Custom Imports
from utils.constants import TIMEOUT_SECONDS
from prompts.generate_prompt import generate_system_prompt

def load_zipped_pickle(filename):
    with gzip.open(filename, 'rb') as f:
        loaded_object = cPickle.load(f)
        return loaded_object
    
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

        Parameters:
            code (str): The code to be evaluated.

        Returns:
            tuple: A tuple containing the result of the evaluation, a boolean indicating if the evaluation was successful,
                   detailed error information if the evaluation failed, and a boolean indicating if response is only text.
        """
        # Format string input to extract only the code
        executable_pattern = r"```python\n(.*?)```"
        executable_code = re.findall(executable_pattern, code, re.DOTALL)
        if len(executable_code) > 0:
            code = executable_code[0]
            code = (
                code.split("```python")[1].split("```")[0]
                if "```python" in code
                else code
            )
        else:
            # Has no code block. Send back with only text response
            return (None, True, None, True)
        nm = globals()  # Keep the existing global variables
        nm.update(import_namespace)  # Update with import_namespace
        # Work on a copy of feed. Every run is a new instance
        nm.update({"feed": self.current_loader.feed.copy()})
        try:
            # Set a timeout for execution
            import threading
            import _thread

            def execute_code():
                global execution_result
                execution_result = None
                try:
                    exec(code, nm)
                    execution_result = nm.get("result")
                except Exception as e:
                    execution_result = e

            def timeout_handler():
                _thread.interrupt_main()

            # Define the timeout duration in seconds
            # Create a new thread to execute the code
            execution_thread = threading.Thread(target=execute_code)
            # Create a timer that will call the timeout_handler after TIMEOUT_SECONDS
            timer = threading.Timer(TIMEOUT_SECONDS, timeout_handler)
            timer.start()
            execution_thread.start()
            # Wait for the execution thread to finish, with a timeout of TIMEOUT_SECONDS
            execution_thread.join(TIMEOUT_SECONDS)  # If the thread doesn't finish in TIMEOUT_SECONDS, join() will return
            # Cancel the timer to prevent it from calling the timeout_handler if execution finished in time
            timer.cancel()

            if execution_thread.is_alive():
                raise TimeoutError("Code execution timed out")

            if isinstance(execution_result, Exception):
                raise execution_result

            return (execution_result, True, None, False)
        except Exception as e:
            error_info = self._get_detailed_error_info(e, code)
            return (None, False, error_info, False)

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
            "Traceback (most recent call last):",
        ]

        for filename, line_num, func_name, text in tb:
            if filename == "<string>":
                filename = "Executed Code"
            error_info.append(f"  File '{filename}', line {line_num}, in {func_name}")
            if text:
                error_info.append(f"    {text.strip()}")

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
