import logging
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, OWL, RDFS
from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer

log = logging.getLogger(__name__)

class OntologyManager:
    """
    Manages loading, querying, and updating the RDFLib graph.
    """
    def __init__(self, ontology_path: str, instance_data_path: str = None):
        """
        Initialize and load the ontology graph.
        
        :param ontology_path: Path to the base ontology file (.owl, .rdf, .ttl)
        :param instance_data_path: Optional path to instance data file.
        """
        self.ontology_path = ontology_path
        self.instance_data_path = instance_data_path
        self.graph = Graph()
        # Define a base namespace for your ontology (matches dummy files)
        self.base_ns = Namespace("http://example.org/ontology#")
        self.graph.bind(":", self.base_ns)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        
        self.load_graph()

    def load_graph(self) -> None:
        """
        Load ontology (.owl/.rdf) and instance data into the RDFLib graph.
        """
        try:
            self.graph.parse(self.ontology_path, format="turtle")
            log.info(f"Successfully loaded base ontology from {self.ontology_path}")
            
            if self.instance_data_path:
                self.graph.parse(self.instance_data_path, format="turtle")
                log.info(f"Successfully loaded instance data from {self.instance_data_path}")
                
            log.info(f"Graph contains {len(self.graph)} triples.")
            
        except FileNotFoundError as e:
            log.error(f"Error loading file: {e}. Please check paths.")
        except Exception as e:
            log.error(f"Error parsing graph: {e}")

    def save_graph(self, output_path: str = None) -> None:
        """
        Persist the updated ontology graph to a file.
        
        :param output_path: File path to save to. If None, overwrites original.
        """
        if output_path is None:
            output_path = self.ontology_path
            
        try:
            self.graph.serialize(destination=output_path, format="turtle")
            log.info(f"Graph successfully saved to {output_path}")
        except Exception as e:
            log.error(f"Error saving graph: {e}")

    def add_triple(self, subject: str, predicate: str, obj: str) -> None:
        """
        Add a triple to the ontology using a SPARQL UPDATE.
        Assumes subject, predicate, and object are in valid Turtle syntax
        (e.g., ":MySubject", ":hasProperty", ":MyObject" or "<uri>" or "literal").
        """
        try:
            query = f"INSERT DATA {{ {subject} {predicate} {obj} . }}"
            self.graph.update(query)
            log.debug(f"Added triple: {subject} {predicate} {obj}")
        except Exception as e:
            log.error(f"Error adding triple via SPARQL update: {e}")

    def remove_triple(self, subject: str, predicate: str, obj: str) -> None:
        """
        Remove a triple from the ontology using a SPARQL UPDATE.
        """
        try:
            query = f"DELETE DATA {{ {subject} {predicate} {obj} . }}"
            self.graph.update(query)
            log.debug(f"Removed triple: {subject} {predicate} {obj}")
        except Exception as e:
            log.error(f"Error removing triple via SPARQL update: {e}")

    def query_graph(self, sparql_query: str) -> list:
        """
        Run a SPARQL SELECT query and return bindings as a list of dicts.
        """
        try:
            log.debug(f"Executing SPARQL query:\n{sparql_query}")
            results = self.graph.query(sparql_query)
            
            # Convert results to a standard list of dictionaries
            bindings = []
            for row in results:
                bindings.append(row.asdict())
                
            return bindings
        except Exception as e:
            log.error(f"Error executing SPARQL query: {e}")
            return []