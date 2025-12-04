import logging
import re
import requests
from typing import Dict, Any, List
from .base_agent import BaseAgent
from src.ontology_manager import OntologyManager
from src.reasoner import Reasoner

log = logging.getLogger(__name__)

class AuthorAgent(BaseAgent):
    """
    Local Agent responsible for fetching and enriching data about Authors.
    """
    
    def __init__(self, ontology_manager: OntologyManager, reasoner: Reasoner):
        super().__init__(ontology_manager, reasoner, agent_name="AuthorAgent")

    def identify_missing_info(self, query_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identifies a missing author name by parsing the user's NL query.
        """
        # Get the original user query, which the Controller added to the feedback
        user_query = query_feedback.get("user_query", "").lower()
        
        # Use the same regex as the mock SuperAgent
        match = re.search(r"(papers by|who is) (.+)", user_query)
        
        if match:
            # Extract the name, e.g., "geoffrey hinton"
            author_name = match.group(2).strip()
            log.debug(f"[{self.agent_name}] Parsed name from user query: {author_name}")
            return {"author_name": author_name}
            
        log.warning(f"[{self.agent_name}] Could not parse name from user query: {user_query}")
        return {}

    def fetch_external_data(self, missing_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query OpenAlex Authors endpoint.
        """
        author_name = missing_info.get("author_name")
        if not author_name:
            return []
            
        url = f"https://api.openalex.org/authors?filter=display_name.search:{author_name}&mailto=prarukreddy@gmail.com"
        log.info(f"Fetching authors from OpenAlex matching: {author_name}")
        
        try:
            res = requests.get(url)
            res.raise_for_status()
            return res.json().get("results", [])
        except requests.RequestException as e:
            log.error(f"OpenAlex API request failed: {e}")
            return []

    def enrich_ontology(self, data: List[Dict[str, Any]]) -> None:
        """
        Add triples for author metadata and affiliations.
        """
        for author in data:
            if not author or not author.get('id'):
                continue
                
            author_id = author.get('id').split('/')[-1]
            author_uri = f":{author_id}"
            source_url = author.get('id')

            # Add the Author node
            self._add_with_provenance(author_uri, "rdf:type", ":Author", source_url)
            if author.get('display_name'):
                self._add_with_provenance(author_uri, "rdfs:label", f'"{author["display_name"]}"', source_url)

            # Add affiliation if available
            institution = author.get('last_known_institution')
            if institution and institution.get('id'):
                inst_id = institution.get('id').split('/')[-1]
                inst_uri = f":{inst_id}"
                
                self._add_with_provenance(author_uri, ":affiliatedWith", inst_uri, source_url)
                
                # Add/update institution node
                self._add_with_provenance(inst_uri, "rdf:type", ":Institution", institution.get('id'))
                if institution.get('display_name'):
                    self._add_with_provenance(inst_uri, "rdfs:label", f'"{institution["display_name"]}"', institution.get('id'))