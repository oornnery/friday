from agno.knowledge import Knowledge


def get_knowledge_base() -> Knowledge:
    """Returns a configured Knowledge base."""
    # This can be expanded to PDFKnowledgeBase, WebsiteKnowledgeBase, etc.
    # For now, it's a base class that can be configured with vector dbs if needed.
    return Knowledge(
        # vector_db=...,
        # num_documents=5,
    )
