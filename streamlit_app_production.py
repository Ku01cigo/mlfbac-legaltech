#!/usr/bin/env python3
"""
DNOTI Legal Tech - Production Streamlit Application
Professional semantic search interface for German legal documents
"""

import streamlit as st
import requests
import pandas as pd
import json
import re
import html
from datetime import datetime
from typing import Dict, List, Optional
import time
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
PAGE_CONFIG = {
    "page_title": "DNOTI Legal Tech - Semantic Search",
    "page_icon": "⚖️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Initialize Streamlit
st.set_page_config(**PAGE_CONFIG)

# Custom CSS for professional appearance
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .search-panel {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin-bottom: 1rem;
    }
    .result-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #28a745;
    }
    .metadata-chip {
        background: #e9ecef;
        color: #495057;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 0.2rem;
        display: inline-block;
    }
    .similarity-score {
        background: #17a2b8;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def check_api_connection() -> bool:
    """Check if the API backend is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def search_documents(query: str, top_k: int = 10, similarity_threshold: float = 0.0) -> List[Dict]:
    """Search documents using the semantic search API or direct ChromaDB access."""
    # First try API
    try:
        payload = {
            "query": query,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold
        }
        
        response = requests.post(
            f"{API_BASE_URL}/search",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("results", [])
    except Exception as e:
        st.warning(f"API nicht verfügbar, verwende direkten ChromaDB-Zugriff: {str(e)}")    # Fallback to direct ChromaDB access
    try:
        import chromadb
        import sys
        import os
        
        # Add src to path for imports
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from src.vectordb.chroma_client import GraniteEmbeddingFunction
        
        client = chromadb.PersistentClient(path="./data/vectordb")
        
        # Use the same IBM Granite model that was used to create the collection
        embedding_fn = GraniteEmbeddingFunction()
        
        collection = client.get_collection("legal_documents", embedding_function=embedding_fn)
        
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
          # Convert to expected format
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 2.0
                # ChromaDB mit Cosine-Distanz: Distance = 1 - Cosine_Similarity
                # Also: Similarity = 1 - Distance, aber nur für gültige Cosine-Distances (0-2)
                if distance <= 2.0:  # Gültige Cosine-Distance
                    similarity = max(0.0, 1.0 - distance)
                else:  # Fallback für andere Distance-Metriken
                    similarity = 1.0 / (1.0 + distance)
                
                if similarity >= similarity_threshold:
                    formatted_results.append({
                        'content': doc,
                        'similarity': similarity,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    })
        
        return formatted_results
        
    except Exception as e:
        st.error(f"Direkter Datenbankzugriff fehlgeschlagen: {str(e)}")
        return []

def extract_gutachten_info(result: Dict) -> Dict[str, str]:
    """Extract structured information from search results."""
    info = {
        "gutachten_number": "N/A",
        "legal_norms": "N/A",
        "jurisdiction": "N/A",
        "date": "N/A"
    }
    
    try:
        metadata = result.get("metadata", {})
        content = result.get("content", "")
        
        # Extract Gutachten number
        if "gutachten_number" in metadata:
            info["gutachten_number"] = metadata["gutachten_number"]
        elif "number" in metadata:
            info["gutachten_number"] = str(metadata["number"])
        else:
            # Try to extract from content
            gutachten_match = re.search(r'(?:Gutachten|Nr\.?)\s*:?\s*(\d+(?:[/-]\d+)*)', content)
            if gutachten_match:
                info["gutachten_number"] = gutachten_match.group(1)
        
        # Extract legal norms
        if "legal_norms" in metadata:
            norms = metadata["legal_norms"]
            if isinstance(norms, list):
                info["legal_norms"] = ", ".join(norms)
            else:
                info["legal_norms"] = str(norms)
        else:
            # Try to extract from content
            norm_patterns = [
                r'§\s*\d+(?:\s+[A-Z][a-z]+)*',
                r'Art\.?\s*\d+(?:\s+[A-Z][a-z]+)*',
                r'[A-Z][a-z]+G\s*§?\s*\d+'
            ]
            found_norms = []
            for pattern in norm_patterns:
                matches = re.findall(pattern, content)
                found_norms.extend(matches)
            
            if found_norms:
                info["legal_norms"] = ", ".join(list(set(found_norms))[:3])
        
        # Extract jurisdiction
        if "jurisdiction" in metadata:
            info["jurisdiction"] = metadata["jurisdiction"]
        elif "court" in metadata:
            info["jurisdiction"] = metadata["court"]
        
        # Extract date
        if "date" in metadata:
            info["date"] = metadata["date"]
        elif "year" in metadata:
            info["date"] = str(metadata["year"])
            
    except Exception as e:
        st.sidebar.error(f"Metadata extraction error: {str(e)}")
    
    return info

def format_result_card(result: Dict, index: int) -> None:
    """Format and display a search result card."""
    similarity = result.get("similarity", 0.0)
    content = result.get("content", "")
    
    # Extract structured information
    info = extract_gutachten_info(result)
    
    with st.container():
        st.markdown(f'<div class="result-card">', unsafe_allow_html=True)
        
        # Header with similarity score
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 📄 Ergebnis {index + 1}")
        with col2:
            st.markdown(f'<span class="similarity-score">{similarity:.1%} Relevanz</span>', 
                       unsafe_allow_html=True)
        
        # Metadata chips
        metadata_html = ""
        if info["gutachten_number"] != "N/A":
            metadata_html += f'<span class="metadata-chip">📋 {info["gutachten_number"]}</span>'
        if info["legal_norms"] != "N/A":
            metadata_html += f'<span class="metadata-chip">⚖️ {info["legal_norms"]}</span>'
        if info["jurisdiction"] != "N/A":
            metadata_html += f'<span class="metadata-chip">🏛️ {info["jurisdiction"]}</span>'
        if info["date"] != "N/A":
            metadata_html += f'<span class="metadata-chip">📅 {info["date"]}</span>'
        
        if metadata_html:
            st.markdown(metadata_html, unsafe_allow_html=True)
        
        # Content preview
        content_preview = content[:500] + "..." if len(content) > 500 else content
        st.markdown(f"**Inhalt:**")
        st.text(content_preview)
        
        # Expandable full content
        with st.expander("Vollständigen Text anzeigen"):
            st.text(content)
        
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    """Main application function."""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>⚖️ DNOTI Legal Tech</h1>
        <p>KI-gestützte semantische Suche für Rechtsgutachten</p>
    </div>
    """, unsafe_allow_html=True)
      # Sidebar
    with st.sidebar:
        st.markdown("### 🔧 Sucheinstellungen")
        
        # Check API connection
        if check_api_connection():
            st.success("✅ API verfügbar")
            api_mode = True
        else:
            st.warning("⚠️ API nicht verfügbar - Direkter Datenbankzugriff")
            st.markdown("**Für beste Performance starten Sie das Backend:**")
            st.code("uvicorn src.api.main:app --reload")
            api_mode = False
        
        # Search parameters
        top_k = st.slider("Anzahl Ergebnisse", 1, 20, 10)
        similarity_threshold = st.slider(
            "Mindest-Ähnlichkeit", 
            0.0, 1.0, 0.3, 0.1,
            help="Ergebnisse unter diesem Schwellenwert werden ausgeblendet"
        )        # Database info
        st.markdown("### 📊 Datenbank-Info")
        try:
            import chromadb
            client = chromadb.PersistentClient(path="./data/vectordb")
            collection = client.get_collection("legal_documents")
            doc_count = collection.count()
            st.metric("Dokumente", doc_count)
        except Exception as e:
            st.error(f"Datenbank nicht verfügbar: {str(e)}")
            st.info("Führen Sie zuerst 'python load_all_gutachten.py' aus")
    
    # Main search interface
    st.markdown('<div class="search-panel">', unsafe_allow_html=True)
    st.markdown("### 🔍 Semantische Suche")
    
    # Search input
    query = st.text_input(
        "Geben Sie Ihre Suchanfrage ein:",
        placeholder="z.B. Pflichtteilsrecht bei Immobilienübertragung",
        help="Nutzen Sie natürliche Sprache für beste Ergebnisse"
    )
    
    # Search examples
    with st.expander("💡 Beispielanfragen"):
        example_queries = [
            "Haftung des Notars bei fehlerhafter Beurkundung",
            "Pflichtteilsrecht bei Immobilienübertragung",
            "Vollmacht bei Grundstücksgeschäften",
            "Eheverträge und Güterstandsregelung",
            "Erbvertrag und gesetzliche Erbfolge"
        ]
        
        for i, example in enumerate(example_queries):
            if st.button(f"📝 {example}", key=f"example_{i}"):
                st.session_state.query = example
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle example query selection
    if 'query' in st.session_state:
        query = st.session_state.query
        del st.session_state.query
    
    # Search execution
    if query:
        with st.spinner("🔍 Suche läuft..."):
            results = search_documents(query, top_k, similarity_threshold)
        
        if results:
            st.markdown(f"### 📊 Suchergebnisse ({len(results)})")
            
            # Display results
            for i, result in enumerate(results):
                format_result_card(result, i)
                
            # Export functionality
            if st.button("📥 Ergebnisse als CSV exportieren"):
                df_data = []
                for result in results:
                    info = extract_gutachten_info(result)
                    df_data.append({
                        "Gutachten_Nr": info["gutachten_number"],
                        "Rechtsnormen": info["legal_norms"],
                        "Zustaendigkeit": info["jurisdiction"],
                        "Datum": info["date"],
                        "Aehnlichkeit": f"{result.get('similarity', 0):.1%}",
                        "Inhalt": result.get("content", "")[:200] + "..."
                    })
                
                df = pd.DataFrame(df_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="CSV herunterladen",
                    data=csv,
                    file_name=f"suchergebnisse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.warning("❌ Keine Ergebnisse gefunden")
            st.markdown("""
            **Tipps für bessere Suchergebnisse:**
            - Verwenden Sie juristische Fachbegriffe
            - Probieren Sie verschiedene Formulierungen
            - Reduzieren Sie den Ähnlichkeits-Schwellenwert
            - Nutzen Sie die Beispielanfragen als Orientierung
            """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6c757d; font-size: 0.9rem;'>
        <p>🏛️ DNOTI Legal Tech | 🤖 KI-gestützte Rechtsdatenbank | 🔒 Datenschutzkonform</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
