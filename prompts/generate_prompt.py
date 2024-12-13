import time
import yaml
import streamlit as st
from prompts.all_prompts import (
    GTFS_STRUCTURE,
    BASE_PROMPT,
    BASE_GTFS_FEED_DATATYPES,
    TASK_INSTRUCTION,
    TASK_INSTRUCTION_VIZ,
    TASK_TIPS,
    VISUALIZATION_TIPS,
)
from prompts.gtfs_file_field_type import GTFS_FILE_FIELD_TYPE_MAPPING
from gtfs_agent.gtfs_loader import GTFSLoader
from functools import lru_cache
from utils.constants import (
    FEW_SHOT_EXAMPLES_FILE,
    FEW_SHOT_EXAMPLES_FILE_VIZ,
    FEW_SHOT_EXAMPLE_LIMIT,
    PROMPT_OUTPUT_LOC,
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rich import print as rich_print


@lru_cache(maxsize=None)
def load_yaml_examples(yaml_file):
    with open(yaml_file, "r") as file:
        return yaml.safe_load(file)

def TFIDF_similarity(examples, query):
    # Create a list of all examples
    all_examples = [f"{ex['question']}\n{ex['answer']}" for ex in examples.values()]
    # Add the query to the list
    all_texts = [query] + all_examples
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer().fit_transform(all_texts)
    cosine_similarities = cosine_similarity(vectorizer[0:1], vectorizer[1:]).flatten()
    return cosine_similarities

@st.cache_resource(show_spinner="Loading sentence transformer...", ttl=3600)
def load_sentence_transformer():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource(show_spinner="Embedding examples...", ttl=3600)
def embed_examples(examples):
    model = load_sentence_transformer()
    example_queries = [f"{ex['question']}" for ex in examples.values()]
    return model.encode(example_queries)

def SentenceTransformer_similarity(examples, query):
    model = load_sentence_transformer()
    examples_embeddings = embed_examples(examples)
    query_embedding = model.encode(query)
    cosine_similarities = cosine_similarity([query_embedding], examples_embeddings).flatten()
    return cosine_similarities

def select_relevant_examples(query, examples, n=FEW_SHOT_EXAMPLE_LIMIT, method = "tfidf", threshold=0.25):
    # Create a list of all examples
    if method == "tfidf":
        cosine_similarities = TFIDF_similarity(examples, query)
    elif method == "sentence_transformer":
        cosine_similarities = SentenceTransformer_similarity(examples, query)

    # Filter examples based on threshold and get top n
    relevant_indices = [
        i for i, score in enumerate(cosine_similarities) if score > threshold
    ]
    relevant_indices.sort(key=lambda i: cosine_similarities[i], reverse=True)
    top_indices = relevant_indices[:n]

    return [list(examples.values())[i] for i in top_indices]


def generate_dynamic_few_shot(query, method, allow_viz, n=3):
    examples = load_yaml_examples(
        FEW_SHOT_EXAMPLES_FILE_VIZ if allow_viz else FEW_SHOT_EXAMPLES_FILE
    )
    relevant_examples = select_relevant_examples(query, examples, n, method)
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
    FILE_INFO = "\n\n## Sample from the feed: \n The following is a sample from the feed, showcasing the first five lines from each file:\n\n"
    GTFS_FEED_DATATYPES = BASE_GTFS_FEED_DATATYPES.format(distance_unit=distance_unit)

    for file_name in file_list:
        try:
            file = file_name.split(".txt")[0]
            df = getattr(feed, file)
            df_string = df.head(3).to_markdown(index=False)

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
                GTFS_FEED_DATATYPES = GTFS_FEED_DATATYPES.replace(
                    "GTFS_DISTANCE_UNITS", distance_unit
                )
        except Exception as e:
            print(f"Failed to generate prompt for {file_name}: {e}")
            continue

    return FILE_INFO, GTFS_FEED_DATATYPES


def generate_system_prompt(loader: GTFSLoader, allow_viz: bool = False) -> str:
    distance_unit = loader.distance_unit
    GTFS = loader.gtfs
    feed = loader.feed
    file_list = loader.file_list
    distance_unit = "`Meters`" if distance_unit == "m" else "`Kilometers`"
    FILE_INFO, GTFS_FEED_DATATYPES = generate_fileinfo_dtypes(
        feed, file_list, distance_unit
    )
    rich_print(
        f"[bold green]Prompt generated[/bold green] for [cyan]{GTFS}[/cyan] with distance units [yellow]{distance_unit}[/yellow]: [magenta]{time.ctime()}[/magenta] and Viz: [blue]{allow_viz}[/blue]"
    )

    # Choose the appropriate task instruction based on allow_viz
    task_instruction = TASK_INSTRUCTION_VIZ if allow_viz else TASK_INSTRUCTION

    final_prompt = (
        BASE_PROMPT
        + GTFS_STRUCTURE
        + GTFS_FEED_DATATYPES
        + FILE_INFO
        + task_instruction
        + TASK_TIPS
    )

    # Add visualization tips if allow_viz is True
    if allow_viz:
        final_prompt += VISUALIZATION_TIPS

    with open(PROMPT_OUTPUT_LOC, "w", encoding="utf-8") as f:
        f.write(final_prompt)
    return final_prompt
