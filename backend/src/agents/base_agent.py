import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from rdflib import Namespace
from src.ontology_manager import OntologyManager
from src.reasoner import Reasoner

log = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all Local Agents.
    Provides a common interface for enrichment and provenance.
    """
    def __init__(self, ontology_manager: OntologyManager, reasoner: Reasoner, agent_name: str):
        """
        Initializes the agent with access to ontology and reasoning tools.
        
        :param ontology_manager: The singleton OntologyManager instance.
        :param reasoner: The singleton Reasoner instance.
        :param agent_name: The name of the concrete agent (e.g., "PaperAgent").
        """
        self.ontology_manager = ontology_manager
        self.reasoner = reasoner
        self.agent_name = agent_name
        
        # Define and bind a provenance namespace for logging agent activity
        self.prov_ns = Namespace("http://example.org/provenance#")
        self.base_ns = self.ontology_manager.base_ns
        self.ontology_manager.graph.bind("prov", self.prov_ns)
        log.debug(f"[{self.agent_name}] Initialized.")

    @abstractmethod
    def identify_missing_info(self, query_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the reasoner's feedback (and user query) to find
        actionable, missing information relevant to this agent.
        
        :param query_feedback: The analysis dict from the Reasoner.
        :return: A dict of parameters for the fetch step (e.g., {'author_name': 'Andrew Ng'}).
        """
        pass

    @abstractmethod
    def fetch_external_data(self, missing_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch relevant information from external APIs based on the
        actionable info identified.
        
        :param missing_info: The output from identify_missing_info.
        :return: A list of result objects from the external API.
        """
        pass

    @abstractmethod
    def enrich_ontology(self, data: List[Dict[str, Any]]) -> None:
        """
        Insert new triples into the ontology based on fetched data,
        using the _add_with_provenance helper.
        
        :param data: The list of results from fetch_external_data.
        """
        pass

    def _add_with_provenance(self, subject_uri: str, predicate_uri: str, object_literal_or_uri: str, source_url: str):
        """
        A helper to add a triple and its associated provenance.
        
        This simple model attaches provenance to the subject of the new triple.
        e.g., :Paper123 :hasAuthor :Author456 .
              :Paper123 prov:addedBy "PaperAgent" .
              :Paper123 prov:source <https://api.openalex.org/W123> .
        
        :param subject_uri: Prefixed URI (e.g., ":MySubject")
        :param predicate_uri: Prefixed URI (e.g., ":hasName")
        :param object_literal_or_uri: Prefixed URI or a literal (e.g., ":MyObject" or '"A Name"')
        :param source_url: The external URL where the data came from.
        """
        try:
            # Add the main data triple
            self.ontology_manager.add_triple(subject_uri, predicate_uri, object_literal_or_uri)
            
            # Add provenance metadata triples attached to the subject
            self.ontology_manager.add_triple(subject_uri, "prov:addedBy", f'"{self.agent_name}"')
            self.ontology_manager.add_triple(subject_uri, "prov:source", f"<{source_url}>")
            
        except Exception as e:
            log.error(f"[{self.agent_name}] Failed to add triple {subject_uri} {predicate_uri} ...: {e}")

    def run_enrichment_cycle(self, query_feedback: Dict[str, Any]) -> bool:
        """
        Executes the full agent cycle: identify -> fetch -> enrich.
        This is the main entry point called by the Controller.
        
        :param query_feedback: The analysis dict from the Reasoner.
        :return: True if enrichment occurred, False otherwise.
        """
        log.info(f"[{self.agent_name}] Running enrichment cycle...")
        
        missing_info = self.identify_missing_info(query_feedback)
        if not missing_info:
            log.warning(f"[{self.agent_name}] No actionable missing info identified.")
            return False
            
        external_data = self.fetch_external_data(missing_info)
        if not external_data:
            log.warning(f"[{self.agent_name}] No external data found for: {missing_info}")
            return False
            
        log.info(f"[{self.agent_name}] Fetched {len(external_data)} items. Enriching ontology...")
        self.enrich_ontology(external_data)
        
        # Save the graph after a successful enrichment batch
        self.ontology_manager.save_graph()
        log.info(f"[{self.agent_name}] Enrichment complete. Graph saved.")
        return True