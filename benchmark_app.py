import streamlit as st
import pandas as pd
import json
import yaml
import os
from datetime import datetime
from stqdm import stqdm
from utils.constants import LLMs, file_mapping
from utils.helper import NpEncoder
from gtfs_agent.agent import LLMAgent
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from streamlit_shortcuts import button, add_keyboard_shortcuts
from streamlit_extras.add_vertical_space import add_vertical_space


@st.cache_resource
def get_agent(model):
    return LLMAgent(file_mapping, model=model)


st.set_page_config(layout="wide")


def run_benchmark(df, model):
    new_results = []
    additional_results = []
    agent = get_agent(model)
    # df = df.head(1) # For testing: Remove this
    for index, row in stqdm(df.iterrows(), total=df.shape[0]):
        st.write(f"Running {index + 1} of {df.shape[0]}")
        allow_viz = (
            row["visualization"]
            if "visualization" in row
            else st.session_state.allow_viz
        )
        allow_retry = (
            row["allow_retry"] if "allow_retry" in row else st.session_state.allow_retry
        )
        agent.update_agent(
            row["feed"], model, file_mapping[row["feed"]]["distance_unit"], allow_viz
        )
        agent.reset()  # Ensure chat history is cleared
        result = agent.run_workflow(
            row["question"], allow_retry, summarize=False, task=row["task"]
        )
        
        # Handle visualization outputs
        if allow_viz and result["code_output"]:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            viz_dir = "benchmark/visualizations"
            os.makedirs(viz_dir, exist_ok=True)
            
            if isinstance(result["code_output"], dict):
                if "map" in result["code_output"]:
                    map_path = f"{viz_dir}/{timestamp}_{index}_map.html"
                    result["code_output"]["map"].save(map_path)
                    result["code_output"]["map"] = map_path
                    
                if "plot" in result["code_output"]:
                    plot_path = f"{viz_dir}/{timestamp}_{index}_plot.png"
                    result["code_output"]["plot"].write_image(plot_path)
                    result["code_output"]["plot"] = plot_path

        new_results.append({"result": result["code_output"]})
        additional_results.append(
            {
                "task": row["task"],
                "success": result["eval_success"],
                "error": result["error_message"],
                "only_text": result["only_text"],
                "llm_response": str(result["main_response"]),
                "execution_time": result["execution_time"],
            }
        )
        # time.sleep(5)
    return new_results, additional_results


def save_benchmark_results(model, results, additional_results):
    timestamp = datetime.now().strftime("%B_%d-%H_%M")
    filename = f"benchmark/results/{timestamp}_{model}.json"
    with open(filename, "w") as f:
        json.dump(
            {
                "model": model,
                "results": results,
                "additional_results": additional_results,
            },
            f,
            indent=2,
            cls=NpEncoder,
            default=str,
        )
    return filename


def get_benchmark_files():
    files = os.listdir("benchmark")
    return ["None"] + sorted(
        files, reverse=True
    )  # Add "None" as the first option and sort files in reverse order


def get_benchmark_results():
    files = [f for f in os.listdir("benchmark/results") if f.endswith(".json")]
    return ["None"] + sorted(
        files, reverse=True
    )  # Add "None" as the first option and sort files in reverse order


# Function to load the DataFrame
@st.cache_data
def load_data(yaml_file):
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)
        df = pd.DataFrame.from_dict(data)
        df["grade"] = ""
    return df


# Function to get ungraded items
def get_ungraded_items(df):
    return df[df["grade"].isnull() | (df["grade"] == "") | (df["grade"] == "None")]


# Function to parse JSON-like strings
def parse_json_like(s):
    try:
        return json.loads(s)
    except:
        return s


def custom_notification(message, duration=2):
    placeholder = st.empty()
    placeholder.info(message)
    time.sleep(duration)
    placeholder.empty()


def find_next_ungraded(df, current_index):
    ungraded = df[df["grade"].isnull() | (df["grade"] == "")].index
    next_ungraded = ungraded[ungraded > current_index]
    if len(next_ungraded) > 0:
        return int(next_ungraded[0])
    elif len(ungraded) > 0:
        return int(ungraded[0])
    else:
        return int(current_index)  # Return the current index if all tasks are graded


