import pkg_resources

try:
    rdf_version = pkg_resources.get_distribution('rdflib').version
    parse_version = pkg_resources.get_distribution('pyparsing').version
    
    print(f"RDFLib: {rdf_version}")
    print(f"Pyparsing: {parse_version}")
    
    if rdf_version.startswith('7') and parse_version.startswith('3'):
        print("✅ SUCCESS: Compatible versions installed.")
    else:
        print("❌ ERROR: Still on old versions. Please run the pip commands again.")
        
except Exception as e:
    print(f"Error: {e}")