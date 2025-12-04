import logging
import requests
from typing import Dict, Any, List
from .base_agent import BaseAgent
from src.ontology_manager import OntologyManager
from src.reasoner import Reasoner

log = logging.getLogger(__name__)

class ConceptAgent(BaseAgent):
    """
    Local Agent responsible for fetching and enriching data about Concepts.
    """
    
    def __init__(self, ontology_manager: OntologyManager, reasoner: Reasoner):
        super().__init__(ontology_manager, reasoner, agent_name="ConceptAgent")

    def identify_missing_info(self, query_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identifies a missing concept name from the query context.
        """
        # Heuristic: Look for entities that are Classes (start with capital)
        entities = query_feedback.get("mentioned_entities", [])
        for entity in entities:
            # e.g., :Deep_Learning
            if entity.startswith(":") and entity[1].isupper() and "_" in entity:
                concept_name = entity[1:].replace("_", " ") # :Deep_Learning -> "Deep Learning"
                log.debug(f"Found potential concept name: {concept_name}")
                return {"concept_name": concept_name}
        return {}

    def fetch_external_data(self, missing_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query OpenAlex Concepts endpoint.
        """
        concept_name = missing_info.get("concept_name")
        if not concept_name:
            return []
            
        url = f"https://api.openalex.org/concepts?filter=display_name.search:{concept_name}&mailto=prarukreddy@gmail.com"
        log.info(f"Fetching concepts from OpenAlex matching: {concept_name}")
        
        try:
            res = requests.get(url)
            res.raise_for_status()
            return res.json().get("results", [])
        except requests.RequestException as e:
            log.error(f"OpenAlex API request failed: {e}")
            return []

    def enrich_ontology(self, data: List[Dict[str, Any]]) -> None:
        """
        Add concept nodes and their relations (e.g., level).
        """
        for concept in data:
            if not concept or not concept.get('id'):
                continue
                
            concept_id = concept.get('id').split('/')[-1]
            concept_uri = f":{concept_id}"
            source_url = concept.get('id')

            # Add the Concept node
            self._add_with_provenance(concept_uri, "rdf:type", ":Concept", source_url)
            if concept.get('display_name'):
                self._add_with_provenance(concept_uri, "rdfs:label", f'"{concept["display_name"]}"', source_url)
            if concept.get('level') is not None:
                self._add_with_provenance(concept_uri, ":hasLevel", f"{concept['level']}", source_url)
