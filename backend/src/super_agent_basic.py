import logging
import re
from typing import Dict, Any

# Mock LLM API clients for runnable code
# In a real scenario:
# from openai import OpenAI
# import google.generativeai as genai

log = logging.getLogger(__name__)

class SuperAgentBasic:
    """
    Converts natural-language queries into SPARQL via LLM (mocked) or templates.
    """
    def __init__(self, llm_api_key: str, ontology_schema_path: str):
        """
        Initialize LLM interface with ontology schema context.
        
        :param llm_api_key: The API key for OpenAI or Gemini.
        :param ontology_schema_path: Path to the .owl file to use as schema context.
        """
        self.api_key = llm_api_key
        self.ontology_schema_path = ontology_schema_path
        self.ontology_schema = self._load_schema()
        
        # Mocking: In a real app, you'd init the client
        # self.client = OpenAI(api_key=self.api_key)
        log.info(f"SuperAgentBasic initialized (using MOCK generator).")
        log.debug(f"Loaded schema context from {ontology_schema_path}")

    # def _load_schema(self) -> str:
    #     """Helper to load the ontology file content as a string."""
    #     try:
    #         with open(self.ontology_schema_path, 'r') as f:
    #             return f.read()
    #     except Exception as e:
    #         log.error(f"Could not load ontology schema: {e}")
    #         return ""

    def _load_schema(self) -> str:
        """Helper to load the ontology file content as a string."""
        try:
            # --- BEFORE ---
            # with open(self.ontology_schema_path, 'r') as f:
            
            # --- AFTER ---
            with open(self.ontology_schema_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            log.error(f"Could not load ontology schema: {e}")
            return ""

    def generate_sparql(self, user_query: str) -> str:
        """
        Call LLM API to convert NL -> SPARQL.
        For Phase 1, this routes to the mock generator.
        """
        log.info(f"Generating SPARQL for query: '{user_query}'")
        
        # --- MOCK IMPLEMENTATION ---
        sparql_query = self.mock_generate_sparql(user_query)
        
        # --- REAL LLM IMPLEMENTATION (Example) ---
        # system_prompt = f"""
        # You are a SPARQL query generator. You will be given a user's
        # natural language query and an ontology schema.
        # Your task is to convert the query into a valid SPARQL 1.1 SELECT query.
        # Use the prefixes defined in the schema.
        # Only output the SPARQL query, with no other text.
        
        # SCHEMA:
        # {self.ontology_schema}
        # """
        
        # response = self.client.chat.completions.create(
        #     model="gpt-4-turbo",
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": user_query}
        #     ]
        # )
        # sparql_query = response.choices[0].message.content
        # -----------------------------------------
        
        log.debug(f"Generated SPARQL:\n{sparql_query}")
        return sparql_query

    def refine_sparql(self, query: str, feedback: Dict[str, Any]) -> str:
        """
        Refine SPARQL if the Reasoner reports missing info.
        
        :param query: The original (failed) SPARQL query.
        :param feedback: The analysis dict from the Reasoner.
        :return: A new, refined SPARQL query.
        """
        log.warning(f"Refining query based on feedback: {feedback['mentioned_entities']}")
        
        # --- MOCK REFINEMENT LOGIC ---
        # This is a simple mock. A real agent would use an LLM call.
        # "Based on the empty result, and the query's mention of 
        # [entities], please generate a new query."
        
        if ":Andrew_Ng" in feedback.get("mentioned_entities", []):
            # Mock refinement: Try a different spelling
            new_query = query.replace(":Andrew_Ng", ":A_Ng")
            log.info("Refinement attempt: Changed :Andrew_Ng to :A_Ng")
            return new_query
            
        log.error("No refinement rule found for this query. Returning original.")
        return query
    
    def mock_generate_sparql(self, user_query: str) -> str:
        """
        Offline rule-based conversion for testing.
        Now searches by label instead of inventing a URI.
        """
        query_lower = user_query.lower()
        
        # Look for patterns like "papers by [Name]"
        match = re.search(r"(papers by|who is) (.+)", query_lower)
        
        if match:
            # Extract the name, e.g., "geoffrey hinton"
            name = match.group(2).strip().title() # -> "Geoffrey Hinton"
            
            log.info(f"Mock agent parsed name: \"{name}\"")
            
            # This is the new, smarter query.
            # It searches for any author with the *label* "Geoffrey Hinton"
            # and then finds papers by that author.
            return f"""
PREFIX : <http://example.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?paper ?label
WHERE {{
  ?author rdfs:label "{name}" .
  ?author rdf:type :Author .
  ?paper :hasAuthor ?author .
  ?paper rdfs:label ?label .
}}
"""
        elif "list all papers" in query_lower:
            return """
PREFIX : <http://example.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?paper ?label
WHERE {
  ?paper rdf:type :Paper .
  ?paper rdfs:label ?label .
}
"""
        else:
            # Fallback for truly unknown queries
            log.warning(f"Mock agent could not parse query: '{user_query}'")
            return """
PREFIX : <http://example.org/ontology#>
SELECT ?s WHERE { ?s rdf:type :NonExistentClass . }
"""
    
#     def mock_generate_sparql(self, user_query: str) -> str:
#         """
#         Offline rule-based conversion for testing.
#         Now with simple regex to parse names.
#         """
#         query_lower = user_query.lower()
        
#         # --- NEW LOGIC TO PARSE NAMES ---
#         # Look for patterns like "papers by [Name]" or "who is [Name]"
#         match = re.search(r"(papers by|who is) (.+)", query_lower)
        
#         if match:
#             # Extract the name, e.g., "geoffrey hinton"
#             name = match.group(2).strip()
#             # Convert to a URI, e.g., ":Geoffrey_Hinton"
#             uri_name = ":" + name.title().replace(" ", "_")
            
#             log.info(f"Mock agent parsed name: {uri_name}")
            
#             # Return a query that WILL FAIL (because this URI isn't in the graph)
#             # This failure is what triggers the Phase 2 enrichment cycle.
#             return f"""
# PREFIX : <http://example.org/ontology#>
# PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# SELECT ?paper ?label
# WHERE {{
#   ?paper rdf:type :Paper .
#   ?paper :hasAuthor {uri_name} .
#   ?paper rdfs:label ?label .
# }}
# """
#         elif "list all papers" in query_lower:
#             return """
# PREFIX : <http://example.org/ontology#>
# PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# SELECT ?paper ?label
# WHERE {
#   ?paper rdf:type :Paper .
#   ?paper rdfs:label ?label .
# }
# """
#         else:
#             # Fallback for truly unknown queries
#             log.warning(f"Mock agent could not parse query: '{user_query}'")
#             # Return a query that is guaranteed to be empty
#             return """
# PREFIX : <http://example.org/ontology#>
# SELECT ?s WHERE { ?s rdf:type :NonExistentClass . }
# """

    # def mock_generate_sparql(self, user_query: str) -> str:
        
#         """
#         Offline rule-based conversion for testing (as required by prompt).
#         """
#         query_lower = user_query.lower()
        
#         if "papers written by andrew ng" in query_lower:
#             return """
# PREFIX : <http://example.org/ontology#>
# PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# SELECT ?paper ?label
# WHERE {
#   ?paper rdf:type :Paper .
#   ?paper :hasAuthor :Andrew_Ng .
#   ?paper rdfs:label ?label .
# }
# """
#         elif "list all papers" in query_lower:
#             return """
# PREFIX : <http://example.org/ontology#>
# PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# SELECT ?paper ?label
# WHERE {
#   ?paper rdf:type :Paper .
#   ?paper rdfs:label ?label .
# }
# """
#         else:
#             # Fallback query
#             return """
# PREFIX : <http://example.org/ontology#>
# SELECT ?s ?p ?o
# WHERE {
#   ?s ?p ?o .
# }
# LIMIT 10
# """
