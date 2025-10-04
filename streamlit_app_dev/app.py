import streamlit as st
import rdflib
from pathlib import Path
import pandas as pd
import os

# Set page config
st.set_page_config(
    page_title="US GAO Antifraud Resource Test Page",
    layout="wide"
)

# Title
st.title("**DEV** US GAO Antifraud Resource Test Page")
st.markdown("Search and explore fraud concepts, instances, and relationships in the GAO's Conceptual Fraud Model")

# Sidebar for ontology management
st.sidebar.header("Ontology Management")

uploaded_file = st.sidebar.file_uploader(
    "Upload Ontology File", 
    type=['owl', 'rdf', 'ttl', 'n3', 'jsonld'],
    help="Upload your ontology file to begin searching"
)

# Initialize session state
if 'ontology' not in st.session_state:
    st.session_state.ontology = None
if 'loaded_file' not in st.session_state:
    st.session_state.loaded_file = None

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

def load_default_ontology():
    script_dir = Path(__file__).parent
    default_ontology_path = script_dir / "gfo_turtle.ttl"
    
    if default_ontology_path.exists():
        try:
            with st.spinner("Loading GFO ontology..."):
                st.session_state.ontology = load_ontology_rdflib(str(default_ontology_path))
                st.session_state.loaded_file = "gfo_turtle.ttl (default)"
                st.session_state.uploaded_file_path = str(default_ontology_path)
                
                if st.session_state.ontology:
                    triple_count = len(st.session_state.ontology)
                    st.sidebar.success(f"[OK] Auto-loaded: gfo_turtle.ttl")
                    st.sidebar.info(f"Triples: {triple_count}")
                    return True
        except Exception as e:
            st.sidebar.error(f"Failed to load: {str(e)}")
    else:
        st.sidebar.warning(f"Default ontology not found")
    return False

# Auto-load default ontology
if st.session_state.ontology is None:
    load_default_ontology()

# Handle file upload
if uploaded_file is not None and uploaded_file != st.session_state.loaded_file:
    temp_path = f"/tmp/{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.session_state.ontology = load_ontology_rdflib(temp_path)
    st.session_state.loaded_file = uploaded_file
    st.session_state.uploaded_file_path = temp_path
    
    if st.session_state.ontology:
        triple_count = len(st.session_state.ontology)
        st.sidebar.success(f"[OK] Loaded: {uploaded_file.name}")
        st.sidebar.info(f"Triples: {triple_count}")

# Main interface
if st.session_state.ontology:
    
    st.header("Fraud Activity Search")
    st.markdown("Search for all resources related to specific fraud activities.")
    
    fraud_activity_mapping = {
        "Beneficiary fraud": "BeneficiaryFraud",
        "Cellphone fraud": "CellphoneFraud",
        "Charity fraud": "CharityFraud",
        "Confidence fraud": "ConfidenceFraud",
        "Consumer fraud": "ConsumerFraud",
        "Corporate fraud": "CorporateFraud",
        "Corruption": "Corruption",
        "Cyber espionage": "CyberEspionage",
        "Cyberextortion": "Cyberextortion",
        "Environmental fraud": "EnvironmentalFraud",
        "Federal contract fraud": "ContractFraud",
        "Financial institution fraud": "FinancialInstitutionFraud",
        "Government furnished equipment fraud": "GovernmentFurnishedEquipmentFraud",
        "Grant fraud": "GrantFraud",
        "Healthcare fraud": "HealthcareFraud",
        "Housing fraud": "HousingFraud",
        "Identity fraud": "IdentityFraud",
        "Insurance fraud": "InsuranceFraud",
        "Investment fraud": "InvestmentFraud",
        "Laboratory fraud": "LaboratoryFraud",
        "Lien filing fraud": "LienFillingFraud",
        "Loan fraud": "LoanFraud",
        "Mail fraud": "MailFraud",
        "Media manipulation": "MediaManipulation",
        "Payment fraud": "PaymentFraud",
        "Procurement fraud": "ProcurementFraud",
        "Public assistance fraud": "AssistanceFraud",
        "Public emergency fraud": "public_emergency_fraud",
        "Sanction evasion fraud": "SanctionEvasion",
        "Student financial aid fraud": "StudentFinancialAidFraud",
        "Supervised release": "supervised_release",
        "Tax fraud": "TaxFraud",
        "Trafficking": "Trafficking",
        "Visa fraud": "VisaFraud",
        "Wire fraud": "WireFraud",
        "Workplace fraud": "WorkplaceFraud"
    }
    
    fraud_activity_label = st.selectbox(
        "Select Fraud Activity Type:",
        options=list(fraud_activity_mapping.keys()),
        help="Choose a fraud activity type to find all related resources"
    )
    
    fraud_activity = fraud_activity_mapping.get(fraud_activity_label)
    
    if st.button("Search All Resources"):
        if fraud_activity_label and fraud_activity:
            
            # Query for Federal Fraud Schemes
            fraud_scheme_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX dcterms: <http://purl.org/dc/terms/>
 
