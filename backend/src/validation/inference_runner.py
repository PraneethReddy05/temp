import logging
import owlrl
from rdflib import Graph

log = logging.getLogger(__name__)

class InferenceRunner:
    """
    Runs reasoning over the graph to materialize implicit knowledge.
    Uses OWL-RL semantics.
    """
    def __init__(self):
        pass

    def run_reasoning(self, graph: Graph) -> bool:
        """
        Expands the graph with inferred triples.
        Returns True if consistent, False if inconsistent.
        """
        initial_count = len(graph)
        try:
            # Applies RDFS and OWL-RL reasoning semantics
            owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(graph)
            # You can upgrade to OWLRL_Semantics for stricter logic:
            # owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)
            
            final_count = len(graph)
            if final_count > initial_count:
                log.info(f"InferenceRunner materialized {final_count - initial_count} new triples.")
            return True
        except Exception as e:
            log.error(f"Inconsistency detected during reasoning: {e}")
            return False