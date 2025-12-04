import logging
import re
import requests
from typing import Dict, Any, List
from .base_agent import BaseAgent
from src.ontology_manager import OntologyManager
from src.reasoner import Reasoner

log = logging.getLogger(__name__)

class PaperAgent(BaseAgent):
    """
    Local Agent responsible for fetching and enriching data about Papers.
    """
    
    def __init__(self, ontology_manager: OntologyManager, reasoner: Reasoner):
        super().__init__(ontology_manager, reasoner, agent_name="PaperAgent")

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

    # In: src/agents/paper_agent.py

    def fetch_external_data(self, missing_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query OpenAlex Works endpoint for papers by a specific author.
        """
        author_name = missing_info.get("author_name")
        if not author_name:
            return []
            
        # MAKE SURE THIS LINE IS CORRECT AND HAS YOUR EMAIL
        # url = f"https://api.openalex.org/works?filter=author.display_name.search:{author_name}&mailto=prarukreddy@gmail.com"
        # url = f"https://api.openalex.org/works?filter=authorships.author.display_name.search:{author_name}&mailto=prarukreddy@gmail.com"
        # url = f"https.api.openalex.org/works?filter=raw_author_name.search:{author_name}&mailto=prarukreddy@gmail.com"
        url = f"https://api.openalex.org/works?filter=raw_author_name.search:{author_name}&mailto=prarukreddy@gmail.com"

        log.info(f"Fetching papers from OpenAlex for author: {author_name}")
        
        try:
            res = requests.get(url)
            res.raise_for_status() # Raise error for bad responses
            return res.json().get("results", [])
        except requests.RequestException as e:
            log.error(f"OpenAlex API request failed: {e}")
            return []

    # def fetch_external_data(self, missing_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    #     """
    #     Query OpenAlex Works endpoint for papers by a specific author.
    #     """
    #     author_name = missing_info.get("author_name")
    #     if not author_name:
    #         return []
            
    #     url = f"https://api.openalex.org/works?filter=author.display_name.search:{author_name}&mailto=prarukreddy@gmail.com"
    #     log.info(f"Fetching papers from OpenAlex for author: {author_name}")
        
    #     try:
    #         res = requests.get(url)
    #         res.raise_for_status() # Raise error for bad responses
    #         return res.json().get("results", [])
    #     except requests.RequestException as e:
    #         log.error(f"OpenAlex API request failed: {e}")
    #         return []

    def enrich_ontology(self, data: List[Dict[str, Any]]) -> None:
        """
        Add triples for Papers and their relationships (e.g., hasAuthor).
        """
        for work in data:
            if not work or not work.get('id'):
                continue
                
            work_id = work.get('id').split('/')[-1]
            work_uri = f":{work_id}"
            source_url = work.get('id')
            
            # Add the Paper node
            self._add_with_provenance(work_uri, "rdf:type", ":Paper", source_url)
            if work.get('display_name'):
                self._add_with_provenance(work_uri, "rdfs:label", f'"{work["display_name"]}"', source_url)

            # Link to authors
            for authorship in work.get('authorships', []):
                author = authorship.get('author')
                if author and author.get('id'):
                    author_id = author.get('id').split('/')[-1]
                    author_uri = f":{author_id}"
                    
                    # Add the :hasAuthor link
                    self._add_with_provenance(work_uri, ":hasAuthor", author_uri, source_url)
                    
                    # Also add/update the Author node (idempotent)
                    self._add_with_provenance(author_uri, "rdf:type", ":Author", author.get('id'))
                    if author.get('display_name'):
                        self._add_with_provenance(author_uri, "rdfs:label", f'"{author["display_name"]}"', author.get('id'))