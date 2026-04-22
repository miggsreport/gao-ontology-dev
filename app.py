import streamlit as st
import rdflib
from rdflib import Namespace, URIRef
from pathlib import Path
import pandas as pd
from io import BytesIO
import re

# Set page config
st.set_page_config(
    page_title="Demo AFR Test Site",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add custom CSS for styling to match AFR site
st.markdown("""
<style>
    /* Header styling - title and badge inline */
    .header-row {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 10px;
    }
    .header-title {
        color: #002147;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    .demo-test-badge {
        background-color: #FFD700;
        color: #002147;
        padding: 6px 14px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.9rem;
        display: inline-block;
        vertical-align: middle;
    }
    
    /* Section header styling */
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #002147;
        margin-bottom: 8px;
    }
    
    /* Comparison section header */
    .comparison-section-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #002147;
        margin-top: 20px;
        margin-bottom: 15px;
        padding: 12px 0;
        border-top: 4px solid #FFD700;
        background: linear-gradient(to bottom, #fffbea 0%, transparent 100%);
    }
    
    /* Tab styling - blue theme with borders */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        margin-top: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 500;
        padding: 10px 16px;
        border: 2px solid #ccc;
        border-radius: 6px 6px 0 0;
        background-color: #f8f8f8;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e8e8e8;
        border-color: #002147;
    }
    .stTabs [aria-selected="true"] {
        background-color: #fff;
        border-color: #002147;
        border-bottom-color: #fff;
        color: #002147;
    }
    
    /* Button styling to match AFR */
    .stButton > button {
        background-color: #3d6a99;
        color: white;
        border: none;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.9rem;
    }
    .stButton > button:hover {
        background-color: #002147;
        color: white;
    }
    
    /* Success message styling */
    .stSuccess {
        margin-bottom: 8px;
    }
    
    /* Note styling for comparison section */
    .comparison-note {
        font-size: 0.65rem;
        font-style: italic;
        color: #888;
        margin-top: 10px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Header with title and TEST badge inline
st.markdown('<div class="header-row"><span class="header-title">The GAO Antifraud Resource</span><span class="demo-test-badge">DEMO TEST SITE</span></div>', unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# CONFIGURATION
# =============================================================================
TAB_CONFIG = [
    ("FederalFraudScheme", "Fraud Scheme Examples"),
    ("FraudEducation", "Fraud Awareness Resources"),
    ("FraudDetection", "Fraud Prevention & Detection Guidance"),
    ("FraudRiskManagementPrinciples", "Fraud Risk Mgmt Principles"),
    ("AuditProduct", "GAO Reports"),
]

# GFO Namespace
GFO_URI = "https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/"
GFO = Namespace(GFO_URI)

# =============================================================================
# SIDEBAR - Ontology Management & Settings
# =============================================================================
with st.sidebar:
    st.header("Ontology Management")
    
    if 'ontology' in st.session_state and st.session_state.ontology:
        st.success("Ontology Loaded")
        st.markdown(f"**File:** {st.session_state.loaded_file}")
        triple_count = len(st.session_state.ontology)
        st.markdown(f"**Triples:** {triple_count:,}")
        st.markdown(f"**Fraud Activities:** {len(st.session_state.fraud_activity_mapping)}")
        
        st.markdown("---")
        st.markdown("**Upload Different Ontology**")
    
    uploaded_file = st.file_uploader(
        "Select file", 
        type=['owl', 'rdf', 'ttl', 'n3', 'jsonld'],
        help="Upload an ontology file",
        label_visibility="collapsed"
    )

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if 'ontology' not in st.session_state:
    st.session_state.ontology = None
if 'loaded_file' not in st.session_state:
    st.session_state.loaded_file = None
if 'fraud_activity_mapping' not in st.session_state:
    st.session_state.fraud_activity_mapping = {}
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'current_fraud_activity' not in st.session_state:
    st.session_state.current_fraud_activity = None
if 'current_fraud_activity_label' not in st.session_state:
    st.session_state.current_fraud_activity_label = None
if 'comparison_dfs' not in st.session_state:
    st.session_state.comparison_dfs = None
if 'comparison_summary' not in st.session_state:
    st.session_state.comparison_summary = None

# =============================================================================
# ONTOLOGY LOADING FUNCTIONS
# =============================================================================
@st.cache_resource
def load_ontology_rdflib(file_path):
    try:
        g = rdflib.Graph()
        if file_path.endswith('.ttl'):
            g.parse(file_path, format="turtle")
        elif file_path.endswith('.rdf') or file_path.endswith('.xml'):
            g.parse(file_path, format="xml")
        elif file_path.endswith('.jsonld'):
            g.parse(file_path, format="json-ld")
        else:
            g.parse(file_path)
        return g
    except Exception as e:
        st.error(f"Error loading ontology: {str(e)}")
        return None

def load_fraud_activities(ontology_graph):
    """Dynamically query the ontology for direct (top-level) FraudActivity subclasses only."""
    sparql_query = """
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?fraudActivity ?fraudActivityLabel
WHERE {
    ?fraudActivity rdfs:subClassOf gfo:FraudActivity .
    ?fraudActivity rdfs:label ?fraudActivityLabel .
}
"""
    try:
        results = list(ontology_graph.query(sparql_query))
        
        fraud_activity_mapping = {}
        for row in results:
            full_uri = str(row.fraudActivity)
            local_name = full_uri.split("/")[-1].split("#")[-1]
            label = str(row.fraudActivityLabel)
            display_label = label.capitalize() if label else local_name
            fraud_activity_mapping[display_label] = local_name
        
        sorted_mapping = dict(sorted(fraud_activity_mapping.items(), key=lambda x: x[0].lower()))
        return sorted_mapping
    
    except Exception as e:
        st.error(f"Error loading fraud activities: {str(e)}")
        return {}

def load_default_ontology():
    script_dir = Path(__file__).parent
    default_ontology_path = script_dir / "gfo_turtle.ttl"
    
    if default_ontology_path.exists():
        try:
            st.session_state.ontology = load_ontology_rdflib(str(default_ontology_path))
            st.session_state.loaded_file = "gfo_turtle.ttl (default)"
            st.session_state.uploaded_file_path = str(default_ontology_path)
            
            if st.session_state.ontology:
                st.session_state.fraud_activity_mapping = load_fraud_activities(st.session_state.ontology)
                return True
        except Exception as e:
            pass
    return False

# =============================================================================
# DEMO APP QUERIES (Current implementation - owl:someValuesFrom approach)
# =============================================================================
def query_fraud_schemes(ontology_graph, fraud_activity):
    """
    Query for FederalFraudScheme instances related to a specific FraudActivity.
    UNION future-proofs against different modeling patterns:
    Path 1: owl:someValuesFrom restrictions | Path 2: direct subclass typing
    """
    query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT ?individual ?individualName ?description ?fraudNarrative ?isDefinedBy ?objectPropertyName
WHERE {{
    ?individual a gfo:FederalFraudScheme ;
                rdfs:label ?individualName .
    
    OPTIONAL {{ ?individual dc:description ?description . }}
    OPTIONAL {{ ?individual gfo:fraudNarrative ?fraudNarrative . }}
    OPTIONAL {{ ?individual rdfs:isDefinedBy ?isDefinedBy . }}
    
    {{
        ?individual a ?restrictionClass .
        ?restrictionClass owl:onProperty ?objectProperty ;
                          owl:someValuesFrom ?relatedClass .
        ?relatedClass rdfs:subClassOf* gfo:{fraud_activity} .
        BIND(REPLACE(STR(?objectProperty), "^.*/", "") AS ?objectPropertyName)
    }}
    UNION
    {{
        ?individual a ?schemeSubClass .
        ?schemeSubClass rdfs:subClassOf* gfo:{fraud_activity} .
        FILTER(?schemeSubClass != gfo:FederalFraudScheme)
        BIND("directSubclass" AS ?objectPropertyName)
    }}
}}
"""
    return list(ontology_graph.query(query))


def query_resource_instances(ontology_graph, resource_class, fraud_activity):
    """
    Dynamically query for instances of a resource class related to a specific FraudActivity.
    Uses property-agnostic owl:someValuesFrom matching.
    """
    query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?individual ?individualName ?definition ?website ?isDefinedBy
WHERE {{
    ?individual a ?instanceClass .
    ?instanceClass rdfs:subClassOf* gfo:{resource_class} .
    
    ?individual rdfs:label ?individualName .
    
    OPTIONAL {{ ?individual skos:definition ?definition . }}
    OPTIONAL {{ ?individual gfo:hasWebsite ?website . }}
    OPTIONAL {{ ?individual rdfs:isDefinedBy ?isDefinedBy . }}
    
    {{
        ?individual a ?someClass .
        ?someClass owl:someValuesFrom ?specificFraud .
        ?specificFraud rdfs:subClassOf* gfo:{fraud_activity} .
    }}
    UNION
    {{
        ?individual a ?resourceSubClass .
        ?resourceSubClass rdfs:subClassOf* gfo:{fraud_activity} .
        FILTER(?resourceSubClass != gfo:{resource_class})
    }}
}}
ORDER BY LCASE(STR(?individualName))
"""
    return list(ontology_graph.query(query))


def process_fraud_scheme_results(results):
    """Process and deduplicate fraud scheme query results."""
    seen_individuals = {}
    for row in results:
        individual_uri = str(row.individual)
        property_name = str(row.objectPropertyName) if row.objectPropertyName else "unknown"
        
        if individual_uri not in seen_individuals:
            seen_individuals[individual_uri] = {
                'individual': row.individual,
                'individualName': str(row.individualName),
                'description': str(row.description) if row.description else None,
                'fraudNarrative': str(row.fraudNarrative) if row.fraudNarrative else None,
                'isDefinedBy': str(row.isDefinedBy) if row.isDefinedBy else None,
                'objectProperties': set()
            }
        seen_individuals[individual_uri]['objectProperties'].add(property_name)
    
    return sorted(seen_individuals.values(), key=lambda x: x['individualName'].lower())


# =============================================================================
# ORIGINAL AFR LOGIC (Strict Replication - EXACT MATCH ONLY, NO SUBCLASS TRAVERSAL)
# =============================================================================
# BUG REPLICATION: The live AFR site does EXACT string matching only when filtering
# results by fraud activity. It does NOT traverse the subclass hierarchy.
# For example, when searching for "ConfidenceFraud":
#   - Finds schemes linked directly to gfo:ConfidenceFraud ✓
#   - Does NOT find schemes linked to gfo:AffinityFraud (even though AffinityFraud 
#     is a subclass of ConfidenceFraud) ✗
# =============================================================================

def query_fraud_schemes_original_afr(ontology_graph, fraud_activity):
    """
    Replicate original AFR query logic for FederalFraudScheme.
    BUG REPLICATION: Uses EXACT MATCH ONLY - does not traverse subclass hierarchy.
    """
    # EXACT MATCH ONLY - only the selected fraud activity, no subclasses
    fraud_activity_uri = f"{GFO_URI}{fraud_activity}"
    
    # Get all FederalFraudScheme instances
    instances_query = """
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?instance ?label
WHERE {
    ?instance a gfo:FederalFraudScheme .
    ?instance rdfs:label ?label .
}
"""
    instances = list(ontology_graph.query(instances_query))
    
    results = []
    
    for row in instances:
        instance_uri = str(row.instance)
        instance_label = str(row.label)
        local_name = instance_uri.split("/")[-1]
        
        # Query 1: All direct properties (original AFR pattern)
        props_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?property ?value
WHERE {{
    gfo:{local_name} ?property ?value .
    FILTER(?property != rdf:type)
}}
"""
        props = list(ontology_graph.query(props_query))
        
        # Query 2: Restriction-based relationships (original query5 pattern)
        restriction_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?target
WHERE {{
    gfo:{local_name} a ?restrictionClass .
    ?restrictionClass ?prop ?target .
    FILTER(?prop != owl:onProperty && ?prop != rdf:type)
    FILTER(isURI(?target))
    {{ ?target a owl:Class }} UNION {{ ?target a owl:NamedIndividual }}
}}
"""
        restrictions = list(ontology_graph.query(restriction_query))
        
        # EXACT MATCH ONLY - check if any property value matches the fraud activity URI exactly
        found_relationship = False
        linked_properties = set()
        
        for prop_row in props:
            value_uri = str(prop_row.value)
            # EXACT MATCH - only matches if value is exactly the selected fraud activity
            if value_uri == fraud_activity_uri:
                found_relationship = True
                prop_name = str(prop_row.property).split("/")[-1].split("#")[-1]
                linked_properties.add(prop_name)
        
        for rest_row in restrictions:
            target_uri = str(rest_row.target)
            # EXACT MATCH - only matches if restriction target is exactly the selected fraud activity
            if target_uri == fraud_activity_uri:
                found_relationship = True
                linked_properties.add("owl:someValuesFrom")
        
        if found_relationship:
            # Get metadata
            metadata_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?description ?fraudNarrative ?isDefinedBy
WHERE {{
    OPTIONAL {{ gfo:{local_name} dc:description ?description }}
    OPTIONAL {{ gfo:{local_name} gfo:fraudNarrative ?fraudNarrative }}
    OPTIONAL {{ gfo:{local_name} rdfs:isDefinedBy ?isDefinedBy }}
}}
"""
            metadata = list(ontology_graph.query(metadata_query))
            meta = metadata[0] if metadata else None
            
            results.append({
                'individual': row.instance,
                'individualName': instance_label,
                'description': str(meta.description) if meta and meta.description else None,
                'fraudNarrative': str(meta.fraudNarrative) if meta and meta.fraudNarrative else None,
                'isDefinedBy': str(meta.isDefinedBy) if meta and meta.isDefinedBy else None,
                'objectProperties': linked_properties
            })
    
    return sorted(results, key=lambda x: x['individualName'].lower())


def query_resource_instances_original_afr(ontology_graph, resource_class, fraud_activity):
    """
    Replicate original AFR query logic for resource instances.
    BUG REPLICATION: Uses EXACT MATCH ONLY - does not traverse subclass hierarchy.
    """
    # EXACT MATCH ONLY - only the selected fraud activity, no subclasses
    fraud_activity_uri = f"{GFO_URI}{fraud_activity}"
    
    # Get resource class hierarchy (original uses 2 levels for resources)
    resource_classes = {f"{GFO_URI}{resource_class}"}
    
    # Level 1 subclasses
    level1_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subclass
WHERE {{
    ?subclass rdfs:subClassOf gfo:{resource_class} .
}}
"""
    for row in ontology_graph.query(level1_query):
        resource_classes.add(str(row.subclass))
        
        # Level 2 subclasses
        local = str(row.subclass).split("/")[-1]
        level2_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subclass
WHERE {{
    ?subclass rdfs:subClassOf gfo:{local} .
}}
"""
        for row2 in ontology_graph.query(level2_query):
            resource_classes.add(str(row2.subclass))
    
    # Get all instances of those resource classes
    instances_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?instance ?label ?class
WHERE {{
    ?instance a ?class .
    ?instance rdfs:label ?label .
    FILTER(?class IN ({', '.join([f'<{c}>' for c in resource_classes])}))
}}
"""
    instances = list(ontology_graph.query(instances_query))
    
    results = []
    seen_instances = set()
    
    for row in instances:
        instance_uri = str(row.instance)
        if instance_uri in seen_instances:
            continue
            
        instance_label = str(row.label)
        local_name = instance_uri.split("/")[-1]
        
        # Query all properties (original AFR pattern)
        props_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?property ?value
WHERE {{
    gfo:{local_name} ?property ?value .
    FILTER(?property != rdf:type)
}}
"""
        props = list(ontology_graph.query(props_query))
        
        # Query restriction-based relationships
        restriction_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?target
WHERE {{
    gfo:{local_name} a ?restrictionClass .
    ?restrictionClass ?prop ?target .
    FILTER(?prop != owl:onProperty && ?prop != rdf:type)
    FILTER(isURI(?target))
}}
"""
        restrictions = list(ontology_graph.query(restriction_query))
        
        # EXACT MATCH ONLY - check for fraud activity relationship
        found_relationship = False
        
        for prop_row in props:
            value_uri = str(prop_row.value)
            # EXACT MATCH - only matches if value is exactly the selected fraud activity
            if value_uri == fraud_activity_uri:
                found_relationship = True
                break
        
        if not found_relationship:
            for rest_row in restrictions:
                target_uri = str(rest_row.target)
                # EXACT MATCH - only matches if restriction target is exactly the selected fraud activity
                if target_uri == fraud_activity_uri:
                    found_relationship = True
                    break
        
        if found_relationship:
            seen_instances.add(instance_uri)
            
            # Get metadata
            metadata_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?definition ?website ?isDefinedBy
WHERE {{
    OPTIONAL {{ gfo:{local_name} skos:definition ?definition }}
    OPTIONAL {{ gfo:{local_name} gfo:hasWebsite ?website }}
    OPTIONAL {{ gfo:{local_name} rdfs:isDefinedBy ?isDefinedBy }}
}}
"""
            metadata = list(ontology_graph.query(metadata_query))
            meta = metadata[0] if metadata else None
            
            results.append({
                'individual': row.instance,
                'individualName': instance_label,
                'definition': str(meta.definition) if meta and meta.definition else None,
                'website': str(meta.website) if meta and meta.website else None,
                'isDefinedBy': str(meta.isDefinedBy) if meta and meta.isDefinedBy else None
            })
    
    return sorted(results, key=lambda x: x['individualName'].lower())


def query_all_fraud_risk_mgmt_principles(ontology_graph):
    """
    Query ALL FraudRiskManagementPrinciples instances regardless of fraud activity.
    Design decision: These are general guidance resources applicable to all fraud types.
    """
    query = """
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?instance ?label ?definition ?website ?isDefinedBy
WHERE {
    ?instance a ?class .
    ?class rdfs:subClassOf* gfo:FraudRiskManagementPrinciples .
    ?instance rdfs:label ?label .
    
    OPTIONAL { ?instance skos:definition ?definition }
    OPTIONAL { ?instance gfo:hasWebsite ?website }
    OPTIONAL { ?instance rdfs:isDefinedBy ?isDefinedBy }
}
ORDER BY LCASE(STR(?label))
"""
    results = list(ontology_graph.query(query))
    
    return [{
        'individual': str(row.instance),
        'individualName': str(row.label),
        'definition': str(row.definition) if row.definition else None,
        'website': str(row.website) if row.website else None,
        'isDefinedBy': str(row.isDefinedBy) if row.isDefinedBy else None
    } for row in results]



# =============================================================================
# COMPARISON LOGIC
# =============================================================================
def compare_results(dev_results, afr_results):
    """
    Compare results from two sources and categorize each instance.
    Returns a DataFrame with comparison data.
    """
    def get_names(results):
        if isinstance(results, dict) and 'error' in results:
            return set()
        return {r['individualName'] for r in results}
    
    def get_result_dict(results):
        if isinstance(results, dict) and 'error' in results:
            return {}
        return {r['individualName']: r for r in results}
    
    dev_names = get_names(dev_results)
    afr_names = get_names(afr_results)
    
    dev_dict = get_result_dict(dev_results)
    afr_dict = get_result_dict(afr_results)
    
    all_names = dev_names | afr_names
    
    comparison_data = []
    for name in sorted(all_names, key=str.lower):
        in_dev = name in dev_names
        in_afr = name in afr_names
        
        # Determine status
        if in_dev and in_afr:
            status = "Both"
        elif in_dev:
            status = "Demo AFR Site Only"
        else:
            status = "AFR Site Only"
        
        # Get description from whichever source has it
        description = None
        if in_dev and dev_dict[name].get('description'):
            description = dev_dict[name]['description']
        elif in_afr and afr_dict[name].get('description'):
            description = afr_dict[name]['description']
        
        # Get linked properties
        linked_props = None
        if in_dev and 'objectProperties' in dev_dict[name]:
            linked_props = ", ".join(sorted(dev_dict[name]['objectProperties']))
        elif in_afr and 'objectProperties' in afr_dict[name]:
            linked_props = ", ".join(sorted(afr_dict[name]['objectProperties']))
        
        comparison_data.append({
            'Instance Name': name,
            'Demo AFR Site': '✓' if in_dev else '',
            'AFR Site': '✓' if in_afr else '',
            'Status': status,
            'Description': description[:100] + '...' if description and len(description) > 100 else description,
            'Linked Properties': linked_props
        })
    
    return pd.DataFrame(comparison_data)


def generate_summary_stats(comparison_dfs, fraud_activity_label):
    """Generate summary statistics for the comparison."""
    summary_data = []
    
    for facet_name, df in comparison_dfs.items():
        if df.empty:
            summary_data.append({
                'Facet': facet_name,
                'Demo AFR Site Count': 0,
                'AFR Site Count': 0
            })
        else:
            dev_count = (df['Demo AFR Site'] == '✓').sum()
            afr_count = (df['AFR Site'] == '✓').sum()
            
            summary_data.append({
                'Facet': facet_name,
                'Demo AFR Site Count': dev_count,
                'AFR Site Count': afr_count
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Add totals row
    totals = summary_df.sum(numeric_only=True)
    totals['Facet'] = 'TOTAL'
    summary_df = pd.concat([summary_df, pd.DataFrame([totals])], ignore_index=True)
    
    return summary_df


def create_excel_export(comparison_dfs, summary_df, fraud_activity_label):
    """Create Excel file with comparison results."""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet first
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Add methodology notes
        methodology_df = pd.DataFrame({
            'Source': [
                'GAO Antifraud Resource Demo Test Site', 
                'GAO Antifraud Resource', 
                'Known Live Site Anomaly'
            ],
            'Description': [
                'Test site implementation using improved SPARQL queries with property-agnostic owl:someValuesFrom patterns and unlimited hierarchy depth (rdfs:subClassOf*). This is how the search SHOULD work.',
                'Replication of the original Lambda code logic from the live GAO Antifraud Resource site. This demonstrates the BUGS in the current live implementation.',
                'Observed behavior on the live site that cannot be explained by the Lambda code and is NOT replicated in this comparison.'
            ],
            'Query Approach': [
                'Finds instances whose class has ANY restriction (regardless of property name) pointing to the selected fraud activity OR any of its subclasses at any depth level. Exception: Fraud Risk Management Principles shows all instances (not filtered by fraud activity).',
                'EXACT MATCH ONLY - does not traverse the fraud activity subclass hierarchy when filtering results. Fraud Risk Management Principles shows ALL instances regardless of selection.',
                'N/A - This is an unexplained anomaly, not a query approach.'
            ],
            'Impact': [
                'Properly finds relationships through subclass hierarchy. Example: When searching "Confidence Fraud", also finds schemes linked to AffinityFraud (which is a subclass of ConfidenceFraud). Fraud Risk Mgmt Principles: Both sites show all ~20 instances (design decision - these are general guidance applicable to all fraud types).',
                'BUG: Only finds items linked DIRECTLY to the selected fraud activity URI, missing items linked to subclasses.',
                'Oversight.gov appears in Fraud Awareness Resources on live site for all searches, but it is typed as InspectorGeneralProduct (subclass of AuditProduct) so should appear in GAO Reports.'
            ]
        })
        methodology_df.to_excel(writer, sheet_name='Methodology Notes', index=False)
        
        # Individual facet sheets
        for facet_name, df in comparison_dfs.items():
            # Truncate sheet name to 31 chars (Excel limit)
            sheet_name = facet_name[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    return output.getvalue()


# =============================================================================
# DISPLAY FUNCTIONS
# =============================================================================
def display_fraud_schemes(schemes, fraud_activity_label):
    """Display fraud scheme results in expanders."""
    if schemes:
        for i, result in enumerate(schemes):
            scheme_name = result['individualName']
            fraud_description = result['description'] if result['description'] else "No description available"
            fraud_narrative = result['fraudNarrative'] if result['fraudNarrative'] else "No fraud narrative available"
            is_defined_by_url = result['isDefinedBy'] if result['isDefinedBy'] else "No definition source available"
            
            properties_list = sorted(result['objectProperties'])
            properties_display = ", ".join(properties_list)
            
            with st.expander(f"{i+1}. {scheme_name}"):
                st.write(f"**Fraud Description:** {fraud_description}")
                st.write("**Fraud Narrative:**")
                st.text(fraud_narrative)
                st.write(f"**Related to:** {fraud_activity_label}")
                st.write(f"**Linked via:** {properties_display}")
                st.caption(f"Source: {is_defined_by_url}")
    else:
        st.info("No fraud scheme examples found for this fraud activity.")


def display_resource_results(results, fraud_activity_label, empty_message):
    """Display resource query results in expanders."""
    if results:
        for i, row in enumerate(results):
            resource_name = str(row.individualName) if hasattr(row, 'individualName') else row['individualName']
            definition = str(row.definition) if (hasattr(row, 'definition') and row.definition) else (row.get('definition') or "No definition available")
            website = str(row.website) if (hasattr(row, 'website') and row.website) else (row.get('website') or "")
            is_defined_by_url = str(row.isDefinedBy) if (hasattr(row, 'isDefinedBy') and row.isDefinedBy) else (row.get('isDefinedBy') or "No definition source available")
            
            with st.expander(f"{i+1}. {resource_name}"):
                st.write(f"**Definition:** {definition}")
                if website:
                    st.write(f"**Website:** {website}")
                st.write(f"**Related to:** {fraud_activity_label}")
                st.caption(f"Source: {is_defined_by_url}")
    else:
        st.info(empty_message)


def display_comparison_table(df, is_fraud_scheme=False):
    """Display comparison DataFrame as a styled table."""
    if df.empty:
        st.info("No results to compare.")
        return
    
    # Select columns to display - only show Description/Linked Properties for fraud schemes
    display_cols = ['Instance Name', 'Demo AFR Site', 'AFR Site', 'Status']
    if is_fraud_scheme:
        if 'Description' in df.columns:
            display_cols.append('Description')
        if 'Linked Properties' in df.columns:
            display_cols.append('Linked Properties')
    
    # Style the dataframe
    def highlight_status(val):
        if val == 'Both':
            return 'background-color: #d4edda'  # Green - both sources agree
        elif val == 'Demo AFR Site Only':
            return 'background-color: #cce5ff'  # Blue - found by improved queries
        elif val == 'AFR Site Only':
            return 'background-color: #fff3cd'  # Yellow - only in buggy original
        return ''
    
    styled_df = df[display_cols].style.map(
        highlight_status, subset=['Status']
    )
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)


# =============================================================================
# MAIN APPLICATION
# =============================================================================

# Auto-load default ontology
if st.session_state.ontology is None:
    load_default_ontology()

# Handle file upload from sidebar
if uploaded_file is not None and uploaded_file.name != st.session_state.loaded_file:
    temp_path = f"/tmp/{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.session_state.ontology = load_ontology_rdflib(temp_path)
    st.session_state.loaded_file = uploaded_file.name
    st.session_state.uploaded_file_path = temp_path
    
    if st.session_state.ontology:
        st.session_state.fraud_activity_mapping = load_fraud_activities(st.session_state.ontology)
        st.rerun()

# Main interface
if st.session_state.ontology:
    
    st.markdown('<p class="section-header">Fraud type search</p>', unsafe_allow_html=True)
    
    fraud_activity_mapping = st.session_state.fraud_activity_mapping
    
    if not fraud_activity_mapping:
        st.warning("No fraud activities found in ontology. Please check that the ontology is properly loaded.")
        fraud_activity_mapping = {}
    
    fraud_activity_label = st.selectbox(
        "What type of fraud do you want to combat?",
        options=list(fraud_activity_mapping.keys()),
        help="Choose a fraud type to find all related resources"
    )
    
    fraud_activity = fraud_activity_mapping.get(fraud_activity_label)
    
    if st.button("Search All Resources"):
        if fraud_activity_label and fraud_activity:
            
            # Execute all queries
            try:
                # Query for FederalFraudScheme (existing working query)
                fraud_scheme_results = query_fraud_schemes(st.session_state.ontology, fraud_activity)
                fraud_schemes = process_fraud_scheme_results(fraud_scheme_results)
                
                # Query for each resource class dynamically
                resource_results = {}
                for class_name, display_label in TAB_CONFIG[1:]:  # Skip FederalFraudScheme
                    # FraudRiskManagementPrinciples: show all instances (not filtered by fraud activity)
                    if class_name == "FraudRiskManagementPrinciples":
                        resource_results[class_name] = query_all_fraud_risk_mgmt_principles(
                            st.session_state.ontology
                        )
                    else:
                        resource_results[class_name] = query_resource_instances(
                            st.session_state.ontology, 
                            class_name, 
                            fraud_activity
                        )
                
                # Store results in session state for display and comparison
                st.session_state.search_results = {
                    'fraud_schemes': fraud_schemes,
                    'resource_results': resource_results
                }
                st.session_state.current_fraud_activity = fraud_activity
                st.session_state.current_fraud_activity_label = fraud_activity_label
                # Clear any previous comparison results when new search is run
                st.session_state.comparison_dfs = None
                st.session_state.comparison_summary = None
                st.session_state.excel_export = None
                    
            except Exception as e:
                st.error(f"[ERROR] SPARQL query failed: {str(e)}")
                st.info("Make sure your ontology file is properly loaded.")
        else:
            st.warning("Please select a fraud type.")
    
    # =============================================================================
    # DISPLAY SEARCH RESULTS (from session state, persists after comparison)
    # =============================================================================
    if st.session_state.search_results:
        fraud_schemes = st.session_state.search_results['fraud_schemes']
        resource_results = st.session_state.search_results['resource_results']
        current_label = st.session_state.current_fraud_activity_label
        
        # Calculate total results
        total_results = len(fraud_schemes) + sum(len(r) for r in resource_results.values())
        
        if total_results > 0:
            st.success(f"Found {total_results} total resources related to {current_label}")
            
            # Create tabs with counts in the configured order
            tab_labels = [
                f"{TAB_CONFIG[0][1]} ({len(fraud_schemes)})",
            ]
            for class_name, display_label in TAB_CONFIG[1:]:
                count = len(resource_results[class_name])
                tab_labels.append(f"{display_label} ({count})")
            
            tabs = st.tabs(tab_labels)
            
            # Tab 1: Fraud Scheme Examples
            with tabs[0]:
                display_fraud_schemes(fraud_schemes, current_label)
            
            # Remaining tabs: Resource classes
            for i, (class_name, display_label) in enumerate(TAB_CONFIG[1:], start=1):
                with tabs[i]:
                    empty_msg = f"No {display_label.lower()} found for this fraud activity."
                    display_resource_results(
                        resource_results[class_name], 
                        current_label,
                        empty_msg
                    )
        else:
            st.info(f"No resources found for {current_label}")
    
    # =============================================================================
    # COMPARISON SECTION
    # =============================================================================
    if st.session_state.search_results:
        
        st.markdown('<p class="comparison-section-header">Search Results Comparison: GAO Antifraud Resource <strong>DEMO TEST SITE</strong> and GAO Antifraud Resource</p>', unsafe_allow_html=True)
        
        if st.button("Run Comparison", type="primary"):
            fraud_activity = st.session_state.current_fraud_activity
            fraud_activity_label = st.session_state.current_fraud_activity_label
            st.session_state.excel_export = None
            
            with st.spinner("Running comparison queries..."):
                comparison_dfs = {}
                    
                # Compare Fraud Schemes
                dev_schemes = st.session_state.search_results['fraud_schemes']
                afr_schemes = query_fraud_schemes_original_afr(
                    st.session_state.ontology, fraud_activity
                )
                
                comparison_dfs['Fraud Scheme Examples'] = compare_results(
                    dev_schemes, afr_schemes
                )
                
                # Compare each resource class
                for class_name, display_label in TAB_CONFIG[1:]:
                    dev_results = st.session_state.search_results['resource_results'][class_name]
                    
                    # Convert query results to dict format for comparison
                    dev_results_dict = []
                    for row in dev_results:
                        dev_results_dict.append({
                            'individual': str(row.individual) if hasattr(row, 'individual') else row.get('individual'),
                            'individualName': str(row.individualName) if hasattr(row, 'individualName') else row.get('individualName'),
                            'definition': str(row.definition) if (hasattr(row, 'definition') and row.definition) else row.get('definition'),
                            'website': str(row.website) if (hasattr(row, 'website') and row.website) else row.get('website'),
                            'isDefinedBy': str(row.isDefinedBy) if (hasattr(row, 'isDefinedBy') and row.isDefinedBy) else row.get('isDefinedBy')
                        })
                    
                    # FraudRiskManagementPrinciples: Both sites show ALL instances
                    # (design decision - general guidance applicable to all fraud types)
                    if class_name == "FraudRiskManagementPrinciples":
                        afr_results = query_all_fraud_risk_mgmt_principles(st.session_state.ontology)
                    else:
                        afr_results = query_resource_instances_original_afr(
                            st.session_state.ontology, class_name, fraud_activity
                        )
                    
                    comparison_dfs[display_label] = compare_results(
                        dev_results_dict, afr_results
                    )
                
                # Store comparison results
                st.session_state.comparison_dfs = comparison_dfs
                st.session_state.comparison_summary = generate_summary_stats(
                    comparison_dfs, fraud_activity_label
                )
        
        # Display comparison results if available
        if 'comparison_dfs' in st.session_state and st.session_state.comparison_dfs:
            st.markdown('<p class="comparison-note">&lt;Oversight.gov&gt; and &lt;Oversight.gov_State_and_Local&gt; always appear in the Fraud awareness resources results on the AFR Site. This cannot be replicated in the Streamlit site results, and warrants further investigation.</p>', unsafe_allow_html=True)
            
            st.markdown('<p class="section-header">Search Results Comparison: Summary</p>', unsafe_allow_html=True)
            
            st.dataframe(st.session_state.comparison_summary, use_container_width=True, hide_index=True)
            
            # Detailed tabs by facet
            st.markdown('<p class="section-header">Search Results Comparison: Details by Facet</p>', unsafe_allow_html=True)
            comparison_tabs = st.tabs(list(st.session_state.comparison_dfs.keys()))
            
            for tab, (facet_name, df) in zip(comparison_tabs, st.session_state.comparison_dfs.items()):
                with tab:
                    # Only show Description/Linked Properties for Fraud Scheme Examples
                    is_fraud_scheme = (facet_name == "Fraud Scheme Examples")
                    display_comparison_table(df, is_fraud_scheme=is_fraud_scheme)
            
            # Excel export
            st.markdown("#### Export")
            if 'excel_export' not in st.session_state:
                st.session_state.excel_export = create_excel_export(
                    st.session_state.comparison_dfs,
                    st.session_state.comparison_summary,
                    st.session_state.current_fraud_activity_label
                )

            st.download_button(
                label="Download Comparison (Excel)",
                data=st.session_state.excel_export,
                file_name=f"AFR_Comparison_{st.session_state.current_fraud_activity}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

else:
    st.info("No ontology loaded. Please upload an ontology file using the sidebar.")
    
    st.markdown('<p class="section-header">Getting Started</p>', unsafe_allow_html=True)
    st.markdown("""
    **What this interface provides:**
    
    - **Fraud type search**: Find all types of resources related to specific fraud activities
      - Fraud Scheme Examples
      - Fraud Awareness Resources
      - Fraud Prevention & Detection Guidance
      - Fraud Risk Mgmt Principles
      - GAO Reports
    
    **Supported formats**: OWL, RDF, TTL, N3, JSON-LD
    
    **To begin**: Open the sidebar (arrow at top left) and upload an ontology file.
    """)
