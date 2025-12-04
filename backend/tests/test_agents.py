import pytest
from unittest.mock import MagicMock, patch
from src.agents.paper_agent import PaperAgent
from src.agents.author_agent import AuthorAgent
from src.agents.concept_agent import ConceptAgent

# --- Mock Data ---

MOCK_PAPER_DATA = [
    {
        "id": "https://openalex.org/W123",
        "display_name": "A paper about AI",
        "authorships": [
            {
                "author": {
                    "id": "https://openalex.org/A456",
                    "display_name": "Andrew Ng"
                }
            }
        ]
    }
]

MOCK_AUTHOR_DATA = [
    {
        "id": "https://openalex.org/A456",
        "display_name": "Andrew Ng",
        "last_known_institution": {
            "id": "https://openalex.org/I789",
            "display_name": "Stanford University"
        }
    }
]

# --- Fixtures ---

@pytest.fixture
def mock_ontology():
    """Mocks the OntologyManager to track added triples."""
    mock_om = MagicMock()
    mock_om.added_triples = []
    
    # Mock the add_triple method to just record the call
    def simple_add(s, p, o):
        mock_om.added_triples.append((s, p, o))
        
    mock_om.add_triple = simple_add
    
    # Mock the query_graph method for the test_paper_agent_adds_triples
    def simple_query(query):
        if "ASK { :W123 :hasAuthor :A456 }" in query:
            return any(t == (":W123", ":hasAuthor", ":A456") for t in mock_om.added_triples)
        return False
        
    mock_om.query_graph.side_effect = simple_query
    
    return mock_om

@pytest.fixture
def mock_reasoner():
    """Mocks the Reasoner."""
    return MagicMock()

# --- Tests ---

def test_paper_agent_enrich_ontology(mock_ontology, mock_reasoner):
    """
    Test if the PaperAgent correctly adds triples for a paper and its author.
    """
    agent = PaperAgent(mock_ontology, mock_reasoner)
    
    # Use patch to mock the provenance helper (we test it implicitly)
    with patch.object(agent, '_add_with_provenance', side_effect=mock_ontology.add_triple):
        agent.enrich_ontology(MOCK_PAPER_DATA)

    # Check that triples were added
    triples = mock_ontology.added_triples
    assert (":W123", "rdf:type", ":Paper") in triples
    assert (":W123", "rdfs:label", '"A paper about AI"') in triples
    assert (":W123", ":hasAuthor", ":A456") in triples
    assert (":A456", "rdf:type", ":Author") in triples
    assert (":A456", "rdfs:label", '"Andrew Ng"') in triples

def test_author_agent_enrich_ontology(mock_ontology, mock_reasoner):
    """
    Test if the AuthorAgent correctly adds triples for an author and affiliation.
    """
    agent = AuthorAgent(mock_ontology, mock_reasoner)
    
    with patch.object(agent, '_add_with_provenance', side_effect=mock_ontology.add_triple):
        agent.enrich_ontology(MOCK_AUTHOR_DATA)
        
    triples = mock_ontology.added_triples
    assert (":A456", "rdf:type", ":Author") in triples
    assert (":A456", "rdfs:label", '"Andrew Ng"') in triples
    assert (":A456", ":affiliatedWith", ":I789") in triples
    assert (":I789", "rdf:type", ":Institution") in triples
    assert (":I789", "rdfs:label", '"Stanford University"') in triples

def test_author_agent_identify_missing_info(mock_ontology, mock_reasoner):
    """
    Test the agent's ability to parse feedback.
    """
    agent = AuthorAgent(mock_ontology, mock_reasoner)
    feedback = {
        "mentioned_entities": [":Paper", ":hasAuthor", ":Andrew_Ng"]
    }
    
    missing_info = agent.identify_missing_info(feedback)
    assert missing_info == {"author_name": "Andrew Ng"}

def test_agent_identify_no_info(mock_ontology, mock_reasoner):
    """
    Test that agents return empty dicts when no relevant info is found.
    """
    author_agent = AuthorAgent(mock_ontology, mock_reasoner)
    feedback = {"mentioned_entities": [":Paper", ":hasTopic"]}
    
    missing_info = author_agent.identify_missing_info(feedback)
    assert missing_info == {}