import logging
import re
from typing import Dict, Any, List
from src.ontology_manager import OntologyManager

log = logging.getLogger(__name__)

class Reasoner:
    """
    Executes SPARQL queries, detects missing data, and returns structured results.
    """
    def __init__(self, ontology_manager: OntologyManager):
        """
        Attach the OntologyManager instance.
        
        :param ontology_manager: An initialized OntologyManager.
        """
        self.ontology_manager = ontology_manager
        log.info("Reasoner initialized.")

    def execute_sparql(self, sparql_query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run query and return a dictionary with bindings.
        
        :param sparql_query: The SPARQL query string.
        :return: A dictionary structured as {"bindings": [...]}.
        """
        bindings = self.ontology_manager.query_graph(sparql_query)
        return {"bindings": bindings}

    def analyze_query_result(self, result: Dict[str, list], query: str) -> Dict[str, Any]:
        """
        Check for missing or empty bindings and package the final response.
        
        :param result: The raw result from execute_sparql.
        :param query: The SPARQL query that produced the result.
        :return: A dictionary with status, data, and gap analysis.
        """
        is_empty = not result.get("bindings")
        missing_entities = []
        
        if is_empty:
            log.warning(f"Query returned no results. Analyzing query for entities.")
            missing_entities = self.get_mentioned_entities(query)
            
        return {
            "status": "success" if not is_empty else "empty",
            "is_empty": is_empty,
            "mentioned_entities": missing_entities,
            "raw_result": result
        }

    def get_mentioned_entities(self, sparql_query: str) -> List[str]:
        """
        A simple (naive) parser to identify prefixed entities (e.g., :Class, :property)
        mentioned in the query. This helps the Super-Agent refine its query.
        
        :param sparql_query: The SPARQL query string.
        :return: A list of mentioned prefixed names.
        """
        # This regex finds terms like :Something or :another_thing
        # It's a basic implementation for Phase 1
        try:
            terms = re.findall(r":([a-zA-Z0-9_]+)", sparql_query)
            # Return unique terms with the prefix
            unique_terms = sorted(list(set([f":{t}" for t in terms])))
            log.debug(f"Found mentioned entities in query: {unique_terms}")
            return unique_terms
        except Exception as e:
            log.error(f"Error parsing entities from query: {e}")
            return []