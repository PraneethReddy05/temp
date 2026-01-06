import logging
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, OWL, RDFS

log = logging.getLogger(__name__)

class OntologyManager:
    """
    Manages loading, querying, and updating the RDFLib graph.
    Updated for Stage 4 to support Transactional Validation (Cloning & Merging).
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
        
        # Define a base namespace for your ontology
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
            # Parse base ontology
            self.graph.parse(self.ontology_path, format="turtle")
            log.info(f"Successfully loaded base ontology from {self.ontology_path}")
            
            # Parse instance data if exists
            if self.instance_data_path:
                try:
                    self.graph.parse(self.instance_data_path, format="turtle")
                    log.info(f"Successfully loaded instance data from {self.instance_data_path}")
                except FileNotFoundError:
                    log.warning(f"Instance data file not found at {self.instance_data_path}. Starting with empty instance data.")
                
            log.info(f"Graph contains {len(self.graph)} triples.")
            
        except FileNotFoundError as e:
            log.error(f"Error loading ontology file: {e}. Please check paths.")
        except Exception as e:
            log.error(f"Error parsing graph: {e}")

    def clone_graph(self) -> Graph:
        """
        Stage 4 Requirement:
        Creates a deep copy of the current graph for validation sandboxing.
        
        :return: A new RDFLib Graph object containing all current triples and namespaces.
        """
        new_graph = Graph()
        
        # Copy all triples
        for triple in self.graph:
            new_graph.add(triple)
            
        # Bind the same namespaces
        for prefix, namespace in self.graph.namespaces():
            new_graph.bind(prefix, namespace)
            
        return new_graph

    def merge_graph(self, validated_graph: Graph) -> None:
        """
        Stage 4 Requirement:
        Updates the main graph with the validated graph and persists changes.
        
        :param validated_graph: The sandbox graph that passed validation.
        """
        # Replace current graph with the validated one
        self.graph = validated_graph
        # Persist immediately
        self.save_graph()
        log.info("Merged validated graph into main ontology and saved.")

    def save_graph(self, output_path: str = None) -> None:
        """
        Persist the updated ontology graph to a file.
        
        :param output_path: File path to save to. If None, overwrites original.
        """
        if output_path is None:
            # We usually save updates to the instance data file to keep base ontology clean
            # But for this simple Phase, we default to the ontology path or instance path
            output_path = self.ontology_path
            
        try:
            self.graph.serialize(destination=output_path, format="turtle")
            log.info(f"Graph successfully saved to {output_path}")
        except Exception as e:
            log.error(f"Error saving graph: {e}")

    def add_triple(self, subject: str, predicate: str, obj: str) -> None:
        """
        Add a triple to the ontology using a SPARQL UPDATE.
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
                # Convert rdflib terms to strings for easier handling in JSON
                binding = {}
                for var in results.vars:
                    if row[var] is not None:
                        binding[str(var)] = str(row[var])
                bindings.append(binding)
                
            return bindings
        except Exception as e:
            log.error(f"Error executing SPARQL query: {e}")
            return []
        
    