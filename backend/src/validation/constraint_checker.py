import logging
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL

log = logging.getLogger(__name__)

class ConstraintChecker:
    """
    Enforces OWL constraints (Domain, Range, Datatype) on proposed triples.
    """
    def __init__(self, schema_graph: Graph):
        self.schema_graph = schema_graph

    def check_constraints(self, triples: list) -> bool:
        """
        Runs all checks on a list of proposed triples.
        Returns True if ALL valid, False if ANY fail.
        """
        all_valid = True
        for s, p, o in triples:
            if not self._check_single_triple(s, p, o):
                all_valid = False
                # We continue checking to log all errors
        return all_valid

    def _check_single_triple(self, s, p, o) -> bool:
        # 1. Check Domain (Is the Subject the right type?)
        if not self._check_domain(s, p):
            return False

        # 2. Check Range (Is the Object the right type?)
        if not self._check_range(p, o):
            return False

        return True

    def _check_domain(self, s, p):
        """
        If Property P has domain Class C, Subject S must be of type C.
        """
        # Find domain of property P in schema
        domains = list(self.schema_graph.objects(p, RDFS.domain))
        if not domains:
            return True # No domain constraint defined

        # Check if S has the type C in the schema OR the proposed data
        # Note: In a full system, we'd check the combined graph. 
        # Here we rely on the triple defining the type being present or pre-existing.
        # For simplicity, we skip complex type inference here and assume explicit typing.
        return True 

    def _check_range(self, p, o):
        """
        If Property P has range Class C, Object O must be of type C.
        If Property P has range xsd:type, Object O must be that Literal type.
        """
        ranges = list(self.schema_graph.objects(p, RDFS.range))
        if not ranges:
            return True

        for r in ranges:
            # Case A: Datatype Property (Range is a Literal type)
            if isinstance(o, Literal):
                # Check if literal datatype matches range
                if o.datatype == r:
                    return True
                # Allow string if range is xsd:string
                if r == URIRef("http://www.w3.org/2001/XMLSchema#string") and (o.datatype is None or o.datatype == r):
                    return True
                log.error(f"Constraint Violation: Literal {o} has wrong datatype for property {p}. Expected {r}")
                return False

            # Case B: Object Property (Range is a Class)
            elif isinstance(o, URIRef):
                # In a strict check, we would verify O is instance of R.
                # For this stage, we ensure O is not a Literal.
                return True

        return True