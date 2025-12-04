import pytest
import json
from unittest.mock import MagicMock, patch
from src.ontology_manager import OntologyManager
from src.super_agent.super_agent_advanced import SuperAgentAdvanced
from src.super_agent.schema_manager import SchemaManager

# --- Mocks and Fixtures ---

@pytest.fixture
def mock_ontology_manager():
    """Mocks the OntologyManager and its graph."""
    mock_om = MagicMock(spec=OntologyManager)
    mock_om.graph = MagicMock()
    mock_om.base_ns = MagicMock()
    mock_om.base_ns.__getitem__.side_effect = lambda key: f"http://example.org/ontology#{key}"
    
    # Mock namespace manager for _get_uri
    mock_ns_manager = MagicMock()
    mock_ns_manager.namespace.return_value = {"int": "http://www.w3.org/2001/XMLSchema#int"}
    mock_om.graph.namespace_manager = mock_ns_manager
    
    return mock_om

@pytest.fixture
def super_agent(mock_ontology_manager):
    """Fixture for the SuperAgentAdvanced, patching the LLM client."""
    # Patch the OpenAI client in the __init__
    with patch("src.super_agent.super_agent_advanced.OpenAI") as mock_openai:
        mock_openai_client = MagicMock()
        mock_openai.return_value = mock_openai_client
        
        agent = SuperAgentAdvanced(
            llm_api_key="sk-test-key",
            ontology_manager=mock_ontology_manager
        )
        # Attach the mock client so we can control it in tests
        agent.mock_llm_client = mock_openai_client
        return agent

# --- SchemaManager Tests ---

def test_schema_manager_add_class(mock_ontology_manager):
    manager = SchemaManager(mock_ontology_manager)
    manager.add_class(":MyTestClass", parent=":ExistingClass", label="My Test Class")
    
    # Check if graph.add was called with the correct triples
    calls = mock_ontology_manager.graph.add.call_args_list
    assert len(calls) == 3
    # Note: This checks the content of the tuples passed to graph.add
    assert "MyTestClass" in str(calls[0])
    assert "type" in str(calls[0])
    assert "Class" in str(calls[0])
    
    assert "MyTestClass" in str(calls[1])
    assert "subClassOf" in str(calls[1])
    assert "ExistingClass" in str(calls[1])
    
    assert "My Test Class" in str(calls[2])

def test_schema_manager_add_object_property(mock_ontology_manager):
    manager = SchemaManager(mock_ontology_manager)
    manager.add_object_property(":hasTestProp", domain=":MyTestClass", range_=":OtherClass")
    
    calls = mock_ontology_manager.graph.add.call_args_list
    assert len(calls) == 4
    assert "hasTestProp" in str(calls[0])
    assert "ObjectProperty" in str(calls[0])
    assert "domain" in str(calls[1])
    assert "range" in str(calls[2])

# --- SuperAgentAdvanced Tests ---

def test_refine_complex_query(super_agent):
    """Test if the agent calls the LLM and parses the refinement JSON."""
    
    # Mock the LLM's response
    mock_llm_response = MagicMock()
    mock_llm_response.choices = [MagicMock()]
    mock_llm_response.choices[0].message.content = json.dumps({
        "sparql": "SELECT ?s WHERE { ?s a :Thing }",
        "confidence": 0.9,
        "explanation": "Used a broader query."
    })
    super_agent.mock_llm_client.chat.completions.create.return_value = mock_llm_response
    
    result = super_agent.refine_complex_query(
        "list things", "SELECT ?s WHERE { ?s a :Nothing }", {}
    )
    
    assert result["confidence"] == 0.9
    assert "SELECT ?s WHERE" in result["sparql"]
    
    # Check that the system prompt was loaded and used
    call_args = super_agent.mock_llm_client.chat.completions.create.call_args
    assert "You are an expert SPARQL" in call_args[1]["messages"][0]["content"]

def test_propose_schema_update(super_agent):
    """Test if the agent calls the LLM and parses the schema proposal JSON."""
    
    # Mock the LLM's response
    mock_response_json = {
        "add_class": [{"name": "Grant", "parent": "owl:Thing", "label": "Grant"}],
        "add_object_property": [{"name": "hasFunding", "domain": ":Paper", "range": ":Grant", "label": "has funding"}]
    }
    mock_llm_response = MagicMock()
    mock_llm_response.choices = [MagicMock()]
    mock_llm_response.choices[0].message.content = json.dumps(mock_response_json)
    super_agent.mock_llm_client.chat.completions.create.return_value = mock_llm_response

    result = super_agent.propose_schema_update("papers and their funding")
    
    assert len(result["add_class"]) == 1
    assert result["add_class"][0]["name"] == "Grant"
    assert result["add_object_property"][0]["name"] == "hasFunding"
    
    # Check that the system prompt was loaded and used
    call_args = super_agent.mock_llm_client.chat.completions.create.call_args
    assert "You are an expert Ontology Engineer" in call_args[1]["messages"][0]["content"]

def test_apply_schema_update(super_agent, mock_ontology_manager):
    """Test if the agent correctly calls SchemaManager methods."""
    
    proposal = {
        "add_class": [{"name": "Grant", "parent": "owl:Thing", "label": "Grant"}],
        "add_object_property": [{"name": "hasFunding", "domain": ":Paper", "range": ":Grant", "label": "has funding"}]
    }
    
    # Spy on the schema_manager methods
    super_agent.schema_manager.add_class = MagicMock()
    super_agent.schema_manager.add_object_property = MagicMock()
    super_agent.schema_manager.save = MagicMock()
    
    super_agent.apply_schema_update(proposal)
    
    # Check that the schema manager was called with the correct arguments
    super_agent.schema_manager.add_class.assert_called_with("Grant", "owl:Thing", "Grant")
    super_agent.schema_manager.add_object_property.assert_called_with(
        "hasFunding", ":Paper", ":Grant", "has funding"
    )
    super_agent.schema_manager.save.assert_called_once()