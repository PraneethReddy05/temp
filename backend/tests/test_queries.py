import pytest
import os
from src.controller import Controller
from src.ontology_manager import OntologyManager
from src.reasoner import Reasoner
from src.super_agent_basic import SuperAgentBasic

# Ensure paths are correct for running tests from project root
ONTOLOGY_PATH = "ontology/base_ontology.owl"
INSTANCES_PATH = "data/sample_instances.rdf"
CONFIG_PATH = "config/settings.yaml"

@pytest.fixture(scope="module")
def controller():
    """Fixture to create a single Controller instance for all tests."""
    # Check if config and data files exist before running tests
    if not all(os.path.exists(p) for p in [ONTOLOGY_PATH, INSTANCES_PATH, CONFIG_PATH]):
        pytest.skip("Missing test data or config files. Run from project root.")
        
    return Controller(config_path=CONFIG_PATH)

def test_ontology_loading(controller):
    """Test if the OntologyManager loaded the graph."""
    manager = controller.ontology_manager
    assert manager is not None
    assert len(manager.graph) > 0, "Graph should not be empty after loading."

def test_sparql_execution(controller):
    """Test direct SPARQL query execution via the Reasoner."""
    reasoner = controller.reasoner
    query = """
    PREFIX : <http://example.org/ontology#>
    SELECT ?s 
    WHERE { 
      ?s rdf:type :Paper .
    }
    """
    result = reasoner.execute_sparql(query)
    assert not result['bindings'] is None
    assert len(result['bindings']) == 3, "Should find 3 papers total."

def test_nl_to_sparql_mock(controller):
    """Test the SuperAgent's mock NL -> SPARQL translation."""
    agent = controller.super_agent
    nl_query = "List all papers written by Andrew Ng."
    sparql = agent.mock_generate_sparql(nl_query)
    
    assert "SELECT" in sparql
    assert ":Paper" in sparql
    assert ":hasAuthor" in sparql
    assert ":Andrew_Ng" in sparql

def test_gap_detection_logic(controller):
    """Test the Reasoner's analysis of an empty result."""
    reasoner = controller.reasoner
    # Query for a non-existent author
    empty_query = """
    PREFIX : <http://example.org/ontology#>
    SELECT ?paper 
    WHERE { 
      ?paper :hasAuthor :NonExistentAuthor .
    }
    """
    raw_result = reasoner.execute_sparql(empty_query)
    analysis = reasoner.analyze_query_result(raw_result, empty_query)
    
    assert analysis['is_empty'] == True
    assert analysis['status'] == "empty"
    assert ":hasAuthor" in analysis['mentioned_entities']
    assert ":NonExistentAuthor" in analysis['mentioned_entities']

def test_controller_e2e_success(controller):
    """Test the full end-to-end flow with a query that succeeds."""
    nl_query = "List all papers written by Andrew Ng."
    result = controller.handle_user_query(nl_query)
    
    assert result['status'] == "success"
    assert result['is_empty'] == False
    assert len(result['raw_result']['bindings']) == 2
    assert "Paper_DL_2020" in str(result['raw_result']['bindings'])

def test_controller_e2e_refinement_flow(controller):
    """
    Test the full flow with a query that fails first and triggers refinement.
    
    NOTE: This test relies on the MOCK refinement logic.
    Our mock 'generate' produces :Andrew_Ng.
    Our mock 'refine' turns :Andrew_Ng -> :A_Ng (which is not in the data).
    So, the *final* result should be empty, but we can trace the flow.
    """
    
    # To test refinement, we need a query that *fails* but *looks like*
    # the one that triggers refinement.
    
    # Let's temporarily override the mock generator for this one test
    original_generator = controller.super_agent.generate_sparql
    
    # This query will fail (return 0 results)
    bad_query_sparql = """
    PREFIX : <http://example.org/ontology#>
    SELECT ?paper 
    WHERE { 
      ?paper rdf:type :Paper .
      ?paper :hasAuthor :Andrew_Ng .
      ?paper :hasTopic :NonExistentTopic .
    }
    """
    
    # Mock the generator to return this bad query
    controller.super_agent.generate_sparql = lambda query: bad_query_sparql
    
    nl_query = "A query that will fail"
    result = controller.handle_user_query(nl_query)
    
    # Restore original generator
    controller.super_agent.generate_sparql = original_generator
    
    # Check that refinement was triggered
    assert 'refined_query' in result
    assert result['status'] == "empty" # The refined query also fails
    assert result['original_query'] == bad_query_sparql
    # Check that the mock refinement logic ran
    assert ":A_Ng" in result['refined_query']