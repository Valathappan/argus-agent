from config.llm import get_agent_model

REWRITE_PROMPT = """Rewrite the user's question as a short search query for a argus knowledge base.
Keep the key argus terms, expand abbreviations, and drop filler words.
Return only the search query.

Question: {question}"""


def rewrite_query(question: str) -> str:
    response = get_agent_model().invoke(REWRITE_PROMPT.format(question=question))
    return response.text.strip().strip('"')
