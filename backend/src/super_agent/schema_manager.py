import logging
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib import RDF, RDFS, OWL, XSD
from src.ontology_manager import OntologyManager

log = logging.getLogger(__name__)

class SchemaManager:
    """
    Safely modifies the ontology schema (TBox) by adding new
    classes, properties, and datatypes.
    
    This manager operates on the graph provided by an OntologyManager
    to ensure there is a single source of truth.
    """
    def __init__(self, ontology_manager: OntologyManager):
        """
        Initialize with an active OntologyManager.
        
        :param ontology_manager: The singleton OntologyManager instance.
        """
        self.ontology_manager = ontology_manager
        self.graph = ontology_manager.graph
        self.base_ns = ontology_manager.base_ns
        log.info("SchemaManager initialized.")

    # def _get_uri(self, name: str, namespace=None):
    #     """Helper to create a full URI from a prefixed name or plain name."""
    #     if ":" in name:
    #         prefix, local = name.split(":", 1)
    #         if prefix == "": # e.g., ":MyClass"
    #             return self.base_ns[local]
    #         # Use rdflib's built-in namespace manager
    #         return self.graph.namespace_manager.namespace(prefix)[local]
    #     # Assume it's a new local name
    #     return self.base_ns[name]

    def _get_uri(self, name: str, namespace=None):
        """Helper to create a full URI from a prefixed name or full URI."""
        
        # --- NEW LOGIC ---
        # Check if it's already a full URI
        if name.startswith('http://') or name.startswith('https://'):
            return URIRef(name)
        # --- END NEW LOGIC ---

        if ":" in name:
            prefix, local = name.split(":", 1)
            if prefix == "":  # e.g., ":MyClass"
                return self.base_ns[local]

            # (Rest of the prefix logic is the same)
            if prefix == 'xsd':
                return XSD[local]
            if prefix == 'rdf':
                return RDF[local]
            if prefix == 'rdfs':
                return RDFS[local]
            if prefix == 'owl':
                return OWL[local]

            for p, ns_uri in self.graph.namespace_manager.namespaces():
                if p == prefix:
                    return Namespace(ns_uri)[local]
            
            raise ValueError(f"Prefix '{prefix}' not found in NamespaceManager.")

        # Assume it's a new local name
        return self.base_ns[name]

    def add_class(self, class_name: str, parent: str = "owl:Thing", label: str = None):
        """
        Add a new OWL class with an optional parent.
        
        :param class_name: The name for the new class (e.g., "Grant" or ":Grant").
        :param parent: The parent class (e.g., "owl:Thing" or ":Project").
        :param label: A human-readable rdfs:label.
        """
        class_uri = self._get_uri(class_name)
        parent_uri = self._get_uri(parent)
        
        self.graph.add((class_uri, RDF.type, OWL.Class))
        self.graph.add((class_uri, RDFS.subClassOf, parent_uri))
        
        if label:
            self.graph.add((class_uri, RDFS.label, Literal(label, lang="en")))
        else:
            self.graph.add((class_uri, RDFS.label, Literal(class_name.replace("_", " "), lang="en")))
            
        log.info(f"Added Class: {class_uri} (subClassOf {parent_uri})")

    def add_object_property(self, prop_name: str, domain: str, range_: str, label: str = None):
        """
        Add a new object property with domain and range.
        
        :param prop_name: The name for the property (e.g., "hasFunding").
        :param domain: The domain class (e.g., ":Paper").
        :param range_: The range class (e.g., ":Grant").
        :param label: A human-readable rdfs:label.
        """
        prop_uri = self._get_uri(prop_name)
        domain_uri = self._get_uri(domain)
        range_uri = self._get_uri(range_)

        self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
        self.graph.add((prop_uri, RDFS.domain, domain_uri))
        self.graph.add((prop_uri, RDFS.range, range_uri))

        if label:
            self.graph.add((prop_uri, RDFS.label, Literal(label, lang="en")))
        else:
            self.graph.add((prop_uri, RDFS.label, Literal(prop_name.replace("_", " "), lang="en")))

        log.info(f"Added ObjectProperty: {prop_uri} (domain: {domain_uri}, range: {range_uri})")

    def add_datatype_property(self, prop_name: str, domain: str, range_: str, label: str = None):
        """
        Add a new datatype property with domain and XSD type.
        
        :param prop_name: The name for the property (e.g., "hasPageCount").
        :param domain: The domain class (e.g., ":Paper").
        :param range_: The XSD datatype (e.g., "xsd:int" or "xsd:string").
        :param label: A human-readable rdfs:label.
        """
        prop_uri = self._get_uri(prop_name)
        domain_uri = self._get_uri(domain)
        range_uri = self._get_uri(range_) # e.g., _get_uri("xsd:int") -> XSD.int

        self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        self.graph.add((prop_uri, RDFS.domain, domain_uri))
        self.graph.add((prop_uri, RDFS.range, range_uri))
        
        if label:
            self.graph.add((prop_uri, RDFS.label, Literal(label, lang="en")))
        else:
            self.graph.add((prop_uri, RDFS.label, Literal(prop_name.replace("_", " "), lang="en")))

        log.info(f"Added DatatypeProperty: {prop_uri} (domain: {domain_uri}, range: {range_uri})")

    def save(self) -> None:
        """
        Persist the updated ontology by calling the OntologyManager's save method.
        """
        log.info("Saving schema updates via OntologyManager...")
        self.ontology_manager.save_graph()