# Main app
def main():
    st.title("Benchmark App")

    # Initialize session state for grade update and selected index
    if "grade_updated" not in st.session_state:
        st.session_state.grade_updated = False
    if "selected_index" not in st.session_state:
        st.session_state.selected_index = 0

    st.sidebar.header("Select Model")
    model = st.sidebar.selectbox("Choose a model", options=LLMs, key="model_selector")
    benchmark = st.sidebar.selectbox(
        "Choose a benchmark", options=get_benchmark_files(), key="benchmark_selector"
    )
    if benchmark != "None":
        st.session_state.df = load_data(f"benchmark/{benchmark}")
    with st.sidebar.expander("Benchmark Settings"):
        st.sidebar.checkbox("Allow Visualization", value=False, key="allow_viz")
        st.sidebar.checkbox("Allow Retry", value=False, key="allow_retry")
    if st.sidebar.button("Run Benchmark"):
        # Clear the main screen
        with st.spinner(f"Running benchmark for {model}..."):
            # Change this later
            n_rows = len(st.session_state.df)
            results, additional_results = run_benchmark(
                st.session_state.df.head(n_rows), model
            )
            filename = save_benchmark_results(model, results, additional_results)
            st.toast(f"Benchmark completed and saved as {filename}")
            st.session_state.df.head(n_rows)[model] = results
            st.session_state.df.head(n_rows)[f"{model}_additional"] = additional_results
            st.rerun()

    # Move the benchmark file selection to the top of the sidebar
    st.sidebar.header("Select Results")
    selected_benchmark = st.sidebar.selectbox(
        "Choose a benchmark results file",
        options=get_benchmark_results(),
        key="results_benchmark_selector",
    )

    if selected_benchmark == "None":
        st.info(
            "Please run a new benchmark or select a benchmark file from the sidebar to view tasks and grade them.",
            icon="💡",
        )
        st.stop()

    # Load the selected benchmark file
    if selected_benchmark != "None":
        benchmark_data = load_benchmark_file(selected_benchmark)

        # Update the DataFrame with the loaded benchmark data
        model = selected_benchmark.split("_")[0]  # Extract model name from file name
        df = st.session_state.df.copy()  # Create a copy of the original DataFrame
        df[model] = benchmark_data["results"] + [None] * (
            len(df) - len(benchmark_data["results"])
        )
        df[f"{model}_additional"] = benchmark_data["additional_results"] + [None] * (
            len(df) - len(benchmark_data["additional_results"])
        )

        # Load grades from the benchmark file
        if "grades" in benchmark_data:
            df["grade"] = benchmark_data["grades"] + [None] * (
                len(df) - len(benchmark_data["grades"])
            )
        else:
            df["grade"] = [None] * len(df)

        # Load comments from the benchmark file
        if "comments" in benchmark_data:
            df["comment"] = benchmark_data["comments"] + [None] * (
                len(df) - len(benchmark_data["comments"])
            )
        else:
            df["comment"] = [None] * len(df)

        # Convert 'None' strings to None
        df["grade"] = df["grade"].replace("None", None)
        df["comment"] = df["comment"].replace("None", None)

        model = selected_benchmark.split("_")[0]
        timestamp = "_".join(selected_benchmark.split("_")[1:]).split(".")[0]
        st.success(f"Loaded benchmark results for {model} at {timestamp}")

        # Get ungraded items for this specific benchmark
        ungraded_df = get_ungraded_items(df)
        # Display selected row
        st.header("Selected Task")
        # Item selection in the main area
        selected_index = st.selectbox(
            "Choose an item to grade or review:",
            options=df.index.tolist(),
            index=st.session_state.selected_index,
            format_func=lambda x: format_task_option(x, df),
            key="task_selector",
        )

        # Update the session state with the selected index
        st.session_state.selected_index = selected_index
        selected_row = df.iloc[selected_index]
        # Current Grade and Grading in the same row
        st.subheader("Grading")
        col1, col2 = st.columns(2)

        with col1:
            current_grade = df.at[selected_index, "grade"]
            if pd.isna(current_grade) or current_grade == "":
                st.markdown(
                    "<div style='padding: 10px; border-radius: 5px; background-color: #f0f2f6; color: #31333F; text-align: center;'>"
                    "<span style='font-weight: bold;'>Current Grade:</span> Not graded yet"
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                grade_colors = {
                    "Correct": "#28a745",
                    "Partially Correct": "#ffc107",
                    "Incorrect": "#dc3545",
                    "Not Applicable": "#6c757d",
                    "Flag for Review": "#ffa500",
                }
                grade_color = grade_colors.get(
                    current_grade, "#6c757d"
                )  # Default to a neutral color if not found
                st.markdown(
                    f"<div style='padding: 10px; border-radius: 5px; background-color: {grade_color}; color: white; text-align: center;'>"
                    f"<span style='font-weight: bold;'>Current Grade:</span> {current_grade}"
                    "</div>",
                    unsafe_allow_html=True,
                )

        with col2:
            grade_options = [
                "",
                "Correct",
                "Partially Correct",
                "Incorrect",
                "Not Applicable",
                "Flag for Review",
            ]
            selected_grade = st.selectbox(
                "Update Grade",
                options=grade_options,
                index=grade_options.index(current_grade)
                if current_grade in grade_options
                else 0,
                key=f"grade_select_{selected_index}",
                label_visibility="collapsed",
            )

            current_comment = (
                df.at[selected_index, "comment"] if "comment" in df.columns else ""
            )
            comment = st.text_area(
                "Add a comment", value=current_comment, key=f"comment_{selected_index}"
            )

        # Display Evaluation and Response in an expander with columns
        with st.expander("Evaluation and Response", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Evaluation")
                eval_data = parse_json_like(selected_row["evaluation"])
                st.json(eval_data, expanded=True)

            with col2:
                st.subheader("Response")
                response_data = parse_json_like(selected_row[model])
                if isinstance(response_data, dict) and "result" in response_data:
                    st.json(response_data["result"], expanded=True)
                else:
                    st.write(selected_row[model])

        # Put additional info in another expander
        with st.expander("Additional Information"):
            additional_data = selected_row[f"{model}_additional"]
            if isinstance(additional_data, dict):
                st.write(
                    f"Task: {additional_data.get('task', 'N/A')} | Success: {additional_data.get('success', 'N/A')} | Only Text: {additional_data.get('only_text', 'N/A')} |\n\n Error: :red-background[{additional_data.get('error', 'N/A')}]"
                )
                if additional_data.get("execution_time", "N/A") != "N/A":
                    # Round to 2 decimal places
                    execution_time = round(
                        additional_data.get("execution_time", "N/A"), 2
                    )
                    st.write(f"Execution Time: {execution_time} seconds")
                st.json(
                    selected_row[["feed", "question", "task"]].to_dict(), expanded=True
                )
                st.write("LLM Response:")
                main_response = (
                    additional_data.get("llm_response", "N/A")
                    .split("```python")[1]
                    .split("```")[0]
                )
                st.code(main_response)
            else:
                st.write(additional_data)

        # Auto-update grade and comment when selection changes
        if selected_grade != current_grade or comment != current_comment:
            grade_or_comment_changed = update_grade(
                selected_benchmark,
                selected_index,
                selected_grade if selected_grade != "" else None,
                comment if comment != "" else None,
            )

            if grade_or_comment_changed:
                df.at[selected_index, "grade"] = (
                    selected_grade if selected_grade != "" else None
                )
                df.at[selected_index, "comment"] = comment if comment != "" else None

                # Update the session state
                st.session_state.df = df

                # Show custom notification
                custom_notification("Grade and/or comment updated successfully!")

                # Find the next ungraded task
                next_ungraded = find_next_ungraded(df, selected_index)
                if next_ungraded is not None:
                    st.session_state.selected_index = next_ungraded

        # Add back the expander DataFrame view
        with st.expander("Full DataFrame View"):
            st.dataframe(df)

        # New expander for comments
        with st.expander("All Comments"):
            comments_df = df[["task", "grade", "comment"]].dropna(subset=["comment"])
            if not comments_df.empty:
                for _, row in comments_df.iterrows():
                    st.markdown(f"**Task:** {row['task']}")
                    st.markdown(f"**Grade:** {row['grade']}")
                    st.markdown(f"**Comment:** {row['comment']}")
                    st.markdown("---")
            else:
                st.info("No comments have been entered yet.")

        # Move grade distribution to sidebar
        st.sidebar.subheader("Grade Distribution")
        grade_counts = df["grade"].value_counts().reset_index()
        grade_counts.columns = ["Grade", "Count"]

        # Add count of ungraded items
        ungraded_count = df["grade"].isnull().sum()
        ungraded_df = pd.DataFrame({"Grade": ["Ungraded"], "Count": [ungraded_count]})
        grade_counts = pd.concat([grade_counts, ungraded_df], ignore_index=True)

        # Define colors for each grade
        color_map = {
            "Correct": "green",
            "Partially Correct": "yellow",
            "Incorrect": "red",
            "Not Applicable": "gray",
            "Flag for Review": "orange",
            "Ungraded": "lightgray",
        }

        # Create horizontal bar chart
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.02)
        fig.add_trace(
            go.Bar(
                y=grade_counts["Grade"],
                x=grade_counts["Count"],
                orientation="h",
                marker_color=[
                    color_map.get(grade, "lightgray") for grade in grade_counts["Grade"]
                ],
                text=grade_counts["Count"],
                textposition="inside",
                hoverinfo="text",
                hovertext=[
                    f"{grade}: {count}"
                    for grade, count in zip(
                        grade_counts["Grade"], grade_counts["Count"]
                    )
                ],
            )
        )
        fig.update_layout(
            height=300,
            width=200,
            margin=dict(l=50, r=0, t=30, b=0),
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
        )
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)

        selected_grade = st.sidebar.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False},
            on_click=handle_plot_click,
        )

        st.sidebar.metric("Total Tasks", len(df))
        st.sidebar.metric("Ungraded Tasks", ungraded_count)

        # Count tasks without comments for specific grades
        tasks_needing_comments = df[
            (df["grade"].isin(["Incorrect", "Partially Correct", "Flag for Review"]))
            & (df["comment"].isnull() | (df["comment"] == ""))
        ].shape[0]
        st.sidebar.metric("Tasks Needing Comments", tasks_needing_comments)

        # Handle plot selection
        if st.session_state.get("selected_grade"):
            selected_grade_name = st.session_state.selected_grade
            if selected_grade_name == "Ungraded":
                filtered_df = df[df["grade"].isnull()]
            else:
                filtered_df = df[df["grade"] == selected_grade_name]

            st.header(f"Questions for grade: {selected_grade_name}")
            for _, row in filtered_df.iterrows():
                with st.expander(f"Task: {row['task']}"):
                    st.write(f"Question: {row['question']}")
                    st.write(f"Feed: {row['feed']}")
                    if not pd.isna(row["grade"]):
                        st.write(f"Grade: {row['grade']}")

        # Move this section to the bottom of the page
        add_vertical_space(3)
        st.markdown("---")
        st.subheader("Navigation and Shortcuts")

        # Create a container for the task icons
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                button(
                    "⬅️",
                    "Ctrl+ArrowLeft",
                    previous_task,
                    hint=True,
                    help="Previous Task",
                )
            with col2:
                button("➡️", "Ctrl+ArrowRight", next_task, hint=True, help="Next Task")
            with col3:
                button(
                    "🔍",
                    "Ctrl+ArrowUp",
                    next_ungraded_task,
                    hint=True,
                    help="Next Ungraded Task",
                )

        add_keyboard_shortcuts(
            {
                "Ctrl+ArrowRight": next_task,
                "Ctrl+ArrowLeft": previous_task,
                "Ctrl+ArrowUp": next_ungraded_task,
            }
        )