SELECT DISTINCT ?individual ?individualName ?description ?fraudNarrative ?isDefinedBy
WHERE {{
    ?individual a gfo:FederalFraudScheme ;
                rdfs:label ?individualName .
   
    OPTIONAL {{ ?individual dcterms:description ?description . }}
    OPTIONAL {{ ?individual gfo:fraudNarrative ?fraudNarrative . }}
    OPTIONAL {{ ?individual rdfs:isDefinedBy ?isDefinedBy . }}
   
    {{
        ?individual a ?someClass .
        ?someClass owl:onProperty gfo:involves ;
                   owl:someValuesFrom ?specificFraud .
       
        ?specificFraud rdfs:subClassOf* ?fraudType .
        ?fraudType rdfs:label ?fraudTypeName .
       
        ?specificFraud rdfs:subClassOf* gfo:{fraud_activity} .
    }}
    UNION
    {{
        ?individual a ?fraudSchemeClass .
        ?fraudSchemeClass rdfs:subClassOf* gfo:{fraud_activity} .
        ?fraudSchemeClass rdfs:subClassOf* ?fraudType .
        ?fraudType rdfs:label ?fraudTypeName .
       
        FILTER(?fraudSchemeClass != gfo:FederalFraudScheme)
    }}
    
    FILTER(?fraudType != gfo:FraudActivity)
}}
ORDER BY ?individualName
"""

            # Query for Fraud Awareness Resources (FraudEducation)
            awareness_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?individual ?individualName ?definition ?website ?isDefinedBy
WHERE {{
    ?individual a gfo:FraudEducation ;
                rdfs:label ?individualName .
    
    OPTIONAL {{ ?individual skos:definition ?definition . }}
    OPTIONAL {{ ?individual gfo:hasWebsite ?website . }}
    OPTIONAL {{ ?individual rdfs:isDefinedBy ?isDefinedBy . }}
    
    {{
        ?individual a ?someClass .
        ?someClass owl:onProperty gfo:addresses ;
                   owl:someValuesFrom ?specificFraud .
        
        ?specificFraud rdfs:subClassOf* gfo:{fraud_activity} .
    }}
    UNION
    {{
        ?individual a ?resourceClass .
        ?resourceClass rdfs:subClassOf* gfo:{fraud_activity} .
        
        FILTER(?resourceClass != gfo:FraudEducation)
    }}
}}
ORDER BY ?individualName
"""

            # Query for Fraud Prevention & Detection Guidance
            prevention_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?individual ?individualName ?definition ?website ?isDefinedBy
