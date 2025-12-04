import json
import logging
import os
import google.generativeai as genai
from typing import Dict, Any, List
from src.ontology_manager import OntologyManager
from src.super_agent.schema_manager import SchemaManager
import time 
import random 

log = logging.getLogger(__name__)

# --- Helper to load prompts ---
# FIX 1: Changed "reasoning_prompt" to "reasoning_prompts"
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "reasoning_prompts")

def load_prompt(filename: str) -> str:
    """Loads a prompt template from the reasoning_prompts directory."""
    try:
        with open(os.path.join(PROMPT_DIR, filename), 'r') as f:
            return f.read()
    except Exception as e:
        log.error(f"Error loading prompt {filename}: {e}")
        return ""
# ------------------------------


class SuperAgentAdvanced:
    """
    Evolves the basic Super-Agent into a cognitive coordinator that can:
    1. Refine complex SPARQL queries.
    2. Interpret agent feedback and perform semantic reasoning.
    3. Suggest and apply ontology schema updates.
    4. Mediate between multiple local agents.
    
    (Using Gemini API)
    """
    
    def __init__(self, llm_api_key: str, ontology_manager: OntologyManager):
        """
        Initialize with a Gemini client and the singleton OntologyManager.
        """
        genai.configure(api_key=llm_api_key)
        
        # FIX 2: Changed model name to "gemini-pro"
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
        self.json_model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config=generation_config
        )
        
        # FIX 2: Changed model name to "gemini-pro"
        self.text_model = genai.GenerativeModel("gemini-2.5-flash")
        
        self.ontology_manager = ontology_manager
        self.schema_manager = SchemaManager(self.ontology_manager)
        
        # Load prompt templates
        self.refinement_prompt = load_prompt("query_refinement_prompt.txt")
        self.schema_prompt = load_prompt("schema_update_prompt.txt")
        self.coordination_prompt = load_prompt("multi_agent_coordination_prompt.txt")
        log.info("SuperAgentAdvanced initialized with Gemini client and SchemaManager.")

    def _call_llm_json(self, combined_prompt: str) -> Dict[str, Any]:
        """
        A generic wrapper for making Gemini calls that MUST return JSON.
        Includes Retry logic for Rate Limits (429).
        """
        log.debug("Calling Gemini for advanced JSON reasoning...")
        
        max_retries = 3
        base_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                response = self.json_model.generate_content([combined_prompt])
                return json.loads(response.text)
            
            except Exception as e:
                error_str = str(e)
                # Check for Rate Limit (429)
                if "429" in error_str or "Quota exceeded" in error_str:
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        log.warning(f"Gemini Rate Limit hit. Retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        log.error("Gemini Rate Limit exceeded after max retries.")
                        return {"error": "Rate limit exceeded"}
                
                # Handle other errors (like the UnboundLocalError from before)
                log.error(f"Gemini JSON call or parsing failed: {e}")
                return {"error": str(e)}
        
        return {"error": "Unknown failure"}

    def get_schema_snippet(self) -> str:
        """
        Generates a string snippet of the ontology's TBox (classes and props).
        (Unchanged)
        """
        query = """
        SELECT ?class ?property ?range
        WHERE {
          { ?class a owl:Class . }
          UNION
          { ?property a owl:ObjectProperty ; rdfs:range ?range . }
          UNION
          { ?property a owl:DatatypeProperty ; rdfs:range ?range . }
        }
        LIMIT 100
        """
        results = self.ontology_manager.query_graph(query)
        return json.dumps(results, indent=2)

    # ---------- 1. Semantic query refinement ----------
    def refine_complex_query(self, user_query: str, failed_sparql: str, feedback: dict) -> dict:
        """
        Use LLM to interpret intent, combine schema + feedback,
        and produce an improved SPARQL query.
        """
        log.info("Escalating to SuperAgent (Gemini) for query refinement...")
        schema = self.get_schema_snippet()
        
        prompt_input = self.refinement_prompt.format(
            user_query=user_query,
            failed_sparql=failed_sparql,
            feedback=json.dumps(feedback),
            schema=schema
        )
        
        response = self._call_llm_json(prompt_input)
        
        return response 

    # ---------- 2. Knowledge synthesis (Example) ----------
    def synthesize_knowledge(self, partial_results: List[dict], context: str) -> str:
        """
        Combines multiple agent results to generate a higher-order insight.
        """
        log.info("Synthesizing knowledge from partial results (Gemini)...")
        
        system_prompt = (
            "You are a research analyst. Summarize the following disconnected "
            "pieces of data into a single, coherent paragraph. "
            "Do not return JSON."
        )
        user_prompt = f"Context: {context}\n\nData: {json.dumps(partial_results)}"
        
        try:
            response = self.text_model.generate_content([system_prompt, user_prompt])
            return response.text
        except Exception as e:
            log.error(f"Gemini synthesis call failed: {e}")
            return f"Synthesis failed: {e}"

    # ---------- 3. Schema evolution ----------
    def propose_schema_update(self, user_query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ask LLM if new classes/properties are needed to model query concepts.
        """
        log.info("Escalating to SuperAgent (Gemini) for schema evolution proposal...")
        schema = self.get_schema_snippet()
        
        prompt_input = self.schema_prompt.format(
            user_query=user_query,
            schema=schema
        )
        
        proposal = self._call_llm_json(prompt_input)
        
        return proposal

    def apply_schema_update(self, proposal: Dict[str, List[Dict[str, Any]]]) -> bool:
        """
        Call SchemaManager to actually add the new OWL elements and save.
        (Unchanged)
        """
        log.info("Applying proposed schema updates...")
        try:
            for new_class in proposal.get("add_class", []):
                self.schema_manager.add_class(
                    new_class["name"],
                    new_class.get("parent", "owl:Thing"),
                    new_class.get("label")
                )
            
            for new_op in proposal.get("add_object_property", []):
                self.schema_manager.add_object_property(
                    new_op["name"],
                    new_op["domain"],
                    new_op["range"],
                    new_op.get("label")
                )
                
            # for new_dp in proposal.get("add_datatype_property", []):
            #     self.schema_manager.add_datatype_property(
            #         new_dp["name"],
            #         new_dp["domain"],
            #         new_dp["range"],
            #         new_op.get("label")
            #     )
            for new_dp in proposal.get("add_datatype_property", []):
                self.schema_manager.add_datatype_property(
                    new_dp["name"],
                    new_dp["domain"],
                    new_dp["range"],
                    # --- BEFORE (BUG) ---
                    # new_op.get("label")
                    
                    # --- AFTER (FIX) ---
                    new_dp.get("label")
                )
            
            self.schema_manager.save()
            log.info("Schema update applied and saved successfully.")
            return True
        except Exception as e:
            log.error(f"Failed to apply schema update: {e}", exc_info=True)
            return False

    # ---------- 4. Coordination ----------
    def orchestrate_agents(self, user_query: str, feedback: dict) -> List[Dict[str, Any]]:
        """
        Decide which local agents should collaborate.
        """
        log.info("Escalating to SuperAgent (Gemini) for multi-agent coordination...")
        
        prompt_input = self.coordination_prompt.format(
            user_query=user_query,
            feedback=json.dumps(feedback)
        )
        
        plan = self._call_llm_json(prompt_input)
        
        return plan