import logging
import re
from typing import Dict, Any, List
from src.ontology_manager import OntologyManager

log = logging.getLogger(__name__)

class Reasoner:
    """
    The Final Authority.
    Executes SPARQL queries against the validated ontology, detects missing data,
    and formats the authoritative answer.
    """
    def __init__(self, ontology_manager: OntologyManager):
        """
        Attach the OntologyManager instance.
        
        :param ontology_manager: An initialized OntologyManager containing the VALIDATED graph.
        """
        self.ontology_manager = ontology_manager
        log.info("Reasoner initialized.")

    def execute_sparql(self, sparql_query: str) -> Dict[str, Any]:
        """
        Executes a SPARQL query against the current (validated) graph.
        This is the ONLY method allowed to return answers to the Controller/User.
        
        :param sparql_query: The SPARQL query string.
        :return: A structured dictionary containing success status and bindings.
        """
        try:
            # Execute query via the manager
            bindings = self.ontology_manager.query_graph(sparql_query)
            
            # Helper to convert RDFLib terms to simple strings if needed, 
            # though ontology_manager.query_graph usually handles asdict().
            # We explicitly structure the response here for consistency.
            formatted_bindings = []
            for row in bindings:
                # row is expected to be a dict from ontology_manager.query_graph
                formatted_bindings.append(row)

            return {
                "status": "success",
                "raw_result": {"bindings": formatted_bindings},
                "count": len(formatted_bindings)
            }
        except Exception as e:
            log.error(f"Reasoner execution error: {e}")
            return {
                "status": "error", 
                "message": str(e), 
                "raw_result": {"bindings": []}
            }

    def analyze_query_result(self, result: Dict[str, Any], sparql_query: str) -> Dict[str, Any]:
        """
        Analyzes the result to determine if it's empty or needs enrichment.
        This drives the Controller's decision to escalate to Agents or Super-Agent.
        
        :param result: The result dictionary from execute_sparql.
        :param sparql_query: The query string (used for gap analysis).
        :return: A dictionary with 'is_empty', 'missing_terms', and original data.
        """
        bindings = result.get("raw_result", {}).get("bindings", [])
        is_empty = len(bindings) == 0
        
        missing_terms = []
        if is_empty:
            log.warning(f"Query returned no results. Analyzing query for entities.")
            missing_terms = self._get_mentioned_entities(sparql_query)
            
        return {
            "status": result.get("status", "unknown"),
            "is_empty": is_empty,
            "bindings": bindings,          # The authoritative answer data
            "missing_terms": missing_terms, # Hints for the Controller/Agents
            "raw_result": result.get("raw_result")
        }

    def _get_mentioned_entities(self, sparql_query: str) -> List[str]:
        """
        Internal helper to identify prefixed entities (e.g., :Class, :property)
        in a failed query. This helps the Controller dispatch the right agents.
        
        :param sparql_query: The SPARQL query string.
        :return: A list of unique mentioned prefixed names.
        """
        try:
            # Basic regex to find :Term
            terms = re.findall(r":([a-zA-Z0-9_]+)", sparql_query)
            # Return unique terms with the prefix
            unique_terms = sorted(list(set([f":{t}" for t in terms])))
            
            if unique_terms:
                log.debug(f"Found mentioned entities in query: {unique_terms}")
            
            return unique_terms
        except Exception as e:
            log.error(f"Error parsing entities from query: {e}")
            return []

    def validate_graph(self) -> bool:
        """
        Placeholder for explicit consistency checking logic if needed
        outside of the ValidationManager transaction loop.
        In Stage 4, most validation happens on write (ValidationManager),
        but this can be used for periodic 'health checks'.
        """
        # For now, we assume if it's in ontology_manager, it's valid.
        return True