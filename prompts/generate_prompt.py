import time
from utils.helper import list_files_in_zip
from prompts.all_prompts import (
    TASK_KNOWLEDGE,
    BASE_PROMPT,
    BASE_GTFS_FEED_DATATYPES,
    TASK_INSTRUCTION,
    EXAMPLE_CODE,
    TASK_TIPS,
)
from prompts.gtfs_file_field_type import GTFS_FILE_FIELD_TYPE_MAPPING
from utils.gtfs_loader import GTFSLoader
from functools import lru_cache

@lru_cache(maxsize=None)
def generate_system_prompt(feed: GTFSLoader) -> str:# -> Any | str:
    print(f"FEED OBJECT: {feed}")
    files = feed.file_list
    FILE_INFO = """\n\n## Sample from the feed:\n"""
    distance_unit = feed.distance_unit
    distance_unit = '`Meters`' if distance_unit == 'm' else '`Kilometers`'
    GTFS_FEED_DATATYPES = BASE_GTFS_FEED_DATATYPES.format(distance_unit=distance_unit)
    for file_name in files:
        try:
            file = file_name.split('.txt')[0]
            df = getattr(feed, file)
            df_string = df.head().to_csv(index=False).replace("\n", "")
            FILE_INFO += f"### {file_name} (feed.{file})\n"
            FILE_INFO += df_string + "\n"
            if file_name in GTFS_FILE_FIELD_TYPE_MAPPING:
                GTFS_FEED_DATATYPES += f"{file_name}:\n"
                for field in df.columns:
                    if field in GTFS_FILE_FIELD_TYPE_MAPPING[file_name]:
                        # print(f"{file} {field}")
                        if len(df[field].unique()) >= 1:
                            GTFS_FEED_DATATYPES += (
                                f"\t- {field}: {GTFS_FILE_FIELD_TYPE_MAPPING[file_name][field]}\n"
                            )
                        else:
                            GTFS_FEED_DATATYPES += f"\t- {field}: {df[field].dtype}\n"
                    # else:
                    #     print(f"Field {field} not found in {file_name}")
        except Exception as e:
            print(f"Failed to generate prompt for {file_name}: {e}")
            continue
        
    print(f"Prompt generated successfully: {time.ctime()}")
    final_prompt = (
        BASE_PROMPT
        + TASK_KNOWLEDGE
        + GTFS_FEED_DATATYPES
        + FILE_INFO
        + TASK_INSTRUCTION
        + TASK_TIPS
        + EXAMPLE_CODE
    )

    with open("prompts/generated_prompt.md", "w", encoding="utf-8") as f:
        f.write(final_prompt)
    return final_prompt
