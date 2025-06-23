#!/usr/bin/env python3
"""
Streamlit Frontend für Legal Tech Semantic Search
Benutzerfreundliche Oberfläche für Rechtsgutachten-Suche und -Analyse
"""

import streamlit as st

# Konfiguration importieren
try:
    from src.config import config
    # Use localhost for client connections even if server binds to 0.0.0.0
    host = "localhost" if config.API_HOST == "0.0.0.0" else config.API_HOST
    API_BASE_URL = f"http://{host}:{config.API_PORT}"
except ImportError:
    # Fallback wenn Konfiguration nicht verfügbar
    API_BASE_URL = "http://localhost:8000"

# Fallback imports für bessere Fehlerbehandlung
try:
    import requests
except ImportError:
    st.error("requests library not installed. Please run: pip install requests")
    st.stop()

try:
    import pandas as pd
except ImportError:
    st.warning("pandas not available - some features may be limited")
    pd = None

from datetime import datetime
from typing import Dict, List, Optional
import time
import html
import json
import re

def get_complete_gutachten(gutachten_id: str) -> str:
    """Holt das komplette Gutachten anhand der ID aus der Original-Datenbank."""
    try:
        # Versuche das Original-Gutachten aus der JSON-Datei zu laden
        import os
        json_path = os.path.join(os.path.dirname(__file__), "Database", "Original", "dnoti_all.json")
        
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Suche das Gutachten mit der entsprechenden ID
                for gutachten in data:
                    if str(gutachten.get('gutachten_nummer', '')) == str(gutachten_id):
                        return gutachten.get('text', '')
                    # Fallback: auch andere ID-Felder prüfen
                    if (str(gutachten.get('id', '')) == str(gutachten_id) or 
                        str(gutachten.get('document_id', '')) == str(gutachten_id)):
                        return gutachten.get('text', '')
        
        return ""
    except Exception as e:
        print(f"Error loading complete gutachten: {e}")
        return ""

