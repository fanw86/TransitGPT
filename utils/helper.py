import json
import random
import zipfile
import numpy as np
import io
import base64
import pytz
from datetime import datetime
import pandas as pd
from typing import Any
import plotly.io as pio


def get_current_time():
    # Get the timezone for Chicago
    chicago_tz = pytz.timezone("America/Chicago")
    # Get the current time in Chicago
    current_time_chicago = datetime.now(chicago_tz)
    return current_time_chicago


def jumble_list(original_list):
    # Create a copy of the original list to avoid modifying it directly
    jumbled_list = original_list.copy()

    # Use the Fisher-Yates shuffle algorithm
    for i in range(len(jumbled_list) - 1, 0, -1):
        j = random.randint(0, i)
        jumbled_list[i], jumbled_list[j] = jumbled_list[j], jumbled_list[i]

    return jumbled_list


def list_files_in_zip(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        file_list = zip_ref.namelist()
    return file_list


custom_btns = [
    {
        "name": "Copy",
        "feather": "Copy",
        "hasText": True,
        "alwaysOn": True,
        "commands": ["copyAll"],
        "style": {"top": "0.4rem", "right": "0.4rem"},
    },
    {
        "name": "Run",
        "feather": "Play",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["submit"],
        "style": {"bottom": "0.44rem", "right": "0.4rem"},
    },
]
info_bar = {
    "name": "language info",
    "css": "\nbackground-color: #bee1e5;\n\nbody > #root .ace-streamlit-dark~& {\n   background-color: #262830;\n}\n\n.ace-streamlit-dark~& span {\n   color: #fff;\n    opacity: 0.6;\n}\n\nspan {\n   color: #000;\n    opacity: 0.5;\n}\n\n.code_editor-info.message {\n    width: inherit;\n    margin-right: 75px;\n    order: 2;\n    text-align: center;\n    opacity: 0;\n    transition: opacity 0.7s ease-out;\n}\n\n.code_editor-info.message.show {\n    opacity: 0.6;\n}\n\n.ace-streamlit-dark~& .code_editor-info.message.show {\n    opacity: 0.5;\n}\n",
    "style": {
        "order": "1",
        "display": "flex",
        "flexDirection": "row",
        "alignItems": "center",
        "width": "100%",
        "height": "2.5rem",
        "padding": "0rem 0.6rem",
        "padding-bottom": "0.2rem",
        "margin-bottom": "-1px",
        "borderRadius": "8px 8px 0px 0px",
        "zIndex": "9993",
    },
    "info": [{"name": "python", "style": {"width": "100px"}}],
}


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        dtypes = (np.datetime64, np.complexfloating)
        if isinstance(obj, dtypes):
            return str(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            if any([np.issubdtype(obj.dtype, i) for i in dtypes]):
                return obj.astype(str).tolist()
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    img_str = base64.b64encode(buf.getvalue()).decode()
    return img_str


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... [truncated]"


def summarize_large_output(
    output: Any, max_rows: int = 10, max_chars: int = 2000
) -> str:
    if isinstance(output, pd.DataFrame):
        if len(output) > max_rows:
            output = output.head(max_rows)
            return f"DataFrame with {len(output)} rows (truncated from original), {output.shape[1]} columns. First few rows:\n{output.to_string()}\n... [truncated]"
        return f"DataFrame with {len(output)} rows, {output.shape[1]} columns. Data:\n{output.to_string()}"
    elif isinstance(output, pd.Series):
        if len(output) > max_rows:
            output = output.head(max_rows)
            return f"Series with {len(output)} items (truncated from original). First few items:\n{output.to_string()}\n... [truncated]"
        return f"Series with {len(output)} items. Data:\n{output.to_string()}"
    elif isinstance(output, list):
        if len(output) > max_rows:
            return f"List with {len(output)} items. First {max_rows} items: {str(output[:max_rows])}... [truncated]"
        return f"List with {len(output)} items: {str(output)}"
    elif isinstance(output, dict):
        truncated_dict = dict(list(output.items())[:max_rows])
        truncated_dict = {k: str(v)[:max_chars] for k, v in truncated_dict.items()}
        return f"Dict with {len(output)} keys. First {max_rows} items: {truncated_dict}... [truncated]"
    else:
        return truncate_text(str(output), max_chars)


def plotly_fig_to_base64(fig):
    img_bytes = pio.to_image(fig, format="png")
    img_str = base64.b64encode(img_bytes).decode()
    return img_str

def combine_token_usage(usage_list):
    combined_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }
    for usage in usage_list:
        combined_usage["prompt_tokens"] += usage["prompt_tokens"]
        combined_usage["completion_tokens"] += usage["completion_tokens"]
        combined_usage["total_tokens"] += usage["total_tokens"]
    return combined_usage
