import time
import yaml
from prompts.all_prompts import (
    TASK_KNOWLEDGE,
    BASE_PROMPT,
    BASE_GTFS_FEED_DATATYPES,
    TASK_INSTRUCTION,
    TASK_TIPS,
)
from prompts.gtfs_file_field_type import GTFS_FILE_FIELD_TYPE_MAPPING
from utils.gtfs_loader import GTFSLoader
from functools import lru_cache
from utils.constants import FEW_SHOT_EXAMPLES_FILE
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@lru_cache(maxsize=None)
def load_yaml_examples(yaml_file):
    with open(yaml_file, "r") as file:
        return yaml.safe_load(file)


def select_relevant_examples(query, examples, n=3, threshold=0.1):
    # Create a list of all examples
    all_examples = [f"{ex['question']}\n{ex['answer']}" for ex in examples.values()]
    # Add the query to the list
    all_texts = [query] + all_examples
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer().fit_transform(all_texts)
    # Compute cosine similarity
    cosine_similarities = cosine_similarity(vectorizer[0:1], vectorizer[1:]).flatten()
    
    # Filter examples based on threshold and get top n
    relevant_indices = [i for i, score in enumerate(cosine_similarities) if score > threshold]
    relevant_indices.sort(key=lambda i: cosine_similarities[i], reverse=True)
    top_indices = relevant_indices[:n]

    return [list(examples.values())[i] for i in top_indices]


def generate_dynamic_few_shot(query, n=3):
    examples = load_yaml_examples(FEW_SHOT_EXAMPLES_FILE)
    relevant_examples = select_relevant_examples(query, examples, n)
    examples = ["<examples>"]
    for ex in relevant_examples:
        example = "<example>\n"
        example += f"<task>\n{ex['question']}\n</task>\n"
        example += f"<solution>\n\n{ex['answer']}\n\n</solution>\n"
        example += "</example>"
        examples.append(example)
    examples.append("</examples>")
    return "\n".join(examples)


@lru_cache(maxsize=None)
def yaml_to_examples(yaml_file: str) -> str:
    # Load the YAML file
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)

    examples = ["<examples>"]
    for key, value in data.items():
        example = "<example>\n"
        example += f"<task>\n{value['question']}\n</task>\n"
        example += f"<solution>\n\n{value['answer']}\n\n</solution>\n"
        example += "</example>"
        examples.append(example)

    examples.append("</examples>")
    return "\n".join(examples)


def generate_fileinfo_dtypes(feed: GTFSLoader, file_list, distance_unit: str):
    FILE_INFO = "\n\n## Sample from the feed:\n\n"
    GTFS_FEED_DATATYPES = BASE_GTFS_FEED_DATATYPES.format(distance_unit=distance_unit)

    for file_name in file_list:
        try:
            file = file_name.split(".txt")[0]
            df = getattr(feed, file)
            df_string = df.head(3).to_html(index=False)

            FILE_INFO += f"### {file_name} (feed.{file})\n<feed-sample>\n"
            FILE_INFO += df_string + "\n</feed-sample>\n\n"

            if file_name in GTFS_FILE_FIELD_TYPE_MAPPING:
                GTFS_FEED_DATATYPES += f"### {file_name}\n\n<data-type>\n\n"
                for field in df.columns:
                    if field in GTFS_FILE_FIELD_TYPE_MAPPING[file_name]:
                        if len(df[field].unique()) >= 1:
                            GTFS_FEED_DATATYPES += f"- `{field}`: {GTFS_FILE_FIELD_TYPE_MAPPING[file_name][field]}\n"
                        else:
                            GTFS_FEED_DATATYPES += f"- `{field}`: {df[field].dtype}\n"
                GTFS_FEED_DATATYPES += "\n</data-type>\n\n"
        except Exception as e:
            print(f"Failed to generate prompt for {file_name}: {e}")
            continue

    return FILE_INFO, GTFS_FEED_DATATYPES


def generate_system_prompt(loader: GTFSLoader) -> str:
    distance_unit = loader.distance_unit
    GTFS = loader.gtfs
    feed = loader.feed
    file_list = loader.file_list
    distance_unit = "`Meters`" if distance_unit == "m" else "`Kilometers`"
    FILE_INFO, GTFS_FEED_DATATYPES = generate_fileinfo_dtypes(
        feed, file_list, distance_unit
    )
    # EXAMPLE_CODE = "## Sample Code Generation for Tasks\n\n Here are few examples that help you discern the logic\n"
    # EXAMPLE_CODE = EXAMPLE_CODE + "\n\n" + yaml_to_examples(FEW_SHOT_EXAMPLES_FILE)
    print(
        f"Prompt generated for {GTFS} with distance units {distance_unit}: {time.ctime()}"
    )

    final_prompt = (
        BASE_PROMPT
        + TASK_KNOWLEDGE
        + GTFS_FEED_DATATYPES
        + FILE_INFO
        + TASK_INSTRUCTION
        + TASK_TIPS
        # + EXAMPLE_CODE
    )

    with open("prompts/generated_prompt.md", "w", encoding="utf-8") as f:
        f.write(final_prompt)
    return final_prompt
