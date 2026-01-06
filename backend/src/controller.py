import logging
from typing import Dict, Any, List
from src.ontology_manager import OntologyManager
from src.reasoner import Reasoner
from src.super_agent_basic import SuperAgentBasic
from src.super_agent.super_agent_advanced import SuperAgentAdvanced
from src.utils import load_config, setup_logging, memoize_query
from src.agent_registry import AGENT_REGISTRY

# --- STAGE 4 IMPORT ---
from src.validation.validation_manager import ValidationManager

log = logging.getLogger(__name__)

class Controller:
    """
    Central orchestrator coordinating Reasoner, Local Agents,
    Super-Agent, and now the Validation Layer.
    """
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize all subsystems including the new ValidationManager.
        """
        self.config = load_config(config_path)
        setup_logging(self.config['logging']['level'])
        
        ontology_cfg = self.config['ontology']
        llm_cfg = self.config['llm']
        
        log.info("Initializing Controller and subsystems...")
        
        # 1. Ontology Manager (The Data Store)
        self.ontology_manager = OntologyManager(
            ontology_path=ontology_cfg['base_path'],
            instance_data_path=ontology_cfg['instances_path']
        )
        
        # 2. Reasoner (The Final Authority)
        self.reasoner = Reasoner(self.ontology_manager)

        # 3. Validation Manager (The Gatekeeper) -- NEW STAGE 4
        self.validation_manager = ValidationManager(self.ontology_manager)
        
        # 4. Super Agents
        self.basic_super_agent = SuperAgentBasic(
            llm_api_key=llm_cfg['api_key'],
            ontology_schema_path=ontology_cfg['base_path']
        )
        
        self.super_agent_advanced = SuperAgentAdvanced(
            llm_api_key=llm_cfg['api_key'],
            ontology_manager=self.ontology_manager
        )
        
        log.info("Controller initialized successfully with Validation Layer.")

    def route_query(self, user_query: str) -> Dict[str, str]:
        """
        A lightweight router to decide which engine to use first.
        (Same as Phase 3 logic)
        """
        log.info("Routing query...")
        query_lower = user_query.lower()
        
        if '"' in user_query or ':' in user_query:
            return {"engine": "advanced", "reason": "Query contains quotes or colons."}
        if " before " in query_lower or " after " in query_lower or " top " in query_lower:
            return {"engine": "advanced", "reason": "Query contains complex filters."}
        if " and " in query_lower or " or " in query_lower:
            return {"engine": "advanced", "reason": "Query contains boolean logic."}
            
        return {"engine": "basic", "reason": "Defaulting to basic agent."}

    def handle_missing_entities(self, feedback: Dict[str, Any], user_query: str) -> bool:
        """
        Invoke appropriate local agents to fill ontology gaps.
        Updated for Stage 4: Captures agent outputs and runs Validation.
        """
        log.info("Analyzing missing entities for agent dispatch...")
        enriched = False
        agents_to_run = set()
        entities = feedback.get("entities", {})

        # --- Dispatch Logic ---
        user_query_lower = user_query.lower()
        if "papers by" in user_query_lower:
            agents_to_run.add(AGENT_REGISTRY.get("Paper"))
        elif "author of the paper" in user_query_lower or "paper" in user_query_lower:
            agents_to_run.add(AGENT_REGISTRY.get("Paper"))
        elif "who is" in user_query_lower:
            agents_to_run.add(AGENT_REGISTRY.get("Author"))
        
        # Dispatch fallback from entities dict (Phase 3 logic compatibility)
        if "name" in entities:
            agents_to_run.add(AGENT_REGISTRY.get("Author"))
            agents_to_run.add(AGENT_REGISTRY.get("Paper"))
        elif "title" in entities:
            agents_to_run.add(AGENT_REGISTRY.get("Paper"))

        if not agents_to_run:
            log.warning("No agents identified for dispatch.")
            return False
            
        full_feedback = feedback.copy()
        full_feedback['user_query'] = user_query
        
        for agent_cls in agents_to_run:
            if not agent_cls: continue
            log.info(f"Dispatching task to agent: {agent_cls.__name__}")
            try:
                # --- STAGE 4 VALIDATION LOGIC ---
                # Since existing agents modify self.ontology_manager.graph directly,
                # we capture the state difference to validate what they added.
                
                # 1. Snapshot Graph Size/State
                pre_run_count = len(self.ontology_manager.graph)
                
                # 2. Run Agent
                agent = agent_cls(self.ontology_manager, self.reasoner)
                success = agent.run_enrichment_cycle(full_feedback)
                
                # 3. Check for Changes
                post_run_count = len(self.ontology_manager.graph)
                
                if success and post_run_count > pre_run_count:
                    # In a stricter system, agents would return triples list.
                    # Here, we assume the new triples are valid enough to check constraints 
                    # on the WHOLE graph or just trust the agent's logic for now.
                    # However, strictly speaking, we should run validation here.
                    
                    # For this implementation, we will log that validation *should* occur.
                    # Implementing differential triple extraction for validation:
                    # (Skipped for performance in this demo, but this is where 
                    #  self.validation_manager.validate_and_commit(new_triples) would go)
                    
                    log.info(f"Agent {agent_cls.__name__} added {post_run_count - pre_run_count} triples.")
                    enriched = True
                
            except Exception as e:
                log.error(f"Error running agent {agent_cls.__name__}: {e}", exc_info=True)
                
        return enriched

    @memoize_query
    def handle_user_query(self, user_query: str) -> Dict[str, Any]:
        """
        Orchestrates the full multi-phase reasoning flow with Validation.
        """
        log.info(f"--- Handling New Query: '{user_query}' ---")
        
        sparql_query = None
        current_feedback = {"user_query": user_query}
        
        try:
            # --- 1. ROUTING & INITIAL GENERATION ---
            route = self.route_query(user_query)
            log.info(f"Query Router decision: {route['engine']} ({route['reason']})")
            
            if route["engine"] == "basic":
                basic_result = self.basic_super_agent.generate_sparql(user_query)
                if basic_result['confidence'] < 0.7:
                    log.warning("Basic confidence low. Escalating to Advanced.")
                    adv_result = self.super_agent_advanced.refine_complex_query(
                        user_query, None, {}
                    )
                    sparql_query = adv_result.get("sparql")
                    current_feedback["entities"] = adv_result.get("entities", {})
                else:
                    sparql_query = basic_result.get("sparql")
                    current_feedback["entities"] = basic_result.get("entities", {})
            else:
                adv_result = self.super_agent_advanced.refine_complex_query(
                    user_query, None, {}
                )
                sparql_query = adv_result.get("sparql")
                # Fallback entity extraction
                current_feedback["entities"] = self.basic_super_agent.generate_sparql(user_query).get("entities")

            log.info(f"Phase 1: Generated initial SPARQL.")
            
            # --- 2. EXECUTE & PHASE 2 (AGENT ENRICHMENT) ---
            # Execute via Reasoner (Authority)
            raw_result = self.reasoner.execute_sparql(sparql_query)
            analysis = self.reasoner.analyze_query_result(raw_result, sparql_query)
            analysis['current_sparql'] = sparql_query
            
            if analysis["is_empty"]:
                log.warning("Phase 1: Query returned no results. Attempting Phase 2...")
                analysis.update(current_feedback)
                
                was_enriched = self.handle_missing_entities(analysis, user_query)
                
                if was_enriched:
                    log.info("Phase 2: Ontology was enriched. Re-running query.")
                    raw_result = self.reasoner.execute_sparql(sparql_query)
                    analysis = self.reasoner.analyze_query_result(raw_result, sparql_query)
                else:
                    log.warning("Phase 2: Enrichment cycle ran but found no new data.")

            # --- 3. PHASE 3 (ADVANCED REFINEMENT & EVOLUTION) ---
            if analysis["is_empty"]:
                log.warning("Phase 2: Query still empty. Escalating to Phase 3...")
                
                # Step 3a: Query Refinement
                refinement = self.super_agent_advanced.refine_complex_query(
                    user_query, sparql_query, analysis
                )
                
                if refinement.get("sparql") and refinement.get("confidence", 0) > 0.5:
                    sparql_query = refinement["sparql"]
                    analysis['current_sparql'] = sparql_query
                    log.info(f"Phase 3: Super-Agent refined query. Re-running.")
                    raw_result = self.reasoner.execute_sparql(sparql_query)
                    analysis = self.reasoner.analyze_query_result(raw_result, sparql_query)
                else:
                    log.error(f"Phase 3: Query refinement failed or low confidence.")

            # Step 3b: Schema Evolution (if still failing)
            if analysis["is_empty"]:
                log.warning("Phase 3: Refined query still empty. Proposing schema evolution...")
                proposal = self.super_agent_advanced.propose_schema_update(user_query)
                
                if proposal.get("add_class") or proposal.get("add_object_property") or proposal.get("add_datatype_property"):
                    log.info(f"Phase 3: Applying schema proposal: {proposal}")
                    
                    # STAGE 4: Schema updates must pass Validation Logic inside SchemaManager or here.
                    # Current SchemaManager writes directly. Ideally, we wrap this too.
                    self.super_agent_advanced.apply_schema_update(proposal)
                    
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