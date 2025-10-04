"""
RDF Ontology Mapping & Gap Analysis Tool
Compares labels between fraud ontology (rdfs:label/skos:prefLabel) 
and GAO Product Taxonomy (skos:prefLabel) with fuzzy matching
"""

import rdflib
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from rdflib.namespace import SKOS
import pandas as pd
from difflib import SequenceMatcher
from collections import defaultdict
import re

# Configuration
SIMILARITY_THRESHOLD = 0.75  # Adjust between 0.0-1.0 (higher = stricter)
TOP_N_MATCHES = 5  # Number of candidate matches to report per concept

def normalize_label(label):
    """Normalize labels for better matching"""
    if not label:
        return ""
    # Convert to lowercase, remove extra whitespace, strip punctuation
    normalized = str(label).lower().strip()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def calculate_similarity(str1, str2):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, normalize_label(str1), normalize_label(str2)).ratio()

def extract_fraud_concepts(graph, fraud_ns):
    """Extract concepts from fraud ontology with labels and hierarchy"""
    concepts = {}
    
    # Query for all classes with labels
    for subj in graph.subjects(RDF.type, OWL.Class):
        if str(subj).startswith(str(fraud_ns)):
            labels = set()
            parent_classes = []
            
            # Get rdfs:label
            for label in graph.objects(subj, RDFS.label):
                labels.add(str(label))
            
            # Get skos:prefLabel
            for label in graph.objects(subj, SKOS.prefLabel):
                labels.add(str(label))
            
            # Get parent classes
            for parent in graph.objects(subj, RDFS.subClassOf):
                if isinstance(parent, rdflib.term.URIRef):
                    parent_classes.append(str(parent))
            
            if labels:
                concepts[str(subj)] = {
                    'labels': list(labels),
                    'parents': parent_classes,
                    'primary_label': list(labels)[0]  # Use first as primary
                }
    
    return concepts

def extract_gao_concepts(graph):
    """Extract concepts from GAO taxonomy with skos:prefLabel"""
    concepts = {}
    
    # Query for all SKOS concepts
    for subj in graph.subjects(RDF.type, SKOS.Concept):
        labels = []
        
        # Get skos:prefLabel
        for label in graph.objects(subj, SKOS.prefLabel):
            labels.append(str(label))
        
        # Get related concepts
        related = [str(r) for r in graph.objects(subj, SKOS.related)]
        broader = [str(b) for b in graph.objects(subj, SKOS.broader)]
        narrower = [str(n) for n in graph.objects(subj, SKOS.narrower)]
        
        if labels:
            concepts[str(subj)] = {
                'labels': labels,
                'primary_label': labels[0],
                'related': related,
                'broader': broader,
                'narrower': narrower
            }
    
    return concepts

def find_matches(fraud_concepts, gao_concepts, threshold=SIMILARITY_THRESHOLD, top_n=TOP_N_MATCHES):
    """Find fuzzy matches between fraud and GAO concepts"""
    mappings = []
    
    for fraud_uri, fraud_data in fraud_concepts.items():
        matches = []
        
        # Compare each fraud label against all GAO labels
        for fraud_label in fraud_data['labels']:
            for gao_uri, gao_data in gao_concepts.items():
                for gao_label in gao_data['labels']:
                    similarity = calculate_similarity(fraud_label, gao_label)
                    
                    if similarity >= threshold:
                        matches.append({
                            'gao_uri': gao_uri,
                            'gao_label': gao_label,
                            'similarity': similarity,
                            'fraud_label_used': fraud_label
                        })
        
        # Sort by similarity and keep top N
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        top_matches = matches[:top_n]
        
        if top_matches:
            for match in top_matches:
                mappings.append({
                    'fraud_uri': fraud_uri,
                    'fraud_label': fraud_data['primary_label'],
                    'fraud_label_matched': match['fraud_label_used'],
                    'gao_uri': match['gao_uri'],
                    'gao_label': match['gao_label'],
                    'similarity_score': round(match['similarity'], 3),
                    'fraud_parents': '; '.join(fraud_data['parents'][:3])  # Limit for readability
                })
    
    return mappings

def identify_gaps(fraud_concepts, gao_concepts, mappings_df):
    """Identify concepts without mappings in both directions"""
    
    # Fraud concepts without GAO matches
    mapped_fraud = set(mappings_df['fraud_uri'].unique()) if not mappings_df.empty else set()
    unmapped_fraud = []
    
    for uri, data in fraud_concepts.items():
        if uri not in mapped_fraud:
            unmapped_fraud.append({
                'uri': uri,
                'label': data['primary_label'],
                'all_labels': '; '.join(data['labels']),
                'parents': '; '.join(data['parents'][:3])
            })
    
    # GAO concepts without fraud matches
    mapped_gao = set(mappings_df['gao_uri'].unique()) if not mappings_df.empty else set()
    unmapped_gao = []
    
    for uri, data in gao_concepts.items():
        if uri not in mapped_gao:
            unmapped_gao.append({
                'uri': uri,
                'label': data['primary_label'],
                'all_labels': '; '.join(data['labels'])
            })
    
    return unmapped_fraud, unmapped_gao

