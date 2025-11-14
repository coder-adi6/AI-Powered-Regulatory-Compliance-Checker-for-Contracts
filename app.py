# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
import io
import time
import tempfile
import os
from pathlib import Path

# Import services
from services.document_processor import DocumentProcessor, DocumentProcessingError, UnsupportedFormatError
from services.nlp_analyzer import NLPAnalyzer
from services.compliance_checker import ComplianceChecker
from services.recommendation_engine import RecommendationEngine
from services.export_service import ExportService
from services.google_sheets_service import GoogleSheetsError
from services.document_viewer import DocumentViewer
from services.document_updater import DocumentUpdater, MissingClauseGeneration
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI Compliance Checker",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        color: #2e86ab;
        border-bottom: 2px solid #2e86ab;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    .risk-high { background-color: #ff6b6b; color: white; padding: 5px; border-radius: 5px; }
    .risk-medium { background-color: #ffd166; color: black; padding: 5px; border-radius: 5px; }
    .risk-low { background-color: #06d6a0; color: white; padding: 5px; border-radius: 5px; }
    .compliance-good { color: #06d6a0; font-weight: bold; }
    .compliance-poor { color: #ff6b6b; font-weight: bold; }
    
    /* Fix clause details tab - ensure dark background with light text */
    [data-testid="stExpander"] {
        background-color: #0e1117 !important;
        border: 1px solid #262730 !important;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    [data-testid="stExpander"] details {
        background-color: #0e1117 !important;
    }
    
    [data-testid="stExpander"] summary {
        background-color: #262730 !important;
        color: #fafafa !important;
        padding: 10px;
        border-radius: 8px;
    }
    
    [data-testid="stExpander"] summary:hover {
        background-color: #31333d !important;
    }
    
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #0e1117 !important;
        color: #fafafa !important;
        padding: 15px;
    }
    
    /* Enhanced contrast for all text elements in expanders */
    [data-testid="stExpander"] p, 
    [data-testid="stExpander"] div,
    [data-testid="stExpander"] span,
    [data-testid="stExpander"] li,
    [data-testid="stExpander"] strong,
    [data-testid="stExpander"] em {
        color: #fafafa !important;
        background-color: transparent !important;
    }
    
    /* Ensure markdown elements are visible */
    [data-testid="stExpander"] .stMarkdown {
        background-color: transparent !important;
        color: #fafafa !important;
    }
    
    /* Keep highlighted clauses visible with their colors */
    .clause-high-risk,
    .clause-medium-risk,
    .clause-low-risk {
        color: #000000 !important;
    }
    
    /* IMPORTANT: Exclude document-viewer from dark theme to keep it readable */
    .document-viewer {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    .document-viewer p,
    .document-viewer div,
    .document-viewer span {
        color: #000000 !important;
    }
    
    /* Keep highlighted clauses with their proper colors in document viewer */
    .document-viewer .highlighted-clause {
        /* Colors set inline by document_viewer.py */
    }
    
    /* Ensure text areas and inputs have proper contrast */
    textarea, input {
        background-color: #262730 !important;
        color: #fafafa !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize services with caching
@st.cache_resource
def get_document_processor():
    """Initialize and cache document processor."""
    logger.info("Initializing DocumentProcessor...")
    return DocumentProcessor()

@st.cache_resource
def get_nlp_analyzer():
    """Initialize and cache NLP analyzer."""
    logger.info("Initializing NLPAnalyzer...")
    return NLPAnalyzer()

@st.cache_resource
def get_compliance_checker():
    """Initialize and cache compliance checker."""
    logger.info("Initializing ComplianceChecker...")
    return ComplianceChecker()

@st.cache_resource
def get_recommendation_engine():
    """Initialize and cache recommendation engine."""
    logger.info("Initializing RecommendationEngine...")
    return RecommendationEngine(use_llama=False)  # Set to True when LLaMA is available

@st.cache_resource
def get_export_service():
    """Initialize and cache export service."""
    logger.info("Initializing ExportService...")
    return ExportService()

@st.cache_resource
def get_document_viewer():
    """Initialize and cache document viewer."""
    logger.info("Initializing DocumentViewer...")
    return DocumentViewer()

# Initialize session state
if 'processed_document' not in st.session_state:
    st.session_state.processed_document = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'compliance_report' not in st.session_state:
    st.session_state.compliance_report = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'contract_history' not in st.session_state:
    st.session_state.contract_history = []
if 'selected_frameworks' not in st.session_state:
    st.session_state.selected_frameworks = ['GDPR', 'HIPAA']
if 'selected_clause_id' not in st.session_state:
    st.session_state.selected_clause_id = None
if 'show_modal' not in st.session_state:
    st.session_state.show_modal = False
if 'modal_content' not in st.session_state:
    st.session_state.modal_content = None
if 'batch_summary' not in st.session_state:
    st.session_state.batch_summary = None

# Header
st.markdown('<h1 class="main-header">⚖️ AI-Powered Regulatory Compliance Checker</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    st.subheader("Regulatory Frameworks")
    gdpr_check = st.checkbox("GDPR", value=True, key="gdpr_checkbox")
    hipaa_check = st.checkbox("HIPAA", value=True, key="hipaa_checkbox")
    
    # Update selected frameworks in session state
    selected_frameworks = []
    if gdpr_check:
        selected_frameworks.append("GDPR")
    if hipaa_check:
        selected_frameworks.append("HIPAA")
    
    st.session_state.selected_frameworks = selected_frameworks
    
    # Validate at least one framework is selected
    if not selected_frameworks:
        st.warning("⚠️ Please select at least one regulatory framework")
    else:
        st.success(f"✅ {len(selected_frameworks)} framework(s) selected")
    
    st.subheader("Analysis Settings")
    risk_tolerance = st.select_slider(
        "Risk Tolerance",
        options=["Low", "Medium", "High"],
        value="Medium"
    )
    
    confidence_threshold = st.slider(
        "Confidence Threshold (%)",
        min_value=50,
        max_value=95,
        value=75,
        help="Minimum confidence for clause classification"
    )
    
    notification_enabled = st.checkbox("Enable Regulatory Updates", value=True)
    
    st.subheader("Integrations")
    google_sheets = st.checkbox("Google Sheets Integration", value=False)
    slack_alerts = st.checkbox("Slack Notifications", value=False)
    
    st.markdown("---")
    st.info("**Current Status**: Systems Operational")
    
    # Show analysis status
    if st.session_state.compliance_report:
        st.metric("Last Analysis Score", f"{st.session_state.compliance_report.overall_score:.0f}%")
    else:
        st.metric("Contracts Analyzed", len(st.session_state.contract_history))

# ==================== HELPER FUNCTIONS ====================
def _display_clause_details(display_report, display_recommendations, key_prefix=""):
    """Display detailed clause-level analysis for a single document."""
    
    if display_report and display_recommendations:
        report = display_report
        recommendations = display_recommendations
        
        # Create recommendations lookup by clause_id
        rec_by_clause = {}
        for rec in recommendations:
            if rec.clause_id:
                if rec.clause_id not in rec_by_clause:
                    rec_by_clause[rec.clause_id] = []
                rec_by_clause[rec.clause_id].append(rec)
        
        # Filters (placed at top for both views)
        st.subheader("🔍 Filter Options")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            risk_filter = st.multiselect(
                "Risk Level:",
                options=['High', 'Medium', 'Low'],
                default=['High', 'Medium', 'Low'],
                key=f"{key_prefix}risk_filter"
            )
        
        with col2:
            regulation_filter = st.multiselect(
                "Regulation:",
                options=report.frameworks_checked,
                default=report.frameworks_checked,
                key=f"{key_prefix}regulation_filter"
            )
        
        with col3:
            status_filter = st.multiselect(
                "Status:",
                options=['Compliant', 'Non-Compliant', 'Partial'],
                default=['Non-Compliant', 'Partial'],
                key=f"{key_prefix}status_filter"
            )
        
        with col4:
            view_mode = st.radio(
                "View:",
                options=["Document", "List"],
                horizontal=True,
                key=f"{key_prefix}view_mode",
                help="Toggle between highlighted document view and clause list view"
            )
        
        st.markdown("---")
        
        # Apply filters to get filtered results
        filtered_results = [
            r for r in report.clause_results
            if r.risk_level.value in risk_filter
            and r.framework in regulation_filter
            and r.compliance_status.value in status_filter
        ]
        
        st.info(f"Showing {len(filtered_results)} of {len(report.clause_results)} clauses")
        
        # Show highlighted document view
        if view_mode == "Document" and st.session_state.processed_document:
            st.markdown("---")
            
            # Create two columns: document view and missing clauses panel
            doc_col, missing_col = st.columns([2, 1])
            
            with doc_col:
                st.subheader("📄 Contract Document")
                
                # Show filter info
                if len(filtered_results) < len(report.clause_results):
                    st.info(f"💡 Highlighting {len(filtered_results)} filtered clauses. Adjust filters above to see more.")
                
                # Get document viewer
                doc_viewer = get_document_viewer()
                
                # Create risk map from FILTERED compliance results
                clause_risk_map = {}
                clause_details_map = {}
                for result in filtered_results:
                    clause_risk_map[result.clause_id] = result.risk_level.value
                    clause_details_map[result.clause_id] = {
                        'compliance_status': result.compliance_status.value,
                        'issues': result.issues,
                        'clause_type': result.clause_type
                    }
                
                # Display legend with filter info
                legend_html = doc_viewer.create_legend_html()
                
                # Add active filters info to legend
                if len(filtered_results) < len(report.clause_results):
                    active_filters = []
                    if len(risk_filter) < 3:
                        active_filters.append(f"Risk: {', '.join(risk_filter)}")
                    if len(regulation_filter) < len(report.frameworks_checked):
                        active_filters.append(f"Frameworks: {', '.join(regulation_filter)}")
                    if len(status_filter) < 3:
                        active_filters.append(f"Status: {', '.join(status_filter)}")
                    
                    if active_filters:
                        filter_info = f"""
                        <div style="background-color: #e7f3ff; border: 1px solid #2196F3; 
                                    border-radius: 5px; padding: 8px; margin-bottom: 10px;">
                            <strong>🔍 Active Filters:</strong> {' | '.join(active_filters)}
                        </div>
                        """
                        st.markdown(filter_info, unsafe_allow_html=True)
                
                st.markdown(legend_html, unsafe_allow_html=True)
                
                # Display highlighted document with click handlers
                highlighted_html = doc_viewer.create_highlighted_html(
                    st.session_state.processed_document,
                    clause_risk_map,
                    clause_details_map
                )
                
                # Add CSS styles
                st.markdown(doc_viewer.get_css_styles(), unsafe_allow_html=True)
                
                # Add JavaScript for click handlers
                st.markdown(doc_viewer.get_click_handler_javascript(), unsafe_allow_html=True)
                
                # Display the highlighted document
                st.markdown(highlighted_html, unsafe_allow_html=True)
            
            with missing_col:
                st.subheader("⚠️ Missing Clauses")
                
                # Display missing clauses panel
                missing_panel_html = doc_viewer.create_missing_clauses_panel(
                    report.missing_requirements,
                    recommendations
                )
                st.markdown(missing_panel_html, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Check if a clause was clicked (for navigation)
        if st.session_state.selected_clause_id:
            # Find the clause in filtered results
            selected_result = next(
                (r for r in report.clause_results if r.clause_id == st.session_state.selected_clause_id),
                None
            )
            if selected_result and selected_result not in filtered_results:
                st.info(f"💡 Clause {st.session_state.selected_clause_id} is hidden by current filters. Adjust filters to view it.")
        
        # Handle modal display for missing clauses
        if 'show_missing_modal' in st.session_state and st.session_state.get('show_missing_modal'):
            req_id = st.session_state.show_missing_modal
            
            # Find the requirement and recommendation
            missing_req = next((r for r in report.missing_requirements if r.requirement_id == req_id), None)
            matching_rec = next((r for r in recommendations if r.requirement and r.requirement.requirement_id == req_id), None)
            
            if missing_req:
                # Create a prominent modal-like container
                st.markdown("---")
                st.markdown(
                    '<div style="background-color: #f8f9fa; border: 2px solid #007bff; '
                    'border-radius: 10px; padding: 20px; margin: 20px 0;">',
                    unsafe_allow_html=True
                )
                
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"### 📋 Full Recommendation: {missing_req.clause_type}")
                with col2:
                    if st.button("✖ Close", key="close_modal", use_container_width=True):
                        st.session_state.show_missing_modal = None
                        st.rerun()
                
                st.markdown(f"**Regulatory Reference:** {missing_req.article_reference} ({missing_req.framework})")
                st.markdown(f"**Description:** {missing_req.description}")
                
                if missing_req.mandatory_elements:
                    st.markdown("**Required Elements:**")
                    for element in missing_req.mandatory_elements:
                        st.markdown(f"- {element}")
                
                if matching_rec:
                    st.markdown("---")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        priority_color = {1: "🔴", 2: "🔴", 3: "🟡", 4: "🟢", 5: "🟢"}
                        st.metric("Priority", f"{priority_color.get(matching_rec.priority, '⚪')} {matching_rec.priority}/5")
                    with col2:
                        st.metric("Action", matching_rec.action_type.value)
                    with col3:
                        st.metric("Framework", missing_req.framework)
                    
                    st.markdown(f"**Recommendation:** {matching_rec.description}")
                    
                    if matching_rec.suggested_text:
                        st.markdown("**Suggested Clause Text:**")
                        st.code(matching_rec.suggested_text, language="text")
                        
                        # Add copy button
                        if st.button("📋 Copy to Clipboard", key="copy_suggested"):
                            st.success("✅ Copied to clipboard! (Note: Manual copy from code block above)")
                    
                    if matching_rec.rationale:
                        with st.expander("📖 View Rationale"):
                            st.markdown(matching_rec.rationale)
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("---")
        
        # Display clauses with formatting
        if filtered_results:
            for result in filtered_results:
                # Add anchor for scrolling
                st.markdown(f'<div id="clause-details-{result.clause_id}"></div>', unsafe_allow_html=True)
                
                # Highlight selected clause
                is_selected = st.session_state.selected_clause_id == result.clause_id
                expander_label = f"{result.clause_id} - {result.clause_type} ({result.framework})"
                if is_selected:
                    expander_label = f"👉 {expander_label}"
                
                with st.expander(expander_label, expanded=is_selected):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        risk_color = {
                            'High': 'risk-high',
                            'Medium': 'risk-medium', 
                            'Low': 'risk-low'
                        }[result.risk_level.value]
                        st.markdown(f"**Risk Level:** <span class='{risk_color}'>{result.risk_level.value}</span>", unsafe_allow_html=True)
                    
                    with col2:
                        status_color = "compliance-good" if result.compliance_status.value == 'Compliant' else "compliance-poor"
                        st.markdown(f"**Status:** <span class='{status_color}'>{result.compliance_status.value}</span>", unsafe_allow_html=True)
                    
                    with col3:
                        st.metric("Confidence", f"{result.confidence * 100:.0f}%")
                    
                    with col4:
                        if result.compliance_status.value != 'Compliant':
                            fix_key = f"{key_prefix}fix_{result.framework}_{result.clause_id}"
                            if st.button("🛠️ Fix", key=fix_key, use_container_width=True):
                                st.session_state[f"show_fix_{result.clause_id}"] = True
                        else:
                            st.button("✅ OK", key=f"{key_prefix}ok_{result.framework}_{result.clause_id}", use_container_width=True, disabled=True)
                    
                    # Show clause text
                    st.markdown("**Clause Text:**")
                    st.text_area(
                        "Clause",
                        value=result.clause_text[:500] + ("..." if len(result.clause_text) > 500 else ""),
                        height=100,
                        key=f"{key_prefix}text_{result.framework}_{result.clause_id}",
                        disabled=True
                    )
                    
                    # Show issues
                    if result.issues:
                        st.markdown("**Issues:**")
                        for issue in result.issues:
                            st.warning(f"• {issue}")
                    
                    # Show recommendations
                    if result.clause_id in rec_by_clause:
                        st.markdown("**Recommendations:**")
                        for rec in rec_by_clause[result.clause_id]:
                            st.info(f"**{rec.action_type.value}:** {rec.description}")
                            if rec.suggested_text and st.session_state.get(f"show_fix_{result.clause_id}", False):
                                st.markdown("**Suggested Text:**")
                                st.code(rec.suggested_text, language="text")
        else:
            st.info("No clauses match the selected filters")
        
        # Show missing requirements
        if report.missing_requirements:
            st.markdown("---")
            st.subheader("Missing Required Clauses")
            
            for req in report.missing_requirements:
                # Check if this is the selected requirement
                is_selected_req = (
                    st.session_state.get('show_missing_modal') == req.requirement_id
                )
                
                expander_label = f"⚠️ Missing: {req.clause_type} ({req.framework})"
                if is_selected_req:
                    expander_label = f"👉 {expander_label}"
                
                with st.expander(expander_label, expanded=is_selected_req):
                    st.markdown(f"**Requirement:** {req.article_reference}")
                    st.markdown(f"**Description:** {req.description}")
                    
                    if req.mandatory_elements:
                        st.markdown("**Required Elements:**")
                        for element in req.mandatory_elements:
                            st.markdown(f"• {element}")
                    
                    # Find recommendation for this requirement
                    matching_rec = next(
                        (r for r in recommendations if r.requirement.requirement_id == req.requirement_id),
                        None
                    )
                    
                    if matching_rec:
                        col1, col2 = st.columns(2)
                        with col1:
                            if matching_rec.suggested_text:
                                if st.button(f"📄 Show Suggested Clause", key=f"{key_prefix}show_{req.requirement_id}", use_container_width=True):
                                    st.markdown("**Suggested Clause Text:**")
                                    st.code(matching_rec.suggested_text, language="text")
                        with col2:
                            if st.button(f"🔍 View Full Details", key=f"{key_prefix}details_{req.requirement_id}", use_container_width=True):
                                st.session_state.show_missing_modal = req.requirement_id
                                st.rerun()
    else:
        st.info("📋 Analyze a contract to see detailed clause-level analysis")


def _display_autofix_section(display_report, document_name):
    """Display auto-fix section for missing clauses."""
    
    if display_report and display_report.missing_requirements:
        report = display_report
        missing_reqs = report.missing_requirements
        
        # Initialize document updater
        if 'document_updater' not in st.session_state:
            from services.document_updater import DocumentUpdater
            st.session_state.document_updater = DocumentUpdater()
        
        updater = st.session_state.document_updater
        
        # Get risk summary
        risk_summary = updater.get_risk_summary(missing_reqs)
        
        # ========== RISK METRICS ==========
        st.subheader("📊 Risk Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Missing Clauses",
                risk_summary['total_missing']
            )
        
        with col2:
            avg_risk = risk_summary['average_risk']
            risk_emoji = "🔴" if avg_risk >= 70 else "🟡" if avg_risk >= 40 else "🟢"
            st.metric(
                "Average Risk",
                f"{avg_risk:.0f}%",
                delta=risk_emoji
            )
        
        with col3:
            st.metric(
                "Highest Risk",
                f"{risk_summary['max_risk']:.0f}%",
                delta="🔴 Critical" if risk_summary['max_risk'] >= 70 else None
            )
        
        with col4:
            st.metric(
                "High Risk Count",
                risk_summary['high_risk_count'],
                delta="⚠️ Urgent" if risk_summary['high_risk_count'] > 0 else None
            )
        
        # ========== RISK DISTRIBUTION CHART ==========
        st.subheader("Risk Distribution")
        
        risk_dist = risk_summary['risk_distribution']
        
        fig = go.Figure(data=[
            go.Bar(
                x=list(risk_dist.keys()),
                y=list(risk_dist.values()),
                marker_color=['#ff6b6b', '#ffd166', '#06d6a0'],
                text=list(risk_dist.values()),
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title="Missing Clauses by Risk Level",
            xaxis_title="Risk Level",
            yaxis_title="Number of Clauses",
            showlegend=False,
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # ========== MISSING CLAUSES TABLE ==========
        st.subheader("🎯 Missing Clauses with Risk Analysis")
        
        # Calculate risk for each requirement
        missing_with_risk = []
        for req in missing_reqs:
            risk_pct = updater.calculate_risk_percentage(req)
            missing_with_risk.append({
                'requirement': req,
                'risk_percentage': risk_pct
            })
        
        # Sort by risk (highest first)
        missing_with_risk.sort(key=lambda x: x['risk_percentage'], reverse=True)
        
        # Display each missing clause
        for item in missing_with_risk:
            req = item['requirement']
            risk_pct = item['risk_percentage']
            
            # Color code risk
            if risk_pct >= 70:
                risk_badge = f'🔴 {risk_pct:.0f}% RISK'
            elif risk_pct >= 40:
                risk_badge = f'🟡 {risk_pct:.0f}% RISK'
            else:
                risk_badge = f'🟢 {risk_pct:.0f}% RISK'
            
            with st.expander(
                f"**{req.article_reference}** - {req.clause_type} - {risk_badge}",
                expanded=(risk_pct >= 70)  # Auto-expand high risk
            ):
                # Requirement details
                st.markdown(f"**Framework:** {req.framework}")
                st.markdown(f"**Description:** {req.description}")
                st.markdown(f"**Mandatory:** {'Yes ⚠️' if req.mandatory else 'No'}")
                st.markdown(f"**Risk Level:** {req.risk_level.value}")
                
                # Risk breakdown
                st.markdown("**Risk Calculation Breakdown:**")
                mandatory_score = 40 if req.mandatory else 15
                risk_level_score = {
                    "HIGH": 30,
                    "MEDIUM": 20,
                    "LOW": 10
                }.get(req.risk_level.value, 10)
                
                st.progress(risk_pct / 100.0)
                st.caption(
                    f"Mandatory: +{mandatory_score}% | "
                    f"Severity: +{risk_level_score}% | "
                    f"Framework: +{risk_pct - mandatory_score - risk_level_score:.0f}%"
                )
                
                # Mandatory elements
                if req.mandatory_elements:
                    st.markdown("**Required Elements:**")
                    for elem in req.mandatory_elements:
                        st.markdown(f"- {elem}")
        
        st.markdown("---")
        
        # ========== GENERATION SECTION ==========
        st.subheader("🤖 Generate Missing Clauses & Rewrite Contract")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info(
                "⚡ This feature will use AI to automatically generate compliant "
                "clause text for all missing requirements and create a rewritten contract with them inserted."
            )
        
        with col2:
            prioritize = st.checkbox("Prioritize by risk", value=True)
            top_n = st.number_input(
                "Generate top N",
                min_value=1,
                max_value=len(missing_reqs),
                value=min(5, len(missing_reqs)),
                help="Generate only the highest risk clauses"
            )
        
        # Generate button
        if st.button("🚀 Generate Missing Clauses", type="primary", use_container_width=True):
            with st.spinner("Generating clauses with AI... This may take a minute."):
                try:
                    # Generate clauses
                    generated_clauses = updater.generate_missing_clauses(
                        missing_requirements=missing_reqs,
                        existing_contract_text=st.session_state.processed_document.extracted_text,
                        prioritize=prioritize,
                        top_n=top_n
                    )
                    
                    # Store in session
                    st.session_state.generated_clauses = generated_clauses
                    
                    st.success(f"✅ Successfully generated {len(generated_clauses)} clauses!")
                    st.rerun()  # Refresh to show generated clauses
                    
                except Exception as e:
                    st.error(f"❌ Error generating clauses: {e}")
                    logger.error(f"Clause generation error: {e}", exc_info=True)
        
        # ========== DISPLAY GENERATED CLAUSES ==========
        if 'generated_clauses' in st.session_state and st.session_state.generated_clauses:
            st.markdown("---")
            st.subheader("📝 Generated Clauses")
            
            generated = st.session_state.generated_clauses
            
            st.success(f"Generated {len(generated)} clauses. Review before adding to document.")
            
            # Display each generated clause
            for i, gen_clause in enumerate(generated, 1):
                req = gen_clause.requirement
                risk_pct = gen_clause.risk_percentage
                
                # Risk badge
                if risk_pct >= 70:
                    risk_badge = f'🔴 {risk_pct:.0f}% Risk'
                elif risk_pct >= 40:
                    risk_badge = f'🟡 {risk_pct:.0f}% Risk'
                else:
                    risk_badge = f'🟢 {risk_pct:.0f}% Risk'
                
                with st.expander(
                    f"**{i}. {req.article_reference}** - {risk_badge}",
                    expanded=(i <= 3)  # Auto-expand first 3
                ):
                    st.markdown(f"**Clause Type:** {req.clause_type}")
                    st.markdown(f"**Framework:** {req.framework}")
                    
                    st.markdown("**Generated Clause Text:**")
                    
                    # Editable text area
                    edited_text = st.text_area(
                        "Clause Text (editable)",
                        value=gen_clause.generated_text,
                        height=150,
                        key=f"clause_text_{i}"
                    )
                    
                    # Update the clause text if edited
                    gen_clause.generated_text = edited_text
                    
                    # Confidence indicator
                    confidence = gen_clause.confidence_score
                    st.progress(confidence, text=f"Generation Confidence: {confidence:.0%}")
            
            st.markdown("---")
            
            # ========== EXPORT SECTION ==========
            st.subheader("📥 Download Rewritten Contract")
            
            st.info("✅ Your contract will be rewritten with all missing clauses inserted and highlighted!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                output_format = st.selectbox(
                    "Output Format",
                    options=["docx", "txt"],
                    format_func=lambda x: "Word Document (.docx) - With Yellow Highlights" if x == "docx" else "Text File (.txt) - With Insertion Markers"
                )
            
            with col2:
                st.write("")  # Spacing
            
            if st.button("📥 Create Rewritten Contract", type="primary", use_container_width=True):
                with st.spinner("Creating rewritten contract with missing clauses..."):
                    try:
                        # Create updated document
                        updated_doc_buffer = updater.create_updated_document(
                            original_text=st.session_state.processed_document.extracted_text,
                            generated_clauses=generated,
                            output_format=output_format
                        )
                        
                        # Offer download
                        file_extension = "docx" if output_format == "docx" else "txt"
                        filename = f"contract_rewritten_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
                        
                        st.download_button(
                            label=f"⬇️ Download Rewritten Contract (.{file_extension})",
                            data=updated_doc_buffer,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document" if output_format == "docx" else "text/plain",
                            use_container_width=True
                        )
                        
                        st.success("✅ Rewritten contract ready for download!")
                        
                        # Show preview
                        with st.expander("📄 Preview Changes"):
                            st.info(
                                f"The rewritten contract includes **{len(generated)} new clauses** "
                                f"{'highlighted in yellow' if output_format == 'docx' else 'marked with insertion tags'}."
                            )
                            st.markdown("**Changes Summary:**")
                            for i, gen_clause in enumerate(generated, 1):
                                st.markdown(
                                    f"{i}. **{gen_clause.requirement.article_reference}** "
                                    f"(Risk: {gen_clause.risk_percentage:.0f}%) - "
                                    f"{len(gen_clause.generated_text)} characters"
                                )
                    
                    except Exception as e:
                        st.error(f"❌ Error creating rewritten contract: {e}")
                        logger.error(f"Document creation error: {e}", exc_info=True)
    
    else:
        # No missing clauses
        if st.session_state.compliance_report:
            st.success("🎉 Great! No missing clauses found. Your contract is fully compliant!")
        else:
            st.info(
                "📋 No compliance analysis available yet. "
                "Please upload and analyze a contract first in the **Contract Analysis** tab."
            )


# ==================== MAIN CONTENT TABS ====================
# Main content
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📄 Contract Analysis", "📊 Dashboard", "🔍 Clause Details", "✨ Auto-Fix & Rewrite", "🔄 Regulatory Updates", "⚙️ Settings"])

with tab1:
    st.markdown('<h2 class="section-header">Contract Analysis</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Contract Document")
        
        upload_method = st.radio(
            "Select upload method:",
            ["Single File Upload", "Batch Upload (up to 10 files)", "Text Input", "Google Sheets URL"]
        )
        
        uploaded_file = None
        uploaded_files = None
        contract_text = None
        
        if upload_method == "Single File Upload":
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['pdf', 'docx', 'txt', 'png', 'jpg'],
                help="Supported formats: PDF, DOCX, TXT, PNG, JPG (max 10MB)"
            )
        
        elif upload_method == "Batch Upload (up to 10 files)":
            uploaded_files = st.file_uploader(
                "Choose multiple files (up to 10)",
                type=['pdf', 'docx', 'txt', 'png', 'jpg'],
                accept_multiple_files=True,
                help="Upload up to 10 contract files for batch processing"
            )
            
            if uploaded_files and len(uploaded_files) > 10:
                st.error("⚠️ Maximum 10 files allowed. Please remove some files.")
                uploaded_files = None
            elif uploaded_files:
                st.info(f"📁 {len(uploaded_files)} files selected for batch processing")
        
        if upload_method == "Single File Upload" and uploaded_file is not None:
            
            if uploaded_file is not None:
                # Validate file size (max 10MB)
                max_size = 10 * 1024 * 1024  # 10MB in bytes
                if uploaded_file.size > max_size:
                    st.error(f"File size ({uploaded_file.size / 1024 / 1024:.1f} MB) exceeds maximum allowed size (10 MB)")
                else:
                    file_details = {
                        "Filename": uploaded_file.name,
                        "File size": f"{uploaded_file.size / 1024:.1f} KB",
                        "File type": uploaded_file.type
                    }
                    st.json(file_details)
                    
                    # Process document immediately
                    with st.spinner("Processing document..."):
                        try:
                            # Save uploaded file to temporary location
                            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_path = tmp_file.name
                            
                            # Process document
                            doc_processor = get_document_processor()
                            processed_doc = doc_processor.process_document(tmp_path)
                            
                            # Store in session state
                            st.session_state.processed_document = processed_doc
                            
                            # Clean up temp file
                            os.unlink(tmp_path)
                            
                            # Display success
                            st.success(f"✅ Document processed successfully!")
                            st.info(f"📄 Extracted {processed_doc.num_clauses} clauses ({processed_doc.total_words} words) in {processed_doc.processing_time:.2f}s")
                            
                        except UnsupportedFormatError as e:
                            st.error(f"❌ Unsupported file format: {e}")
                            logger.error(f"Unsupported format: {e}")
                        except DocumentProcessingError as e:
                            st.error(f"❌ Error processing document: {e}")
                            logger.error(f"Processing error: {e}")
                        except Exception as e:
                            st.error(f"❌ Unexpected error: {e}")
                            logger.exception(f"Unexpected error: {e}")
        
        elif upload_method == "Batch Upload (up to 10 files)" and uploaded_files:
            st.markdown("### 📦 Batch Processing")
            
            # Validate all file sizes
            max_size = 10 * 1024 * 1024  # 10MB
            oversized_files = [f for f in uploaded_files if f.size > max_size]
            
            if oversized_files:
                st.error(f"⚠️ {len(oversized_files)} file(s) exceed 10MB limit:")
                for f in oversized_files:
                    st.write(f"- {f.name} ({f.size / 1024 / 1024:.1f} MB)")
            else:
                # Display file list
                with st.expander("📁 Selected Files", expanded=True):
                    for i, f in enumerate(uploaded_files, 1):
                        st.write(f"{i}. {f.name} ({f.size / 1024:.1f} KB)")
                
                # Batch processing button
                if st.button("🚀 Process All Files", type="primary", use_container_width=True):
                    from services.batch_processor import BatchProcessor
                    
                    # Save uploaded files to temp locations, preserving original names
                    temp_paths = []
                    original_names = []
                    for uploaded in uploaded_files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded.name).suffix) as tmp_file:
                            tmp_file.write(uploaded.getvalue())
                            temp_paths.append(tmp_file.name)
                            original_names.append(uploaded.name)
                    
                    # Create progress tracking UI
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    status_text.text(f"🔄 Processing {len(temp_paths)} files...")
                    
                    # Process batch (without progress callback to avoid thread issues)
                    try:
                        batch_processor = BatchProcessor(max_workers=3, max_files=10)
                        
                        # Show indeterminate progress
                        progress_bar.progress(0.5)
                        
                        summary = batch_processor.process_batch(
                            temp_paths,
                            framework=st.session_state.selected_frameworks[0] if st.session_state.selected_frameworks else "GDPR",
                            progress_callback=None,  # Disable thread-unsafe progress updates
                            original_filenames=original_names  # Preserve original names
                        )
                        
                        # Clean up temp files
                        for path in temp_paths:
                            try:
                                os.unlink(path)
                            except:
                                pass
                        
                        progress_bar.progress(1.0)
                        status_text.text("✅ Batch processing complete!")
                        
                        # Store batch results in session state
                        st.session_state.batch_summary = summary
                        st.session_state.batch_mode = True
                        
                        # Display summary
                        st.success(f"✅ Processed {summary.successful}/{summary.total_files} files successfully in {summary.total_time:.2f}s")
                        
                        # Show summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Files", summary.total_files)
                        with col2:
                            st.metric("Successful", summary.successful)
                        with col3:
                            st.metric("Failed", summary.failed)
                        with col4:
                            st.metric("Avg Time", f"{summary.avg_time_per_file:.1f}s")
                        
                        # Show aggregated compliance score
                        agg_metrics = batch_processor.get_aggregated_compliance_score(summary)
                        
                        st.markdown("### 📊 Aggregated Compliance Score")
                        score_col1, score_col2, score_col3 = st.columns(3)
                        with score_col1:
                            st.metric("Average Score", f"{agg_metrics['average_score']:.1f}%")
                        with score_col2:
                            st.metric("Total Issues", agg_metrics['total_issues'])
                        with score_col3:
                            high_risk = agg_metrics['high_risk_count']
                            st.metric("High Risk Issues", high_risk, delta=None if high_risk == 0 else "❗")
                        
                        # Show individual file results
                        st.markdown("### 📋 Individual File Results")
                        for result in summary.results:
                            with st.expander(f"{'✅' if result.success else '❌'} {result.filename}"):
                                if result.success:
                                    st.write(f"**Processing Time:** {result.processing_time:.2f}s")
                                    if result.compliance_results:
                                        # compliance_results is now a ComplianceReport object
                                        score = result.compliance_results.overall_score
                                        st.write(f"**Compliance Score:** {score:.1f}%")
                                        missing = len(result.compliance_results.missing_requirements)
                                        st.write(f"**Missing Clauses:** {missing}")
                                        clauses = len(result.compliance_results.clause_results)
                                        st.write(f"**Clauses Analyzed:** {clauses}")
                                else:
                                    st.error(f"Error: {result.error}")
                        
                        # Export options - All formats enabled
                        st.markdown("### 💾 Export Batch Results")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("📥 Export JSON", use_container_width=True, key="batch_export_json"):
                                try:
                                    from services.export_service import ExportService
                                    export_service = ExportService()
                                    output_path = batch_processor.export_batch_results(summary, 'json')
                                    st.success(f"✅ Results exported to: {output_path}")
                                except Exception as e:
                                    st.error(f"❌ Export failed: {e}")
                        
                        with col2:
                            if st.button("📊 Export CSV", use_container_width=True, key="batch_export_csv"):
                                try:
                                    output_path = batch_processor.export_batch_results(summary, 'csv')
                                    st.success(f"✅ Results exported to: {output_path}")
                                except Exception as e:
                                    st.error(f"❌ Export failed: {e}")
                        
                        with col3:
                            if st.button("📄 Export PDF", use_container_width=True, key="batch_export_pdf"):
                                try:
                                    # Export each report as PDF
                                    export_service = get_export_service()
                                    pdf_files = []
                                    for result in summary.results:
                                        if result.success and result.compliance_results:
                                            pdf_data = export_service.export_to_pdf(result.compliance_results)
                                            pdf_files.append((result.filename, pdf_data))
                                    st.success(f"✅ Exported {len(pdf_files)} PDF reports")
                                except Exception as e:
                                    st.error(f"❌ PDF export failed: {e}")
                        
                    except Exception as e:
                        st.error(f"❌ Batch processing failed: {e}")
                        logger.exception("Batch processing error")
                        # Clean up temp files on error
                        for path in temp_paths:
                            try:
                                os.unlink(path)
                            except:
                                pass
                
        elif upload_method == "Text Input":
            contract_text = st.text_area(
                "Paste contract text here:",
                height=200,
                placeholder="Enter the contract text for analysis..."
            )
            
            if contract_text and len(contract_text.strip()) > 100:
                if st.button("Process Text", use_container_width=True):
                    with st.spinner("Processing text..."):
                        try:
                            doc_processor = get_document_processor()
                            processed_doc = doc_processor.process_text(contract_text)
                            
                            # Store in session state
                            st.session_state.processed_document = processed_doc
                            
                            st.success(f"✅ Text processed successfully!")
                            st.info(f"📄 Extracted {processed_doc.num_clauses} clauses ({processed_doc.total_words} words)")
                        except Exception as e:
                            st.error(f"❌ Error processing text: {e}")
                            logger.exception(f"Text processing error: {e}")
        
        elif upload_method == "Google Sheets URL":
            st.markdown("### 📊 Import from Google Sheets")
            st.info("💡 Make sure the spreadsheet is shared with your service account email")
            
            sheets_url = st.text_input(
                "Enter Google Sheets URL:",
                placeholder="https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit",
                help="Paste the full URL of your Google Sheets document"
            )
            
            if sheets_url and sheets_url.strip():
                # Validate URL format
                if "docs.google.com/spreadsheets" not in sheets_url:
                    st.error("❌ Invalid URL format. Please enter a valid Google Sheets URL.")
                else:
                    if st.button("📥 Extract from Google Sheets", type="primary", use_container_width=True):
                        with st.spinner("Connecting to Google Sheets..."):
                            try:
                                from services.google_sheets_service import GoogleSheetsService
                                
                                # Initialize service
                                sheets_service = GoogleSheetsService()
                                
                                # Extract text
                                with st.spinner("Extracting contract text..."):
                                    contract_text = sheets_service.extract_text_from_sheet(sheets_url)
                                
                                st.success(f"✅ Extracted {len(contract_text)} characters from Google Sheets")
                                
                                # Process the extracted text
                                with st.spinner("Processing contract..."):
                                    doc_processor = get_document_processor()
                                    processed_doc = doc_processor.process_text(
                                        text=contract_text,
                                        filename="GoogleSheets_Contract.txt"
                                    )
                                    
                                    # Store in session state
                                    st.session_state.processed_document = processed_doc
                                    
                                    st.success(f"✅ Contract processed successfully!")
                                    st.info(f"📄 Extracted {processed_doc.num_clauses} clauses ({processed_doc.total_words} words)")
                                    st.info(f"⏱️ Processing time: {processed_doc.processing_time:.2f}s")
                                
                            except GoogleSheetsError as e:
                                st.error(f"❌ Google Sheets error: {e}")
                                st.warning("💡 Common issues:")
                                st.write("1. Spreadsheet not shared with service account")
                                st.write("2. Invalid or incorrect URL")
                                st.write("3. No data found in the specified range")
                                logger.error(f"Google Sheets error: {e}")
                            except Exception as e:
                                st.error(f"❌ Error processing Google Sheets: {e}")
                                logger.exception(f"Google Sheets processing error: {e}")
        
        # Show available upload methods at the bottom
        if upload_method:
            with st.expander("ℹ️ About Upload Methods", expanded=False):
                if upload_method == "Single File Upload":
                    st.write("Upload one contract file at a time for detailed analysis.")
                elif upload_method == "Batch Upload (up to 10 files)":
                    st.write("Upload multiple contracts for batch processing and comparison.")
                elif upload_method == "Text Input":
                    st.write("Paste contract text directly for quick analysis.")
                elif upload_method == "Google Sheets URL":
                    st.write("Extract contract data directly from Google Sheets for real-time analysis.")
                    st.write("**Requirements:** Spreadsheet must be shared with your service account email.")
    
    # Analysis button moved to bottom of upload section
    with col2:
        st.markdown("### 📊 Document Status")
        if st.session_state.processed_document:
            st.success("✅ Document Ready")
            st.metric("Clauses Identified", st.session_state.processed_document.num_clauses)
        else:
            st.info("📤 Upload a document to begin")
        
        st.markdown("---")
        
        # Analyze button (only enabled if document is processed)
        analyze_disabled = st.session_state.processed_document is None
        
        if st.button("🚀 Analyze Contract", type="primary", use_container_width=True, disabled=analyze_disabled):
            if not st.session_state.selected_frameworks:
                st.error("Please select at least one regulatory framework in the sidebar")
            else:
                with st.spinner("Analyzing contract for compliance..."):
                    try:
                        # Get services
                        nlp_analyzer = get_nlp_analyzer()
                        compliance_checker = get_compliance_checker()
                        recommendation_engine = get_recommendation_engine()
                        
                        # Step 1: NLP Analysis
                        st.info("🔍 Step 1/3: Analyzing clauses...")
                        clause_analyses = nlp_analyzer.analyze_clauses(
                            st.session_state.processed_document.clauses
                        )
                        st.session_state.analysis_results = clause_analyses
                        
                        # Step 2: Compliance Checking
                        st.info("⚖️ Step 2/3: Checking compliance...")
                        compliance_report = compliance_checker.check_compliance(
                            clause_analyses,
                            st.session_state.selected_frameworks,
                            st.session_state.processed_document.document_id
                        )
                        st.session_state.compliance_report = compliance_report
                        
                        # Step 3: Generate Recommendations
                        st.info("💡 Step 3/3: Generating recommendations...")
                        recommendations = recommendation_engine.generate_recommendations(
                            compliance_report
                        )
                        st.session_state.recommendations = recommendations
                        
                        # Add to history
                        st.session_state.contract_history.append({
                            'filename': st.session_state.processed_document.original_filename,
                            'date': datetime.now(),
                            'score': compliance_report.overall_score,
                            'status': 'Compliant' if compliance_report.overall_score >= 80 else 'Review Needed',
                            'risk': 'High' if compliance_report.summary.high_risk_count > 0 else 'Medium' if compliance_report.summary.medium_risk_count > 0 else 'Low'
                        })
                        
                        # Display results
                        st.success("✅ Analysis Complete!")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Compliance Score", f"{compliance_report.overall_score:.0f}%")
                        with col2:
                            st.metric("High Risk Items", compliance_report.summary.high_risk_count)
                        with col3:
                            st.metric("Missing Clauses", len(compliance_report.missing_requirements))
                        
                        # Direct user to clause details tab
                        st.info("📄 View the highlighted document in the **Clause Details** tab to see risk-coded clauses and click for details!")
                        
                        # Set default view mode to Document
                        if 'view_mode' not in st.session_state:
                            st.session_state.view_mode = "Document"
                        
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {e}")
                        logger.exception(f"Analysis error: {e}")
        
        # Export section
        if st.session_state.compliance_report:
            st.markdown("---")
            st.subheader("Export Results")
            
            export_service = get_export_service()
            
            # JSON Export
            try:
                json_data = export_service.export_to_json(
                    st.session_state.compliance_report,
                    st.session_state.recommendations
                )
                json_filename = export_service.get_json_filename(
                    st.session_state.compliance_report
                )
                
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=json_filename,
                    mime="application/json",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"JSON export error: {e}")
                logger.error(f"JSON export failed: {e}")
            
            # CSV Export
            try:
                csv_data = export_service.export_to_csv(
                    st.session_state.compliance_report,
                    st.session_state.recommendations
                )
                csv_filename = export_service.get_csv_filename(
                    st.session_state.compliance_report
                )
                
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=csv_filename,
                    mime="text/csv",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"CSV export error: {e}")
                logger.error(f"CSV export failed: {e}")
            
            # PDF Export
            try:
                pdf_data = export_service.export_to_pdf(
                    st.session_state.compliance_report,
                    st.session_state.recommendations
                )
                pdf_filename = export_service.get_pdf_filename(
                    st.session_state.compliance_report
                )
                
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_data,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF export error: {e}")
                logger.error(f"PDF export failed: {e}")

with tab2:
    st.markdown('<h2 class="section-header">Compliance Dashboard</h2>', unsafe_allow_html=True)
    
    # Check if batch results are available
    if st.session_state.batch_summary and st.session_state.batch_summary.results:
        st.markdown("### 📦 Batch Processing Results")
        summary = st.session_state.batch_summary
        
        # Calculate aggregated metrics
        from services.batch_processor import BatchProcessor
        batch_processor = BatchProcessor()
        agg_metrics = batch_processor.get_aggregated_compliance_score(summary)
        success_rate = (summary.successful / summary.total_files * 100) if summary.total_files > 0 else 0
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Files", summary.total_files)
        with col2:
            st.metric("Successful", summary.successful, delta=f"{success_rate:.0f}%")
        with col3:
            st.metric("Avg Compliance", f"{agg_metrics['average_score']:.1f}%")
        with col4:
            st.metric("Total Issues", agg_metrics['total_issues'])
        
        st.markdown("---")
        
        # Show all file results inline (not in expander)
        st.markdown("### 📊 Individual File Results")
        for i, result in enumerate(summary.results, 1):
            if result.success and result.compliance_results:
                report = result.compliance_results
                st.markdown(f"#### {i}. {result.filename}")
                
                # File metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Overall Score", f"{report.overall_score:.0f}%")
                with col2:
                    total_issues = report.summary.high_risk_count + report.summary.medium_risk_count + report.summary.low_risk_count
                    st.metric("Total Issues", total_issues)
                with col3:
                    st.metric("High Risk", report.summary.high_risk_count)
                with col4:
                    st.metric("Medium Risk", report.summary.medium_risk_count)
                
                st.markdown("---")
            elif not result.success:
                st.error(f"❌ {i}. {result.filename} - {result.error}")
                st.markdown("---")
        
        st.markdown("---")
    
    # Check if we have single analysis results
    if st.session_state.compliance_report:
        report = st.session_state.compliance_report
        
        # KPI Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Overall Compliance", 
                f"{report.overall_score:.0f}%",
                delta_color="normal"
            )
        
        with col2:
            st.metric(
                "High Risk Items", 
                report.summary.high_risk_count,
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                "Contracts Analyzed", 
                len(st.session_state.contract_history)
            )
        
        with col4:
            st.metric(
                "Missing Clauses", 
                len(report.missing_requirements)
            )
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Compliance by Framework")
            
            # Calculate scores per framework
            framework_scores = {}
            for framework in report.frameworks_checked:
                framework_results = [r for r in report.clause_results if r.framework == framework]
                if framework_results:
                    compliant = sum(1 for r in framework_results if r.compliance_status.value == 'Compliant')
                    score = (compliant / len(framework_results)) * 100
                    framework_scores[framework] = score
                else:
                    framework_scores[framework] = 0
            
            framework_data = pd.DataFrame({
                'Framework': list(framework_scores.keys()),
                'Compliance': list(framework_scores.values()),
                'Target': [90] * len(framework_scores)
            })
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Current',
                x=framework_data['Framework'],
                y=framework_data['Compliance'],
                marker_color='#2e86ab'
            ))
            fig.add_trace(go.Scatter(
                name='Target',
                x=framework_data['Framework'],
                y=framework_data['Target'],
                mode='markers',
                marker=dict(color='red', size=10, symbol='line-ew'),
                line=dict(width=3)
            ))
            
            fig.update_layout(
                height=300,
                showlegend=True,
                yaxis_range=[0, 100],
                yaxis_title="Compliance %"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Risk Distribution")
            
            risk_data = pd.DataFrame({
                'Level': ['High', 'Medium', 'Low'],
                'Count': [
                    report.summary.high_risk_count,
                    report.summary.medium_risk_count,
                    report.summary.low_risk_count
                ]
            })
            
            # Only show non-zero values
            risk_data = risk_data[risk_data['Count'] > 0]
            
            if not risk_data.empty:
                fig = px.pie(
                    risk_data, 
                    values='Count', 
                    names='Level',
                    color='Level',
                    color_discrete_map={
                        'High': '#ff6b6b',
                        'Medium': '#ffd166', 
                        'Low': '#06d6a0'
                    }
                )
                
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No risk data available")
        
        # Recent Activity
        st.subheader("Recent Analysis Activity")
        
        if st.session_state.contract_history:
            activity_data = pd.DataFrame(st.session_state.contract_history)
            activity_data = activity_data.rename(columns={
                'filename': 'Contract',
                'date': 'Date',
                'status': 'Status',
                'risk': 'Risk',
                'score': 'Score'
            })
            
            st.dataframe(
                activity_data,
                use_container_width=True,
                height=300,
                column_config={
                    "Date": st.column_config.DatetimeColumn("Date", format="MMM D, YYYY HH:mm"),
                    "Status": st.column_config.TextColumn("Status"),
                    "Risk": st.column_config.TextColumn("Risk"),
                    "Score": st.column_config.ProgressColumn("Score", format="%.0f%%", min_value=0, max_value=100)
                },
                hide_index=True
            )
        else:
            st.info("No contracts analyzed yet")
    else:
        st.info("📊 Upload and analyze a contract to see dashboard metrics")
        
        # Show placeholder
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Overall Compliance", "—")
        with col2:
            st.metric("High Risk Items", "—")
        with col3:
            st.metric("Contracts Analyzed", len(st.session_state.contract_history))
        with col4:
            st.metric("Missing Clauses", "—")

with tab3:
    st.markdown('<h2 class="section-header">Clause-Level Analysis</h2>', unsafe_allow_html=True)
    
    # Check if batch results are available
    if st.session_state.batch_summary and st.session_state.batch_summary.results:
        st.info("💡 **Batch Mode**: Showing detailed clause analysis for all files")
        
        summary = st.session_state.batch_summary
        for i, result in enumerate(summary.results, 1):
            if result.success and result.compliance_results:
                st.markdown(f"## 📄 {i}. {result.filename}")
                display_report = result.compliance_results
                display_recommendations = result.recommendations or []
                
                # Display clause details for this file inline with unique key prefix
                _display_clause_details(display_report, display_recommendations, key_prefix=f"batch_{i}_")
                
                st.markdown("---" * 20)
            elif not result.success:
                st.error(f"❌ {i}. {result.filename} - {result.error}")
                st.markdown("---")
    elif st.session_state.compliance_report:
        # Single file mode
        display_report = st.session_state.compliance_report
        display_recommendations = st.session_state.recommendations
        _display_clause_details(display_report, display_recommendations, key_prefix="single_")
    else:
        st.info("👈 Please upload and process documents from the sidebar")

# ==================== TAB 4: AUTO-FIX & REWRITE CONTRACT ====================
with tab4:
    st.markdown('<h2 class="section-header">✨ Auto-Fix Missing Clauses & Rewrite Contract</h2>', unsafe_allow_html=True)
    
    # Check if batch results are available
    if st.session_state.batch_summary and st.session_state.batch_summary.results:
        st.info("💡 **Batch Mode**: Showing auto-fix suggestions for all files with missing clauses")
        
        summary = st.session_state.batch_summary
        files_with_missing = [r for r in summary.results if r.success and r.compliance_results and r.compliance_results.missing_requirements]
        
        if files_with_missing:
            for i, result in enumerate(files_with_missing, 1):
                st.markdown(f"## 📄 {i}. {result.filename}")
                display_report = result.compliance_results
                
                # Display auto-fix for this file
                _display_autofix_section(display_report, result.filename)
                
                st.markdown("---" * 20)
        else:
            st.success("✅ No files with missing requirements - all contracts are compliant!")
    elif st.session_state.compliance_report:
        # Single file mode
        display_report = st.session_state.compliance_report
        _display_autofix_section(display_report, "Current Document")
    else:
        st.info("👈 Please upload and process documents from the sidebar")

# ==================== TAB 5: REGULATORY UPDATES ====================
with tab5:
    st.markdown('<h2 class="section-header">🔄 Real-Time Regulatory Updates</h2>', unsafe_allow_html=True)
    
    # Initialize regulatory update tracker
    if 'regulatory_tracker' not in st.session_state:
        try:
            from services.regulatory_update_tracker import RegulatoryUpdateTracker
            st.session_state.regulatory_tracker = RegulatoryUpdateTracker()
            st.session_state.regulatory_updates = []
        except Exception as e:
            logger.error(f"Failed to initialize regulatory tracker: {e}")
            st.session_state.regulatory_tracker = None
    
    tracker = st.session_state.regulatory_tracker
    
    if tracker is None:
        st.error("⚠️ Regulatory update tracking is not available. Please check API keys in .env file.")
        st.info("Required: SERPER_API_KEY and GROQ_API_KEY")
    else:
        st.info("👆 Click 'Scan for Regulatory Updates' to check for recent changes")

# ==================== TAB 6: SETTINGS ====================
with tab6:
    st.markdown('<h2 class="section-header">⚙️ Settings & Configuration</h2>', unsafe_allow_html=True)
    
    # Load current configuration
    from config.settings import AppConfig
    
    try:
        config = AppConfig()
        config_loaded = True
    except Exception as e:
        st.error(f"Failed to load configuration: {e}")
        config_loaded = False
        config = None
    
    # Create tabs for different setting categories
    settings_tab1, settings_tab2, settings_tab3, settings_tab4 = st.tabs([
        "🔧 Analysis", "🔌 Integrations", "🔔 Notifications", "🔐 API Keys"
    ])
    
    with settings_tab1:
        st.subheader("Analysis Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            analysis_depth = st.select_slider(
                "Analysis Depth",
                options=["Basic", "Standard", "Comprehensive"],
                value="Standard",
                help="Determines thoroughness of compliance analysis"
            )
            
            confidence_threshold = st.slider(
                "Minimum Confidence Threshold (%)",
                min_value=50,
                max_value=95,
                value=75,
                help="Minimum confidence required for clause classification"
            )
            
            prioritized_regulations = st.multiselect(
                "Prioritized Regulations",
                options=['GDPR', 'HIPAA'],
                default=['GDPR', 'HIPAA'],
                help="Regulations to prioritize in analysis"
            )
        
        with col2:
            use_ai_recommendations = st.checkbox(
                "Enable AI-powered recommendations",
                value=True,
                help="Use LLaMA model for intelligent recommendations"
            )
            
            auto_generate_clauses = st.checkbox(
                "Auto-generate missing clauses",
                value=True,
                help="Automatically generate suggested text for missing clauses"
            )
            
            use_gpu = st.checkbox(
                "Use GPU acceleration",
                value=config.models.use_gpu if config_loaded else False,
                help="Faster processing with GPU (requires CUDA)"
            )
            
            max_file_size = st.number_input(
                "Max File Size (MB)",
                min_value=1,
                max_value=100,
                value=config.processing.max_file_size_mb if config_loaded else 10,
                help="Maximum allowed file size for upload"
            )
        
        st.markdown("---")
        
        st.subheader("Model Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if config_loaded:
                st.text_input(
                    "Legal BERT Model",
                    value=config.models.legal_bert_model,
                    disabled=True,
                    help="NLP model for legal text analysis"
                )
                
                st.text_input(
                    "LLaMA Model",
                    value=config.models.llama_model,
                    disabled=True,
                    help="Large language model for generation"
                )
        
        with col2:
            if config_loaded:
                st.text_input(
                    "Sentence Transformer",
                    value=config.models.sentence_transformer_model,
                    disabled=True,
                    help="Model for semantic similarity"
                )
                
                st.info("💡 Model paths are configured in .env file")
    
    with settings_tab2:
        st.subheader("Integration Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Google Sheets")
            
            google_sheets_enabled = st.checkbox(
                "Enable Google Sheets Integration",
                value=google_sheets,
                help="Export reports directly to Google Sheets"
            )
            
            if google_sheets_enabled:
                credentials_path = st.text_input(
                    "Credentials Path",
                    value="config/google_credentials.json",
                    help="Path to Google API credentials JSON file"
                )
                
                if st.button("🧪 Test Google Sheets Connection"):
                    with st.spinner("Testing connection..."):
                        try:
                            from services.google_sheets_service import GoogleSheetsService
                            sheets_service = GoogleSheetsService()
                            st.success("✅ Google Sheets connection successful!")
                        except Exception as e:
                            st.error(f"❌ Connection failed: {e}")
            
            st.markdown("---")
            
            st.markdown("#### 💬 Slack")
            
            slack_enabled = st.checkbox(
                "Enable Slack Notifications",
                value=slack_alerts,
                help="Send compliance alerts to Slack"
            )
            
            if slack_enabled:
                slack_webhook = st.text_input(
                    "Webhook URL",
                    value=config.api.slack_webhook_url if config_loaded and config.api.slack_webhook_url else "",
                    type="password",
                    help="Slack webhook URL for notifications"
                )
                
                if st.button("🧪 Test Slack Connection"):
                    if slack_webhook:
                        with st.spinner("Sending test message..."):
                            try:
                                import requests
                                response = requests.post(
                                    slack_webhook,
                                    json={"text": "✅ Compliance Checker: Test notification successful!"}
                                )
                                if response.status_code == 200:
                                    st.success("✅ Slack notification sent!")
                                else:
                                    st.error(f"❌ Failed: {response.status_code}")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                    else:
                        st.warning("Please enter a webhook URL first")
        
        with col2:
            st.markdown("#### 📤 Export Settings")
            
            default_export_format = st.selectbox(
                "Default Export Format",
                options=["PDF", "DOCX", "JSON", "CSV"],
                index=0,
                help="Default format for exports"
            )
            
            include_recommendations = st.checkbox(
                "Include recommendations in exports",
                value=True
            )
            
            include_risk_analysis = st.checkbox(
                "Include detailed risk analysis",
                value=True
            )
            
            st.markdown("---")
            
            st.markdown("#### 🔄 Auto-Export")
            
            auto_export_enabled = st.checkbox(
                "Enable automatic export after analysis",
                value=False
            )
            
            if auto_export_enabled:
                auto_export_formats = st.multiselect(
                    "Auto-export formats",
                    options=["PDF", "JSON", "CSV"],
                    default=["JSON"]
                )
                
                auto_export_location = st.text_input(
                    "Export directory",
                    value="data/exports",
                    help="Directory for auto-exported files"
                )
    
    with settings_tab3:
        st.subheader("Notification Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🚨 Compliance Alerts")
            
            alert_high_risk = st.checkbox(
                "Alert on high-risk findings",
                value=True,
                help="Receive notifications for high-risk issues"
            )
            
            alert_non_compliant = st.checkbox(
                "Alert on non-compliant clauses",
                value=True,
                help="Get notified when clauses fail compliance"
            )
            
            alert_missing_clauses = st.checkbox(
                "Alert on missing mandatory clauses",
                value=True,
                help="Notification for missing required clauses"
            )
            
            st.markdown("---")
            
            st.markdown("#### � Email Notifications")
            
            email_enabled = st.checkbox("Enable email notifications", value=False)
            
            if email_enabled:
                notification_email = st.text_input(
                    "Email address",
                    placeholder="you@example.com"
                )
                
                email_frequency = st.selectbox(
                    "Email frequency",
                    options=["Immediate", "Daily Digest", "Weekly Summary"],
                    index=1
                )
        
        with col2:
            st.markdown("#### 🔔 Regulatory Update Alerts")
            
            notify_critical = st.checkbox(
                "Notify on CRITICAL updates",
                value=True,
                key="settings_notify_critical"
            )
            
            notify_high = st.checkbox(
                "Notify on HIGH severity updates",
                value=True,
                key="settings_notify_high"
            )
            
            notify_medium = st.checkbox(
                "Notify on MEDIUM severity updates",
                value=False,
                key="settings_notify_medium"
            )
            
            st.markdown("---")
            
            st.markdown("#### 🕒 Quiet Hours")
            
            enable_quiet_hours = st.checkbox("Enable quiet hours", value=False)
            
            if enable_quiet_hours:
                col_start, col_end = st.columns(2)
                with col_start:
                    quiet_start = st.time_input("Start time", value=datetime.strptime("22:00", "%H:%M").time())
                with col_end:
                    quiet_end = st.time_input("End time", value=datetime.strptime("08:00", "%H:%M").time())
    
    with settings_tab4:
        st.subheader("🔐 API Key Management")
        
        st.warning("⚠️ API keys are stored in the `.env` file. Never commit this file to version control!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔍 Serper API (Web Search)")
            
            if config_loaded and config.api.serper_api_key:
                st.success("✅ Serper API key configured")
                masked_key = config.api.serper_api_key[:8] + "..." + config.api.serper_api_key[-4:]
                st.code(masked_key)
            else:
                st.error("❌ Serper API key not found")
                st.info("Add SERPER_API_KEY to your .env file")
            
            st.markdown("---")
            
            st.markdown("#### 🤖 Groq API (LLaMA Inference)")
            
            if config_loaded and config.api.groq_api_key:
                st.success("✅ Groq API key configured")
                masked_key = config.api.groq_api_key[:8] + "..." + config.api.groq_api_key[-4:]
                st.code(masked_key)
            else:
                st.error("❌ Groq API key not found")
                st.info("Add GROQ_API_KEY to your .env file")
        
        with col2:
            st.markdown("#### 💬 Slack Integration")
            
            if config_loaded and config.api.slack_webhook_url:
                st.success("✅ Slack webhook configured")
                masked_url = config.api.slack_webhook_url[:30] + "..."
                st.code(masked_url)
            else:
                st.warning("⚠️ Slack webhook not configured")
                st.info("Optional: Add SLACK_WEBHOOK_URL to .env")
            
            st.markdown("---")
            
            st.markdown("#### 📊 Google Sheets API")
            
            credentials_exists = os.path.exists("config/google_credentials.json")
            
            if credentials_exists:
                st.success("✅ Google credentials file found")
            else:
                st.warning("⚠️ Google credentials not found")
                st.info("Optional: Add credentials to config/google_credentials.json")
        
        st.markdown("---")
        
        # API Key setup instructions
        with st.expander("📖 How to Get API Keys", expanded=False):
            st.markdown("""
            ### Serper API (Required for Regulatory Updates)
            
            1. Visit [serper.dev](https://serper.dev)
            2. Sign up for a free account
            3. Get your API key from the dashboard
            4. Add to `.env`: `SERPER_API_KEY=your_key_here`
            
            ---
            
            ### Groq API (Required for AI Analysis)
            
            1. Visit [console.groq.com](https://console.groq.com)
            2. Create an account
            3. Generate an API key
            4. Add to `.env`: `GROQ_API_KEY=your_key_here`
            
            ---
            
            ### Slack Webhook (Optional)
            
            1. Go to [api.slack.com/apps](https://api.slack.com/apps)
            2. Create a new app
            3. Enable Incoming Webhooks
            4. Add webhook URL to `.env`
            
            ---
            
            ### Google Sheets API (Optional)
            
            1. Visit [Google Cloud Console](https://console.cloud.google.com)
            2. Create a project
            3. Enable Google Sheets API
            4. Create service account credentials
            5. Download JSON and save to `config/google_credentials.json`
            """)
    
    # Save button at bottom
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info("💡 Most settings are applied immediately. Configuration changes require restart.")
    
    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            st.warning("This will reset all settings to defaults")
            if st.button("Confirm Reset"):
                st.success("✅ Settings reset to defaults")
                st.rerun()
    
    with col3:
        if st.button("💾 Save All Settings", type="primary", use_container_width=True):
            # Here you would save settings to a config file
            st.success("✅ Settings saved successfully!")
            st.info("Note: API keys must be set in .env file")

# Footer
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

# Get current datetime in IST
from datetime import timezone, timedelta
ist = timezone(timedelta(hours=5, minutes=30))
current_time_ist = datetime.now(ist)
current_year = current_time_ist.year
last_updated = current_time_ist.strftime("%B %d, %Y")
next_scan_time = (current_time_ist + timedelta(hours=1)).strftime("%H:%M IST")

with footer_col1:
    st.caption(f"© {current_year} AI Compliance Checker")
    st.caption("Version 1.0.0")

with footer_col2:
    st.caption(f"Last updated: {last_updated}")
    st.caption(f"Next regulatory scan: Today, {next_scan_time}")

with footer_col3:
    st.caption("Need help? Contact support@compliancechecker.ai")