def fix_encoding_issues(text: str) -> str:
    """Korrigiert häufige Encoding-Probleme in API-Antworten."""
    if not text:
        return text
    
    # Häufige UTF-8 zu Latin-1 Encoding-Probleme korrigieren
    replacements = {
        'Ã¤': 'ä', 'Ã¶': 'ö', 'Ã¼': 'ü', 'ÃŸ': 'ß',
        'Ã„': 'Ä', 'Ã–': 'Ö', 'Ã‹': 'Ü',
        'Â§': '§', 'Â°': '°', 'Â´': '´', 'Â±': '±',
        'Ã©': 'é', 'Ã¨': 'è', 'Ã¡': 'á', 'Ã ': 'à',
        'Ã­': 'í', 'Ã¬': 'ì', 'Ã³': 'ó', 'Ã²': 'ò',
        'Ãº': 'ú', 'Ã¹': 'ù', 'Ã¥': 'å', 'Ã†': 'Æ',
        'Ã¸': 'ø', 'Ã¦': 'æ', 'Ã±': 'ñ', 'Ã§': 'ç',
        'â€œ': '"', 'â€': '"', 'â€™': "'", 'â€˜': "'",
        'â€"': '–', 'â€"': '—', 'â€¦': '…',
        'Â ': ' ', 'Â': ''  # Remove spurious characters
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    # Entferne doppelte Spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

# Konfiguration
PAGE_CONFIG = {
    "page_title": "Legal Tech Semantic Search",
    "page_icon": "⚖️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

def init_streamlit():
    """Initialisiert Streamlit-Konfiguration."""
    st.set_page_config(**PAGE_CONFIG)
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f9ff 0%, #dbeafe 100%);
        border-radius: 10px;
    }
    .search-box {
        padding: 1rem;
        border-radius: 10px;
        background-color: #f8fafc;
        margin: 1rem 0;
    }
    .result-card {
        padding: 1rem;
        border-left: 4px solid #3b82f6;
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        margin: 0.5rem 0;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .result-card h4 {
        color: #1e293b !important;
        margin-bottom: 0.5rem;
    }
    .result-card p {
        color: #374151 !important;
        margin: 0.25rem 0;
    }
    .result-card strong {
        color: #1f2937 !important;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
    }
      /* Stelle sicher, dass alle Texte gut lesbar sind */
    .stMarkdown, .stText {
        color: #000000 !important;
        background-color: #ffffff !important;
    }
    
    /* Fix für Streamlit Container */
    div[data-testid="stContainer"] {
        background-color: #ffffff !important;
    }
    
    /* Maximale Lesbarkeit für alle Textelemente */
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
    }
    
    p {
        color: #000000 !important;
    }
    
    /* Expander mit perfekter Lesbarkeit */
    .streamlit-expander {
        background-color: #ffffff !important;
        border: 1px solid #cccccc !important;
    }
    
    .streamlit-expander > div > div {
        color: #000000 !important;
        background-color: #ffffff !important;
    }
    
    /* Alle Texte in Expandern schwarz auf weiß */
    .streamlit-expander * {
        color: #000000 !important;
        background-color: transparent !important;
    }
    
    /* JSON Display mit perfekter Lesbarkeit */
    .stJson {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Expander-Inhalte optimal lesbar */
    div[data-testid="stExpander"] * {
        color: #000000 !important;
        background-color: transparent !important;
    }
    
    /* Code-Blöcke lesbar machen */
    pre {
        background-color: #f8f9fa !important;
        color: #000000 !important;
        border: 1px solid #dee2e6 !important;
        padding: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

def check_api_connection() -> bool:
    """Prüft Verbindung zur API."""
    try:
        response = requests.get(f"{API_BASE_URL}/admin/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def search_documents(query: str, search_type: str = "semantic", limit: int = 10, 
                    similarity_threshold: float = 0.1, filters: str = None) -> Dict:
    """Führt Dokumentensuche über API durch."""
    try:
        data = {
            "query": query,
            "search_type": search_type,
            "limit": limit,
            "similarity_threshold": similarity_threshold
        }
        
        # Filter hinzufügen falls vorhanden
        if filters:
            try:
                filter_dict = json.loads(filters)
                data.update(filter_dict)
            except json.JSONDecodeError:
                pass  # Ignoriere ungültige JSON-Filter
        
        response = requests.post(f"{API_BASE_URL}/search/semantic", json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            
            # Erweitere jeden Treffer um vollständigen Gutachten-Text
            for item in result.get("results", []):
                gutachten_id = item.get("metadata", {}).get("source_gutachten_id")
                current_length = len(item.get("content", ""))
                if gutachten_id:
                    try:
                        # Versuche das komplette Gutachten aus der Original-JSON zu holen
                        full_content = get_complete_gutachten(gutachten_id)
                        if full_content and len(full_content) > current_length:
                            item["content"] = full_content
                            item["is_complete"] = True
                            item["debug_info"] = f"Erweitert von {current_length} auf {len(full_content)} Zeichen"
                        else:
                            item["is_complete"] = False
                            item["debug_info"] = f"Kein vollständiges Gutachten gefunden oder bereits vollständig. Original: {current_length} Zeichen"
                    except Exception as e:
                        item["is_complete"] = False
                        item["debug_info"] = f"Fehler beim Laden: {str(e)}"
                        pass  # Falls es fehlschlägt, behalte den ursprünglichen Content
            
            return result
        else:
            return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Connection Error: {str(e)}"}

def format_gutachten_text(text: str) -> str:
    """Formatiert Gutachtentext für bessere Lesbarkeit mit erhaltener Struktur."""
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Leere Zeilen werden zu Absätzen
        if not line_stripped:
            formatted_lines.append('<br>')
            continue
        
        # Erkenne verschiedene Arten von Überschriften
        if any(line_stripped.startswith(prefix) for prefix in [
            'Gutachten Nr.', 'Rechtsbezug:', 'Normen:', 'Sachverhalt:', 
            'Rechtliche Bewertung:', 'Fazit:', 'I.', 'II.', 'III.', 'IV.',
            'A.', 'B.', 'C.', 'D.', '1.', '2.', '3.', '4.', '5.'
        ]):
            formatted_lines.append(f'<h5 style="color: #1e40af !important; margin: 1.5rem 0 0.5rem 0; font-weight: 600; font-size: 16px !important;">{html.escape(line_stripped)}</h5>')
        
        # Erkenne Listen und Aufzählungen
        elif line_stripped.startswith(('a)', 'b)', 'c)', 'd)', 'e)', '- ', '• ', '*')):
            formatted_lines.append(f'<p style="color: #374151 !important; margin: 0.3rem 0 0.3rem 1.5rem; line-height: 1.6; font-size: 14px;">{html.escape(line_stripped)}</p>')
        
        # Erkenne eingerückte Texte (oft wichtige Punkte)
        elif line.startswith('    ') or line.startswith('\t'):
            formatted_lines.append(f'<p style="color: #374151 !important; margin: 0.3rem 0 0.3rem 2rem; line-height: 1.6; font-size: 14px; font-style: italic;">{html.escape(line_stripped)}</p>')
        
        # Normaler Absatz
        else:
            formatted_lines.append(f'<p style="color: #374151 !important; margin: 0.8rem 0; line-height: 1.6; font-size: 14px;">{html.escape(line_stripped)}</p>')
    
    return '\n'.join(formatted_lines)

def extract_meaningful_title_new(content: str) -> str:
    """Extrahiert einen aussagekräftigen Titel aus dem Gutachten-Content."""
    if not content:
        return "Kein Titel verfügbar"
    
    import re
    
    # Bereinige und entferne Encoding-Probleme vom Content für bessere Analyse
    clean_content = fix_encoding_issues(content)
    
    # Da der Content oft in einer langen Zeile steht, arbeiten wir direkt mit dem String
    # Überspringe DNotI-Header durch Pattern-Matching
    
    # 1. Direktere Suche nach thematischen Titeln im gesamten Content
    # Erweiterte Pattern für verschiedene Rechtsbereiche
    theme_patterns = [
        r'(Befristung[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Vertragsschluss[^I]*?)(?:\s+I\.|\s+Rechtsfragen)', 
        r'(Schadensersatz[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Haftung[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Widerruf[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Eigentum[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Vollmacht[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Kündigung[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Dauerwohnrecht[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Dauernutzungsrecht[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Heimfall[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Unternehmereigenschaft[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Anwendbarkeit[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(AGB-Recht[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(öffentliche Hand[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Gegenstand einer GmbH[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(ärztliches Standesrecht[^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'(Träger-GmbH[^I]*?)(?:\s+I\.|\s+Rechtsfragen)'
    ]    
    for pattern in theme_patterns:
        match = re.search(pattern, clean_content)
        if match:
            title_candidate = match.group(1).strip()
            title_candidate = re.sub(r'^\s*,\s*|\s*;\s*$', '', title_candidate)
            if len(title_candidate) > 10:
                return html.escape(title_candidate)
    
    # 2. Fallback: Nach allen Norm-Referenzen suchen (für verschiedene Rechtsgebiete)
    # Pattern: "41 Abs. 1 Titel I." oder "GmbHG §§ 3, 10 Titel I."
    norm_end_patterns = [
        r'\d+\s+Abs\.\s*\d+\s+([A-ZÄÖÜ][^I]*?)(?:\s+I\.|\s+Rechtsfragen)',
        r'[A-Z]{2,6}\s*§§?\s*[0-9][^A-ZÄÖÜ]*?([A-ZÄÖÜ][^I]*?)(?:\s+I\.|\s+Rechtsfragen)'
    ]
    
    for pattern in norm_end_patterns:
        match = re.search(pattern, clean_content)
        if match:
            title_candidate = match.group(1).strip()
            # Entferne führende Norm-Reste
            title_candidate = re.sub(r'^[^A-ZÄÖÜ]*', '', title_candidate)
            title_candidate = re.sub(r'^\s*,\s*|\s*;\s*$', '', title_candidate)
            if len(title_candidate) > 10:
                return html.escape(title_candidate[:120] + '...' if len(title_candidate) > 120 else title_candidate)
    
    # 3. Allgemeiner Fallback: Suche nach jeder substanziellen Überschrift mit großbuchstaben
    # Aber überspringe DNotI-Header
    general_pattern = r'([A-ZÄÖÜ][a-zäöüß\s,;:-]{15,}?)(?:\s+I\.|\s+Rechtsfragen|\s+II\.)'
    matches = re.findall(general_pattern, clean_content)
    
    for match in matches:
        title_candidate = match.strip()
        # Entferne DNotI-Header-Teile
        if not any(skip in title_candidate for skip in [
            'DNotI', 'Deutsches Notarinstitut', 'Dokumentnummer', 'Gutachten des', 
            'letzte Aktualisierung', 'Fax - Abfrage'
        ]):
            title_candidate = re.sub(r'^\s*,\s*|\s*;\s*$', '', title_candidate)
            if len(title_candidate) > 15:
                return html.escape(title_candidate[:100] + '...' if len(title_candidate) > 100 else title_candidate)
    
    # 4. Letzter Fallback
    return "Gutachten (Titel nicht verfügbar)"


def search_documents(query: str, search_type: str = "semantic", limit: int = 10, 
                    similarity_threshold: float = 0.1, filters: str = None) -> Dict:
    """Führt Dokumentensuche über API durch."""
    try:
        data = {
            "query": query,
            "search_type": search_type,
            "limit": limit,
            "similarity_threshold": similarity_threshold
        }
        
        # Filter hinzufügen falls vorhanden
        if filters:
            try:
                filter_dict = json.loads(filters)
                data.update(filter_dict)
            except json.JSONDecodeError:
                pass  # Ignoriere ungültige JSON-Filter
        
        response = requests.post(f"{API_BASE_URL}/search/semantic", json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            
            # Erweitere jeden Treffer um vollständigen Gutachten-Text
            for item in result.get("results", []):
                gutachten_id = item.get("metadata", {}).get("source_gutachten_id")
                current_length = len(item.get("content", ""))
                if gutachten_id:
                    try:
                        # Versuche das komplette Gutachten aus der Original-JSON zu holen
                        full_content = get_complete_gutachten(gutachten_id)
                        if full_content and len(full_content) > current_length:
                            item["content"] = full_content
                            item["is_complete"] = True
                            item["debug_info"] = f"Erweitert von {current_length} auf {len(full_content)} Zeichen"
                        else:
                            item["is_complete"] = False
                            item["debug_info"] = f"Kein vollständiges Gutachten gefunden oder bereits vollständig. Original: {current_length} Zeichen"
                    except Exception as e:
                        item["is_complete"] = False
                        item["debug_info"] = f"Fehler beim Laden: {str(e)}"
                        pass  # Falls es fehlschlägt, behalte den ursprünglichen Content
            
            return result
        else:
            return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Connection Error: {str(e)}"}


def render_search_results(results: Dict, show_debug: bool = False):
    """Rendert Suchergebnisse im Original-DNOTI-Format."""
    
    if "error" in results:
        st.error(f"Fehler bei der Suche: {results['error']}")
        return

    if results.get("total_results", 0) == 0:
        st.warning("Keine Ergebnisse gefunden.")
        return    
    st.success(f"**{results['total_results']} Ergebnisse** gefunden in {results.get('search_time_ms', 0):.0f}ms")
    
    def extract_original_dnoti_data(result: Dict) -> Dict[str, str]:
        """Extrahiert Original-DNOTI-Daten aus der API-Antwort mit mehreren Fallback-Strategien"""
        metadata = result.get("metadata", {})
        content = result.get("content", result.get("text", ""))
        
        # Gutachten-Nummer-Extraktion mit "None"-Behandlung
        gutachten_nummer = 'N/A'
        source_id = metadata.get("source_gutachten_id")
        
        if source_id and str(source_id) != "None" and str(source_id).strip():
            gutachten_nummer = f"Gutachten Nr. {source_id}"
        elif metadata.get("gutachten_nummer") and str(metadata.get("gutachten_nummer")) != "None":
            gutachten_nummer = f"Gutachten Nr. {metadata['gutachten_nummer']}"
        elif metadata.get("gutachten_id") and str(metadata.get("gutachten_id")) != "None":
            gutachten_nummer = f"Gutachten Nr. {metadata['gutachten_id']}"
        else:
            # Fallback: Aus Content extrahieren
            import re
            patterns = [
                r'Gutachten[- ]?Nr\.?\s*(\d+)',
                r'Dokumentnummer:\s*(\d+)',
                r'GUTACHTEN\s+(\d+)',
                r'DNotI\s+(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    extracted_number = match.group(1)
                    if extracted_number.isdigit():
                        gutachten_nummer = f"Gutachten Nr. {extracted_number}"
                        break
        
        # Erscheinungsdatum-Extraktion
        erscheinungsdatum = metadata.get("erscheinungsdatum") or 'N/A'
        if not erscheinungsdatum or erscheinungsdatum == 'N/A':
            import re
            date_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', content)
            if date_match:
                erscheinungsdatum = date_match.group(1)
          # Normen-Extraktion
        normen = metadata.get("normen") or 'Nicht angegeben'
        if not normen or normen == 'Nicht angegeben':
            # Fallback: Normen aus Content extrahieren
            import re
            norm_pattern = r'(§§?\s*\d+[a-z]*(?:\s+Abs\.\s*\d+)?(?:\s+S\.\s*\d+)?\s+[A-Z]{2,6})'
            norm_matches = re.findall(norm_pattern, content[:500])  # Nur erste 500 Zeichen
            if norm_matches:
                normen = '; '.join(norm_matches[:5])  # Max 5 Normen
        
        dnoti_data = {
            'gutachten_nummer': gutachten_nummer,
            'erscheinungsdatum': erscheinungsdatum, 
            'rechtsbezug': metadata.get("rechtsbezug") or 'National',
            'normen': normen,
            'url': metadata.get("url") or '',
            'id': source_id if source_id and str(source_id) != "None" else 'N/A'
        }
        
        return dnoti_data
    
    # Ergebnisse anzeigen
    for i, result in enumerate(results.get("results", []), 1):
        with st.container():
            # Original DNOTI-Daten extrahieren
            dnoti_data = extract_original_dnoti_data(result)
            content = result.get("content", result.get("text", ""))
            
            # Encoding-Probleme korrigieren
            content = fix_encoding_issues(content)
            
            # DNOTI-Header im Original-Stil
            with st.container():
                # Header mit Datum
                st.markdown(f"""
                <div style="background-color: #f8fafc; padding: 0.5rem 1rem; border: 1px solid #e2e8f0; border-radius: 8px 8px 0 0; font-size: 12px; color: #64748b;">
                    ZURÜCK • {dnoti_data['erscheinungsdatum']}
                </div>
                """, unsafe_allow_html=True)
                
                # Normen
                st.markdown(f"""
                <div style="padding: 1rem; border-left: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; color: #1e40af; font-size: 14px; font-weight: 500;">
                    {dnoti_data['normen']}
                </div>
                """, unsafe_allow_html=True)
                
                # Titel
                title = extract_meaningful_title_new(content)
                st.markdown(f"""
                <div style="padding: 0 1rem 1rem 1rem; border-left: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0;">
                    <h3 style="color: #1e293b; font-size: 18px; font-weight: 600; margin: 0; line-height: 1.4;">
                        {title}
                    </h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Überblick
                st.markdown(f"""
                <div style="padding: 1rem; border: 1px solid #e2e8f0; border-radius: 0 0 8px 8px; background-color: #f8fafc;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: #1e293b;">ÜBERBLICK</strong>
                        <div style="font-size: 12px; color: #64748b;">
                            <a href="#" style="color: #3b82f6; text-decoration: none;">PDF VORSCHAU</a> | 
                            <a href="#" style="color: #3b82f6; text-decoration: none;">Download</a>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Gutachten-Inhalt im DNOTI-Stil - zeige vollständigen Content
            # Encoding-Probleme korrigieren
            clean_content = fix_encoding_issues(content)
            
            # Zeige den rohen Content ohne HTML-Escaping, da der schon sauber ist
            # Einfache Formatierung für bessere Lesbarkeit
            formatted_content = clean_content.replace('\n', '<br>')
              # Hervorhebung von Rechtsnormen ohne HTML-Escaping
            formatted_content = re.sub(r'(§\s*\d+[a-z]*(?:\s+Abs\.\s*\d+)?(?:\s+S\.\s*\d+)?\s+[A-Z]{2,6})', 
                                     r'<strong style="color: #1e40af; background-color: #eff6ff; padding: 2px 4px; border-radius: 3px;">\1</strong>', 
                                     formatted_content)
            formatted_content = re.sub(r'(Art\.\s*\d+[a-z]*(?:\s+Abs\.\s*\d+)?\s+[A-Z]{2,6})', 
                                     r'<strong style="color: #1e40af; background-color: #eff6ff; padding: 2px 4px; border-radius: 3px;">\1</strong>', 
                                     formatted_content)
            
            with st.expander("📖 Vollständiger Gutachten-Text", expanded=True):                # Debug-Info nur anzeigen wenn aktiviert
                if show_debug and "debug_info" in result:
                    st.info(f"🔧 Debug: {result['debug_info']}")
                
                st.markdown(f"""
                <div class="gutachten-content">
                    {formatted_content}
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()


def render_search_page():
    """Rendert die Suchseite."""
    st.title("🔍 DNOTI Rechtsgutachten Suche")
    
    # Debug-Option in der Sidebar
    with st.sidebar:
        st.subheader("⚙️ Einstellungen")
        show_debug = st.checkbox("Debug-Informationen anzeigen", value=False)
    
    with st.form("search_form"):
        query = st.text_input(
            "Suchbegriff eingeben:",
            placeholder="z.B. Befristung Dauernutzungsrecht, AGB öffentliche Hand..."        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_type = st.selectbox(
                "Suchtyp:",
                ["semantic", "hybrid", "keyword"],
                index=0,
                help="Semantic: KI-basierte Suche | Hybrid: Kombination | Keyword: Stichwortsuche"
            )
        
        with col2:
            limit = st.number_input("Ergebnisse:", min_value=1, max_value=50, value=10)
        
        submit_button = st.form_submit_button("🔍 Suchen", use_container_width=True)
    
    if submit_button and query:
        with st.spinner("Durchsuche Rechtsgutachten..."):
            results = search_documents(query, search_type, limit)
            if results:
                render_search_results(results, show_debug)
            else:
                st.error("Keine Suchergebnisse erhalten.")


def main():
    """Hauptfunktion der Streamlit-App."""
    st.set_page_config(
        page_title="DNOTI Legal Tech",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    render_search_page()


if __name__ == "__main__":
    main()


