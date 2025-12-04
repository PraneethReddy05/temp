import logging
from typing import Dict, Any
from src.ontology_manager import OntologyManager
from src.reasoner import Reasoner
from src.super_agent_basic import SuperAgentBasic # Still used for initial NL->SPARQL
from src.utils import load_config, setup_logging
from src.agent_registry import AGENT_REGISTRY
# --- PHASE 3 IMPORTS ---
from src.super_agent.super_agent_advanced import SuperAgentAdvanced

log = logging.getLogger(__name__)

class Controller:
    """
    Central orchestrator coordinating Reasoner, Local Agents,
    and the Super-Agent.
    """
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize all subsystems.
        """
        self.config = load_config(config_path)
        setup_logging(self.config['logging']['level'])
        
        ontology_cfg = self.config['ontology']
        llm_cfg = self.config['llm']
        
        log.info("Initializing Controller and subsystems...")
        
        # --- Phase 1 Subsystems ---
        self.ontology_manager = OntologyManager(
            ontology_path=ontology_cfg['base_path'],
            instance_data_path=ontology_cfg['instances_path']
        )
        self.reasoner = Reasoner(self.ontology_manager)
        
        # --- Phase 1/3 Super-Agent ---
        # We keep the "basic" agent for the fast, cheap, initial NL->SPARQL
        self.basic_super_agent = SuperAgentBasic(
            llm_api_key=llm_cfg['api_key'],
            ontology_schema_path=ontology_cfg['base_path']
        )
        
        # --- Phase 3 Advanced Super-Agent ---
        # This is the new, "expensive" cognitive coordinator
        self.super_agent_advanced = SuperAgentAdvanced(
            llm_api_key=llm_cfg['api_key'],
            ontology_manager=self.ontology_manager
        )
        
        log.info("Controller initialized successfully.")

    # --- Phase 2 Method (Unchanged) ---
    # def handle_missing_entities(self, feedback: Dict[str, Any], user_query: str) -> bool:
    #     """
    #     Invoke appropriate local agents to fill ontology gaps.
    #     """
    #     log.info("Analyzing missing entities for agent dispatch...")
    #     enriched = False
        
    #     # (This uses the simple regex-based identification from Phase 2)
    #     agents_to_run = set()
    #     user_query_lower = user_query.lower()
    #     if "papers by" in user_query_lower or "who is" in user_query_lower:
    #         agents_to_run.add(AGENT_REGISTRY.get("Author"))
    #         agents_to_run.add(AGENT_REGISTRY.get("Paper"))
        
    #     if not agents_to_run:
    #         log.warning("No agents identified for dispatch.")
    #         return False
            
    #     full_feedback = feedback.copy()
    #     full_feedback['user_query'] = user_query
        
    #     for agent_cls in agents_to_run:
    #         if not agent_cls:
    #             continue
    #         log.info(f"Dispatching task to agent: {agent_cls.__name__}")
    #         try:
    #             agent = agent_cls(self.ontology_manager, self.reasoner)
    #             success = agent.run_enrichment_cycle(full_feedback)
    #             if success:
    #                 enriched = True
    #         except Exception as e:
    #             log.error(f"Error running agent {agent_cls.__name__}: {e}", exc_info=True)
                
    #     return enriched

    def handle_missing_entities(self, feedback: Dict[str, Any], user_query: str) -> bool:
        """
        Invoke appropriate local agents to fill ontology gaps.
        (Updated with smarter dispatch logic)
        """
        log.info("Analyzing missing entities for agent dispatch...")
        enriched = False
        agents_to_run = set()
        user_query_lower = user_query.lower()

        # --- NEW DISPATCH LOGIC ---
        if "papers by" in user_query_lower:
            # PaperAgent is responsible for papers AND their authors
            log.debug("Dispatching PaperAgent for 'papers by' query.")
            agents_to_run.add(AGENT_REGISTRY.get("Paper"))
        elif "who is" in user_query_lower:
            # AuthorAgent is responsible for author details
            log.debug("Dispatching AuthorAgent for 'who is' query.")
            agents_to_run.add(AGENT_REGISTRY.get("Author"))
        else:
            # A simple fallback (can be improved)
            log.debug("Dispatching both agents as a fallback.")
            agents_to_run.add(AGENT_REGISTRY.get("Author"))
            agents_to_run.add(AGENT_REGISTRY.get("Paper"))
        # --- END NEW LOGIC ---

        if not agents_to_run:
            log.warning("No agents identified for dispatch.")
            return False
            
        full_feedback = feedback.copy()
        full_feedback['user_query'] = user_query
        
        for agent_cls in agents_to_run:
            if not agent_cls:
                continue
            log.info(f"Dispatching task to agent: {agent_cls.__name__}")
            try:
                agent = agent_cls(self.ontology_manager, self.reasoner)
                success = agent.run_enrichment_cycle(full_feedback)
                if success:
                    enriched = True
            except Exception as e:
                log.error(f"Error running agent {agent_cls.__name__}: {e}", exc_info=True)
                
        return enriched

    # --- PHASE 3: MAIN QUERY HANDLER ---
    def handle_user_query(self, user_query: str) -> Dict[str, Any]:
        """
        Orchestrates the full 3-phase reasoning flow.
        """
        log.info(f"Handling user query: '{user_query}'")
        
        try:
            # --- PHASE 1: Initial SPARQL Generation ---
            sparql_query = self.basic_super_agent.generate_sparql(user_query)
            log.info(f"Phase 1: Generated initial SPARQL.")
            
            raw_result = self.reasoner.execute_sparql(sparql_query)
            analysis = self.reasoner.analyze_query_result(raw_result, sparql_query)
            analysis['current_sparql'] = sparql_query

            # --- PHASE 2: Local Agent Enrichment ---
            if analysis["is_empty"]:
                log.warning("Phase 1: Query returned no results. Attempting Phase 2...")
                
                was_enriched = self.handle_missing_entities(analysis, user_query)
                
                if was_enriched:
                    log.info("Phase 2: Ontology was enriched. Re-running query.")
                    raw_result = self.reasoner.execute_sparql(sparql_query)
                    analysis = self.reasoner.analyze_query_result(raw_result, sparql_query)
                else:
                    log.warning("Phase 2: Enrichment cycle ran but found no new data.")
            
            # --- PHASE 3: Super-Agent Escalation ---
            if analysis["is_empty"]:
                log.warning("Phase 2: Query still empty. Escalating to Phase 3...")
                
                # Step 3a: Query Refinement
                refinement = self.super_agent_advanced.refine_complex_query(
                    user_query, sparql_query, analysis
                )
                
                if refinement.get("sparql") and refinement.get("confidence", 0) > 0.5:
                    sparql_query = refinement["sparql"]
                    analysis['current_sparql'] = sparql_query
                    log.info(f"Phase 3: Super-Agent refined query (Conf: {refinement['confidence']}). Re-running.")
                    raw_result = self.reasoner.execute_sparql(sparql_query)
                    analysis = self.reasoner.analyze_query_result(raw_result, sparql_query)
                else:
                    log.error(f"Phase 3: Query refinement failed or low confidence: {refinement.get('explanation')}")

            # Step 3b: Schema Evolution (if still failing)
            if analysis["is_empty"]:
                log.warning("Phase 3: Refined query still empty. Proposing schema evolution...")
                
                proposal = self.super_agent_advanced.propose_schema_update(user_query)
                
                if proposal.get("add_class") or proposal.get("add_object_property") or proposal.get("add_datatype_property"):
                    log.info(f"Phase 3: Applying schema proposal: {proposal}")
                    self.super_agent_advanced.apply_schema_update(proposal)
                    
                    # One final attempt with the refined query on the new schema
                    log.info("Phase 3: Schema updated. Re-running final query.")
                    raw_result = self.reasoner.execute_sparql(sparql_query)
                    analysis = self.reasoner.analyze_query_result(raw_result, sparql_query)
                else:
                    log.warning("Phase 3: Super-Agent proposed no schema changes.")
            
            # --- FINAL RESULT ---
            self.log_query(user_query, sparql_query, analysis)
            analysis['original_query'] = user_query
            return analysis

        except Exception as e:
            log.critical(f"Unhandled exception in query flow: {e}", exc_info=True)
            return {"status": "error", "message": str(e), "is_empty": True}

    def log_query(self, user_query: str, sparql_query: str, result: Dict[str, Any]) -> None:
        """Write query/response logs."""
        log.info(f"--- QUERY TRACE ---")
        log.info(f"User Query: {user_query}")
        log.info(f"Final SPARQL Query:\n{sparql_query}")
        log.info(f"Result Status: {result.get('status', 'N/A')}")
        log.info(f"Bindings Count: {len(result.get('raw_result', {}).get('bindings', []))}")
        log.info(f"---------------------")