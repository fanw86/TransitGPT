import yaml
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from functools import lru_cache
from utils.constants import FEW_SHOT_EXAMPLES_FILE

@lru_cache(maxsize=None)
def load_yaml_examples(yaml_file: str) -> Dict[str, Dict]:
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)

class FewShotGenerator:
    def __init__(self):
        self.examples = load_yaml_examples(FEW_SHOT_EXAMPLES_FILE)
        self.vectorizer = TfidfVectorizer()
        self.all_examples_formatted = [f"{ex['question']}\n{ex['answer']}" for ex in self.examples.values()]
        self.example_vectors = self.vectorizer.fit_transform(self.all_examples_formatted)

    def select_relevant_examples(self, query: str, num_examples: int = 3) -> List[Dict]:
        task_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(task_vector, self.example_vectors).flatten()
        top_indices = np.argsort(similarities)[-num_examples:][::-1]
        return [list(self.examples.values())[i] for i in top_indices]
    
    def format_examples(self, examples: List[Dict]) -> str:
        formatted_examples = ["<examples>"]
        for example in examples:
            formatted_example = "<example>\n"
            formatted_example += f"<task>\n{example['question']}\n</task>\n"
            formatted_example += f"<solution>\n\n{example['answer']}\n\n</solution>\n"
            formatted_example += "</example>"
            formatted_examples.append(formatted_example)
        formatted_examples.append("</examples>")
        return "\n".join(formatted_examples)
    
    def get_few_shot_prompt(self, query:str):
        relevant_examples = self.select_relevant_examples(query)
        FEW_SHOT_PROMPT = "## Sample Code Generation for Tasks\n\n Here are few relevant examples that help you discern the logic\n"
        FEW_SHOT_PROMPT = FEW_SHOT_PROMPT + "\n\n" + self.format_examples(relevant_examples)
        return FEW_SHOT_PROMPT