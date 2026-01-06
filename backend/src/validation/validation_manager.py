import logging
from rdflib import Graph
from src.ontology_manager import OntologyManager
from src.validation.constraint_checker import ConstraintChecker
from src.validation.inference_runner import InferenceRunner

log = logging.getLogger(__name__)

class ValidationManager:
    """
    Gatekeeper: Prevents invalid data from entering the ontology.
    Implements a transactional 'Try -> Validate -> Commit' workflow.
    """
    def __init__(self, ontology_manager: OntologyManager):
        self.ontology_manager = ontology_manager
        self.constraint_checker = ConstraintChecker(ontology_manager.graph)
        self.inference_runner = InferenceRunner()

    def validate_and_commit(self, proposed_triples: list) -> bool:
        """
        1. Clone current graph (Sandbox).
        2. Insert proposed triples.
        3. Check constraints.
        4. Run inference.
        5. If success -> Merge into Main Graph.
        """
        if not proposed_triples:
            return False

        log.info(f"ValidationManager: Validating {len(proposed_triples)} proposed triples...")

        # 1. Create Sandbox Graph (Clone)
        sandbox_graph = self.ontology_manager.clone_graph()

        # 2. Apply proposed changes to Sandbox
        for s, p, o in proposed_triples:
            sandbox_graph.add((s, p, o))

        # 3. Constraint Checking
        if not self.constraint_checker.check_constraints(proposed_triples):
            log.warning("ValidationManager: Constraint check FAILED. Discarding updates.")
            return False

        # 4. Inference & Consistency
        if not self.inference_runner.run_reasoning(sandbox_graph):
            log.warning("ValidationManager: Reasoning inconsistency found. Discarding updates.")
            return False

        # 5. Commit (Merge Sandbox back to Main)
        log.info("ValidationManager: Checks passed. Committing to main ontology.")
        self.ontology_manager.merge_graph(sandbox_graph)
        return True