def main(fraud_file, gao_file, output_prefix='ontology_mapping'):
    """Main execution function"""
    
    print("Loading fraud ontology...")
    fraud_graph = Graph()
    fraud_graph.parse(fraud_file, format='turtle')
    
    print("Loading GAO taxonomy...")
    gao_graph = Graph()
    gao_graph.parse(gao_file, format='turtle')
    
    # Detect fraud namespace (assuming consistent pattern)
    fraud_ns = None
    for ns_prefix, ns_uri in fraud_graph.namespaces():
        if 'gfo' in ns_prefix or 'fraud' in str(ns_uri).lower():
            fraud_ns = Namespace(ns_uri)
            break
    
    if not fraud_ns:
        # Fallback: find most common namespace for owl:Class subjects
        ns_counts = defaultdict(int)
        for subj in fraud_graph.subjects(RDF.type, OWL.Class):
            ns = str(subj).rsplit('/', 1)[0] + '/'
            ns_counts[ns] += 1
        fraud_ns = Namespace(max(ns_counts, key=ns_counts.get))
    
    print(f"Fraud namespace detected: {fraud_ns}")
    
    print("\nExtracting fraud concepts...")
    fraud_concepts = extract_fraud_concepts(fraud_graph, fraud_ns)
    print(f"Found {len(fraud_concepts)} fraud concepts")
    
    print("Extracting GAO concepts...")
    gao_concepts = extract_gao_concepts(gao_graph)
    print(f"Found {len(gao_concepts)} GAO concepts")
    
    print(f"\nFinding matches (threshold={SIMILARITY_THRESHOLD})...")
    mappings = find_matches(fraud_concepts, gao_concepts, SIMILARITY_THRESHOLD, TOP_N_MATCHES)
    mappings_df = pd.DataFrame(mappings)
    
    print(f"Found {len(mappings)} mappings")
    
    print("\nIdentifying coverage gaps...")
    unmapped_fraud, unmapped_gao = identify_gaps(fraud_concepts, gao_concepts, mappings_df)
    
    # Save results
    print("\nSaving results...")
    
    if not mappings_df.empty:
        mappings_df.to_csv(f'{output_prefix}_mappings.csv', index=False)
        print(f"✓ Mappings saved to {output_prefix}_mappings.csv")
    else:
        print("⚠ No mappings found above threshold")
    
    if unmapped_fraud:
        pd.DataFrame(unmapped_fraud).to_csv(f'{output_prefix}_gaps_fraud.csv', index=False)
        print(f"✓ Fraud gaps saved to {output_prefix}_gaps_fraud.csv ({len(unmapped_fraud)} concepts)")
    
    if unmapped_gao:
        pd.DataFrame(unmapped_gao).to_csv(f'{output_prefix}_gaps_gao.csv', index=False)
        print(f"✓ GAO gaps saved to {output_prefix}_gaps_gao.csv ({len(unmapped_gao)} concepts)")
    
    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Fraud concepts: {len(fraud_concepts)}")
    print(f"GAO concepts: {len(gao_concepts)}")
    print(f"Mappings found: {len(mappings)}")
    print(f"Fraud concepts mapped: {len(set(mappings_df['fraud_uri'])) if not mappings_df.empty else 0}")
    print(f"GAO concepts mapped: {len(set(mappings_df['gao_uri'])) if not mappings_df.empty else 0}")
    print(f"Unmapped fraud concepts: {len(unmapped_fraud)}")
    print(f"Unmapped GAO concepts: {len(unmapped_gao)}")
    
    if not mappings_df.empty:
        print(f"\nAverage similarity score: {mappings_df['similarity_score'].mean():.3f}")
        print(f"Median similarity score: {mappings_df['similarity_score'].median():.3f}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python ontology_mapper.py <fraud_ontology.ttl> <gao_taxonomy.ttl> [output_prefix]")
        print("\nConfiguration:")
        print(f"  Similarity threshold: {SIMILARITY_THRESHOLD}")
        print(f"  Top matches per concept: {TOP_N_MATCHES}")
        print("\nTo adjust, edit SIMILARITY_THRESHOLD and TOP_N_MATCHES in the script")
        sys.exit(1)
    
    fraud_file = sys.argv[1]
    gao_file = sys.argv[2]
    output_prefix = sys.argv[3] if len(sys.argv) > 3 else 'ontology_mapping'
    
    main(fraud_file, gao_file, output_prefix)