WHERE {{
    ?individual a gfo:FraudPreventionAndDetectionGuidance ;
                rdfs:label ?individualName .
    
    OPTIONAL {{ ?individual skos:definition ?definition . }}
    OPTIONAL {{ ?individual gfo:hasWebsite ?website . }}
    OPTIONAL {{ ?individual rdfs:isDefinedBy ?isDefinedBy . }}
    
    {{
        ?individual a ?someClass .
        ?someClass owl:onProperty gfo:addresses ;
                   owl:someValuesFrom ?specificFraud .
        
        ?specificFraud rdfs:subClassOf* gfo:{fraud_activity} .
    }}
    UNION
    {{
        ?individual a ?resourceClass .
        ?resourceClass rdfs:subClassOf* gfo:{fraud_activity} .
        
        FILTER(?resourceClass != gfo:FraudPreventionAndDetectionGuidance)
    }}
}}
ORDER BY ?individualName
"""

            # Query for Fraud Risk Management Principles
            risk_mgmt_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?individual ?individualName ?definition ?website ?isDefinedBy
WHERE {{
    ?individual a gfo:FraudRiskManagementPrinciples ;
                rdfs:label ?individualName .
    
    OPTIONAL {{ ?individual skos:definition ?definition . }}
    OPTIONAL {{ ?individual gfo:hasWebsite ?website . }}
    OPTIONAL {{ ?individual rdfs:isDefinedBy ?isDefinedBy . }}
    
    {{
        ?individual a ?someClass .
        ?someClass owl:onProperty gfo:addresses ;
                   owl:someValuesFrom ?specificFraud .
        
        ?specificFraud rdfs:subClassOf* gfo:{fraud_activity} .
    }}
    UNION
    {{
        ?individual a ?resourceClass .
        ?resourceClass rdfs:subClassOf* gfo:{fraud_activity} .
        
        FILTER(?resourceClass != gfo:FraudRiskManagementPrinciples)
    }}
}}
ORDER BY ?individualName
"""

            # Query for GAO Reports
            gao_report_query = f"""
PREFIX gfo: <https://gaoinnovations.gov/antifraud_resource/howfraudworks/gfo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?individual ?individualName ?definition ?website ?isDefinedBy
WHERE {{
    ?individual a gfo:GAOReport ;
                rdfs:label ?individualName .
    
    OPTIONAL {{ ?individual skos:definition ?definition . }}
    OPTIONAL {{ ?individual gfo:hasWebsite ?website . }}
    OPTIONAL {{ ?individual rdfs:isDefinedBy ?isDefinedBy . }}
    
    {{
        ?individual a ?someClass .
        ?someClass owl:onProperty gfo:addresses ;
                   owl:someValuesFrom ?specificFraud .
        
        ?specificFraud rdfs:subClassOf* gfo:{fraud_activity} .
    }}
    UNION
    {{
        ?individual a ?resourceClass .
        ?resourceClass rdfs:subClassOf* gfo:{fraud_activity} .
        
        FILTER(?resourceClass != gfo:GAOReport)
    }}
}}
ORDER BY ?individualName
"""
            
            try:
                g = rdflib.Graph()
                if 'uploaded_file_path' in st.session_state:
                    g.parse(st.session_state.uploaded_file_path)
                    
                    # Execute all queries
                    fraud_schemes = list(g.query(fraud_scheme_query))
                    awareness_resources = list(g.query(awareness_query))
                    prevention_resources = list(g.query(prevention_query))
                    risk_mgmt_resources = list(g.query(risk_mgmt_query))
                    gao_reports = list(g.query(gao_report_query))
                    
                    # Calculate total results
                    total_results = (len(fraud_schemes) + len(awareness_resources) + 
                                   len(prevention_resources) + len(risk_mgmt_resources) + 
                                   len(gao_reports))
                    
                    if total_results > 0:
                        st.success(f"[OK] Found {total_results} total resources related to {fraud_activity_label}")
                        
                        # Display GAO Reports section first (full width)
                        if gao_reports:
                            st.markdown("---")
                            st.subheader(f"GAO Reports ({len(gao_reports)})")
                            
                            for i, row in enumerate(gao_reports):
                                resource_name = str(row.individualName)
                                definition = str(row.definition) if row.definition else "No definition available"
                                website = str(row.website) if row.website else ""
                                is_defined_by_url = str(row.isDefinedBy) if row.isDefinedBy else "No definition source available"
                                
                                with st.expander(f"{i+1}. {resource_name}"):
                                    st.write(f"**Definition:** {definition}")
                                    if website:
                                        st.write(f"**Website:** {website}")
                                    st.write(f"**Related to:** {fraud_activity_label}")
                                    st.markdown("---")
                                    st.caption(f"Source: {is_defined_by_url}")
                        
                        st.markdown("---")
                        
                        # Create 2x2 grid layout for other resources
                        col1, col2 = st.columns(2)
                        
                        # Top left: Fraud Scheme Examples
                        with col1:
                            if fraud_schemes:
                                st.subheader(f"Fraud Scheme Examples ({len(fraud_schemes)})")
                                
                                for i, row in enumerate(fraud_schemes):
                                    scheme_name = str(row.individualName)
                                    fraud_description = str(row.description) if row.description else "No description available"
                                    fraud_narrative_uri = str(row.fraudNarrative) if row.fraudNarrative else "No fraud narrative available"
                                    is_defined_by_url = str(row.isDefinedBy) if row.isDefinedBy else "No definition source available"
                                    
                                    with st.expander(f"{i+1}. {scheme_name}"):
                                        st.write(f"**Fraud Description:** {fraud_description}")
                                        st.write("**Fraud Narrative:**")
                                        st.text(fraud_narrative_uri)
                                        st.write(f"**Related to:** {fraud_activity_label}")
                                        st.markdown("---")
                                        st.caption(f"Source: {is_defined_by_url}")
                            else:
                                st.subheader("Fraud Scheme Examples (0)")
                                st.info("No fraud scheme examples found")
                        
                        # Top right: Fraud Prevention & Detection Guidance
                        with col2:
                            if prevention_resources:
                                st.subheader(f"Fraud Prevention & Detection Guidance ({len(prevention_resources)})")
                                
                                for i, row in enumerate(prevention_resources):
                                    resource_name = str(row.individualName)
                                    definition = str(row.definition) if row.definition else "No definition available"
                                    website = str(row.website) if row.website else ""
                                    is_defined_by_url = str(row.isDefinedBy) if row.isDefinedBy else "No definition source available"
                                    
                                    with st.expander(f"{i+1}. {resource_name}"):
                                        st.write(f"**Definition:** {definition}")
                                        if website:
                                            st.write(f"**Website:** {website}")
                                        st.write(f"**Related to:** {fraud_activity_label}")
                                        st.markdown("---")
                                        st.caption(f"Source: {is_defined_by_url}")
                            else:
                                st.subheader("Fraud Prevention & Detection Guidance (0)")
                                st.info("No prevention & detection guidance found")
                        
                        # Bottom row
                        col3, col4 = st.columns(2)
                        
                        # Bottom left: Fraud Awareness Resources
                        with col3:
                            if awareness_resources:
                                st.subheader(f"Fraud Awareness Resources ({len(awareness_resources)})")
                                
                                for i, row in enumerate(awareness_resources):
                                    resource_name = str(row.individualName)
                                    definition = str(row.definition) if row.definition else "No definition available"
                                    website = str(row.website) if row.website else ""
                                    is_defined_by_url = str(row.isDefinedBy) if row.isDefinedBy else "No definition source available"
                                    
                                    with st.expander(f"{i+1}. {resource_name}"):
                                        st.write(f"**Definition:** {definition}")
                                        if website:
                                            st.write(f"**Website:** {website}")
                                        st.write(f"**Related to:** {fraud_activity_label}")
                                        st.markdown("---")
                                        st.caption(f"Source: {is_defined_by_url}")
                            else:
                                st.subheader("Fraud Awareness Resources (0)")
                                st.info("No fraud awareness resources found")
                        
                        # Bottom right: Fraud Risk Management Principles
                        with col4:
                            if risk_mgmt_resources:
                                st.subheader(f"Fraud Risk Management Principles ({len(risk_mgmt_resources)})")
                                
                                for i, row in enumerate(risk_mgmt_resources):
                                    resource_name = str(row.individualName)
                                    definition = str(row.definition) if row.definition else "No definition available"
                                    website = str(row.website) if row.website else ""
                                    is_defined_by_url = str(row.isDefinedBy) if row.isDefinedBy else "No definition source available"
                                    
                                    with st.expander(f"{i+1}. {resource_name}"):
                                        st.write(f"**Definition:** {definition}")
                                        if website:
                                            st.write(f"**Website:** {website}")
                                        st.write(f"**Related to:** {fraud_activity_label}")
                                        st.markdown("---")
                                        st.caption(f"Source: {is_defined_by_url}")
                            else:
                                st.subheader("Fraud Risk Management Principles (0)")
                                st.info("No fraud risk management principles found")
                    else:
                        st.info(f"No resources found for {fraud_activity_label}")
                        
            except Exception as e:
                st.error(f"[ERROR] SPARQL query failed: {str(e)}")
                st.info("Make sure your ontology file is properly loaded.")
        else:
            st.warning("Please select a fraud activity type.")

else:
    st.info("Please upload an ontology file to begin")
    
    st.markdown("---")
    st.header("Getting Started")
    st.markdown("""
    **What this interface provides:**
    
    1. **Fraud Activity Search**: Find all types of resources related to specific fraud activities
       - Fraud Scheme Examples
       - Fraud Awareness Resources
       - Fraud Prevention & Detection Guidance
       - Fraud Risk Management Principles
       - GAO Reports
    
    **Supported formats**: OWL, RDF, TTL, N3, JSON-LD
    
    **Next steps**:
    - Upload your ontology file using the sidebar
    - Select a fraud activity type
    - Click "Search All Resources" to find all related content
    
    **How it works**:
    - Finds both direct and indirect relationships through class hierarchies and property chains
    - Captures complex OWL restrictions and property relationships
    - Uses the `involves` property for fraud schemes and `addresses` property for other resources
    """)