from src.agents.paper_agent import PaperAgent
from src.agents.author_agent import AuthorAgent
from src.agents.concept_agent import ConceptAgent

"""
A simple registry mapping string keys (entity types or properties)
to the Agent class responsible for handling them.

The Controller uses this to dispatch tasks.
"""
AGENT_REGISTRY = {
    # Entity Types
    "Paper": PaperAgent,
    "Author": AuthorAgent,
    "Concept": ConceptAgent,
    
    # Properties (can also trigger agents)
    "hasAuthor": AuthorAgent,
    "hasConcept": ConceptAgent,
    "affiliatedWith": AuthorAgent,
}