def load_benchmark_file(filename):
    with open(f"benchmark/results/{filename}", "r") as f:
        return json.load(f)


def save_benchmark_file(filename, data):
    with open(f"benchmark/results/{filename}", "w") as f:
        json.dump(data, f, indent=2, cls=NpEncoder, default=str)


def update_grade(filename, task_index, new_grade, new_comment):
    data = load_benchmark_file(filename)
    if "grades" not in data:
        data["grades"] = [None] * len(data["results"])
    if "comments" not in data:
        data["comments"] = [None] * len(data["results"])

    # Ensure the grades and comments lists are long enough
    while len(data["grades"]) <= task_index:
        data["grades"].append(None)
    while len(data["comments"]) <= task_index:
        data["comments"].append(None)

    old_grade = data["grades"][task_index]
    old_comment = data["comments"][task_index]
    data["grades"][task_index] = new_grade
    data["comments"][task_index] = new_comment
    save_benchmark_file(filename, data)

    return old_grade != new_grade or old_comment != new_comment


def handle_plot_click(trace, points, state):
    if points.point_inds:
        st.session_state.selected_grade = points.y[0]
        st.rerun()


def format_task_option(x, df):
    task = df.iloc[x]["task"]
    grade = df.iloc[x]["grade"]
    if pd.isna(grade) or grade == "":
        return f"R {x}: {task} (Ungraded)"
    else:
        return f"R {x}: {task} ({grade})"


def next_task():
    st.session_state.selected_index = (st.session_state.selected_index + 1) % len(
        st.session_state.df
    )


def previous_task():
    st.session_state.selected_index = (st.session_state.selected_index - 1) % len(
        st.session_state.df
    )


def next_ungraded_task():
    st.session_state.selected_index = find_next_ungraded(
        st.session_state.df, st.session_state.selected_index
    )


if __name__ == "__main__":
    main()
