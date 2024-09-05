from sklearn.feature_extraction.text import TfidfVectorizer

def generate_prompt(documents, threshold=0.1):
    """
    Generate prompts based on the given documents and filter relevant terms using TF-IDF.

    :param documents: List of documents (strings)
    :param threshold: TF-IDF score threshold for filtering relevant terms
    :return: List of relevant terms with their TF-IDF scores
    """
    # Initialize the TF-IDF Vectorizer
    vectorizer = TfidfVectorizer()

    # Fit and transform the documents
    tfidf_matrix = vectorizer.fit_transform(documents)

    # Get feature names (terms)
    terms = vectorizer.get_feature_names_out()

    # Filter relevant terms
    relevant_terms = []
    for doc_idx, doc in enumerate(tfidf_matrix):
        for term_idx, score in zip(doc.indices, doc.data):
            if score > threshold:
                relevant_terms.append((terms[term_idx], score))

    return relevant_terms

# Example usage
if __name__ == "__main__":
    documents = [
        "This is a sample document.",
        "This document is another example.",
        "TF-IDF is used to find relevant terms."
    ]
    relevant_terms = generate_prompt(documents, threshold=0.1)
    for term, score in relevant_terms:
        print(f"Term: {term}, Score: {score}")