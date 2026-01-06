import logging
import re
from typing import Dict, Any

log = logging.getLogger(__name__)

class SuperAgentBasic:
    """
    Refactored to act as a "screener" or "dummy" agent.
    It attempts to parse the query with minimal regex and returns
    a confidence score and any extracted entities.
    It no longer loads the schema; it only knows its patterns.
    """
    def __init__(self, llm_api_key: str, ontology_schema_path: str):
        # We no longer need the schema or API key here.
        log.info("SuperAgentBasic initialized (in screener mode).")
        
        # --- Minimal, stable patterns ---
        # Pattern 1: "papers by [Name]" or "who is [Name]"
        self.name_pattern = re.compile(r"(papers by|who is) ([a-z \.-]+)", re.IGNORECASE)
        # Pattern 2: "... paper [Title]"
        self.title_pattern = re.compile(r"paper (.+)", re.IGNORECASE)

    def generate_sparql(self, user_query: str) -> Dict[str, Any]:
        """
        Generates a basic SPARQL query and a confidence score.
        
        :return: A dict {"sparql": str, "confidence": float, "entities": dict}
        """
        
        # --- Pattern 1: Match by Author Name ---
        match_name = self.name_pattern.search(user_query)
        if match_name and "paper" not in user_query.lower():
            name = match_name.group(2).strip().title()
            log.info(f"Basic agent: Matched name '{name}'")
            sparql = f"""
PREFIX : <http://example.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?author ?label
WHERE {{
  ?author rdfs:label "{name}" .
  ?author rdf:type :Author .
  OPTIONAL {{ ?author rdfs:label ?label . }}
}}
"""
            return {
                "sparql": sparql,
                "confidence": 0.9,  # High confidence in this pattern
                "entities": {"name": name}
            }

        # --- Pattern 2: Match by Paper Title ---
        match_title = self.title_pattern.search(user_query)
        if match_title:
            title = match_title.group(1).strip().strip('"')
            log.info(f"Basic agent: Matched title '{title}'")
            sparql = f"""
PREFIX : <http://example.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?author ?label
WHERE {{
  ?paper rdfs:label "{title}" .
  ?paper rdf:type :Paper .
  ?paper :hasAuthor ?author .
  ?author rdfs:label ?label .
}}
"""
            return {
                "sparql": sparql,
                "confidence": 0.9,  # High confidence in this pattern
                "entities": {"title": title}
            }

        # --- Fallback: Low Confidence ---
        log.warning(f"Basic agent: No pattern matched. Low confidence.")
        return {
            "sparql": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
            "confidence": 0.1,  # Very low confidence
            "entities": {}
        }