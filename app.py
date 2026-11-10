import streamlit as st
import json
import os
import re
import requests
import base64
from typing import Dict, Any, List, Tuple

# ---------------------------------------------------------
# Page Setup & Modern App Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Enterprise QA Engine & Azure Ingestion",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Main App Card containers */
    .app-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Status banner tags */
    .metric-pill {
        display: inline-flex;
        align-items: center;
        background: #f1f5f9;
        color: #334155;
        font-size: 13px;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
        border: 1px solid #cbd5e1;
        margin-right: 8px;
    }
    
    .learning-box-new {
        background: #f0fdf4;
        border: 1px solid #86efac;
        color: #166534;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 14px 0;
        font-size: 14px;
    }
    
    .learning-box-stable {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #64748b;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 14px 0;
        font-size: 13px;
        font-style: italic;
    }
    
    .code-display {
        background-color: #0f172a;
        color: #e2e8f0;
        padding: 14px;
        border-radius: 8px;
        font-family: 'Fira Code', monospace;
        font-size: 12px;
        max-height: 250px;
        overflow-y: auto;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px 8px 0 0;
        padding-left: 18px;
        padding-right: 18px;
    }
</style>
""", unsafe_allow_html=True)

MEMORY_FILE = "projects_memory.json"

# ---------------------------------------------------------
# Memory Persistence Engine
# ---------------------------------------------------------
def load_memories() -> Dict[str, Any]:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "TB Direct": {
            "summary": "Enterprise architecture and QA workspace for TB Direct / Trublu Dental.",
            "invariants": [
                "Macroscopic big-picture view: omit trivial micro-interaction click steps.",
                "Strict RBAC validation: isolate permissions across administrative and standard roles.",
                "Impersonation sessions must cleanly terminate and restore Super Admin context without leaked tokens."
            ],
            "personas": ["Super Admin", "Practice Admin", "Standard User"],
            "learned_search_knowledge": []
        },
        "Default SaaS Project": {
            "summary": "Standard SaaS tenant architecture.",
            "invariants": ["Tenant isolation must be enforced."],
            "personas": ["Super Admin", "Standard User"],
            "learned_search_knowledge": []
        }
    }

def save_memories(data: Dict[str, Any]):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

if "memories" not in st.session_state:
    st.session_state.memories = load_memories()
if "last_learning_delta" not in st.session_state:
    st.session_state.last_learning_delta = None

# ---------------------------------------------------------
# Security / Auth Gatekeeper
# ---------------------------------------------------------
expected_pwd = None
if hasattr(st, "secrets") and "APP_PASSWORD" in st.secrets:
    expected_pwd = st.secrets["APP_PASSWORD"]
if not expected_pwd:
    expected_pwd = os.getenv("APP_PASSWORD", "Login@123$")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("### 🔒 Enterprise QA Engine Access")
    st.write("Authorized enterprise access only. Multi-project memory & visual intelligence.")
    pwd_input = st.text_input("Enter Access Key", type="password")
    if st.button("Authenticate", type="primary"):
        if pwd_input == expected_pwd:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Access Denied: Invalid credentials.")
    st.stop()

# ---------------------------------------------------------
# Azure DevOps Helpers
# ---------------------------------------------------------
def get_azure_credentials() -> Tuple[str, str]:
    org = ""
    pat = ""
    if hasattr(st, "secrets"):
        org = st.secrets.get("AZURE_ORG", "")
        pat = st.secrets.get("AZURE_PAT", "")
    return org, pat

def fetch_azure_projects(org: str, pat: str) -> List[str]:
    clean_org = org.replace("https://dev.azure.com/", "").strip("/")
    url = f"https://dev.azure.com/{clean_org}/_apis/projects?api-version=7.1-preview.4"
    auth = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return [p["name"] for p in resp.json().get("value", [])]
    except Exception:
        pass
    return []

def publish_work_item(org: str, pat: str, project: str, wit_type: str, title: str, description_html: str, tcm_xml: str = "") -> Tuple[bool, str]:
    clean_org = org.replace("https://dev.azure.com/", "").strip("/")
    url = f"https://dev.azure.com/{clean_org}/{requests.utils.quote(project)}/_apis/wit/workitems/${requests.utils.quote(wit_type)}?api-version=7.1"
    auth = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json-patch+json"}
    
    patch_doc = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description_html}
    ]
    if wit_type == "Test Case" and tcm_xml:
        patch_doc.append({"op": "add", "path": "/fields/Microsoft.VSTS.TCM.Steps", "value": tcm_xml})
        
    try:
        resp = requests.post(url, headers=headers, json=patch_doc, timeout=15)
        if resp.status_code in [200, 201]:
            item_id = resp.json().get("id")
            web_link = f"https://dev.azure.com/{clean_org}/{requests.utils.quote(project)}/_workitems/edit/{item_id}"
            return True, f"Success! Created {wit_type} #{item_id}. [Open in Azure DevOps]({web_link})"
        else:
            return False, f"Failed ({resp.status_code}): {resp.text}"
    except Exception as e:
        return False, f"Request error: {str(e)}"

# ---------------------------------------------------------
# TCM Steps XML Parser
# ---------------------------------------------------------
def convert_to_tcm_xml(steps: List[Dict[str, str]]) -> str:
    if not steps:
        return ""
    xml = f'<steps id="0" last="{len(steps) + 1}">'
    for idx, s in enumerate(steps, start=2):
        action_escaped = s["action"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        expected_escaped = s["expected"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        xml += (
            f'<step id="{idx}" type="ValidateStep">'
            f'<parameterizedString isformatted="true">&lt;DIV&gt;&lt;P&gt;{action_escaped}&lt;/P&gt;&lt;/DIV&gt;</parameterizedString>'
            f'<parameterizedString isformatted="true">&lt;DIV&gt;&lt;P&gt;{expected_escaped}&lt;/P&gt;&lt;/DIV&gt;</parameterizedString>'
            f'<description/></step>'
        )
    xml += "</steps>"
    return xml

def extract_steps_and_learn(raw_text: str, current_proj: str, current_persona: str) -> Tuple[str, List[Dict[str, str]], List[str]]:
    lines = [l.strip() for l in raw_text.strip().split("\n") if l.strip()]
    title = f"Scenario - {current_proj}"
    steps = []
    new_invariants = []
    
    for l in lines:
        if re.match(r"^(title:|# |\*\*title\*\*:?)", l, re.IGNORECASE):
            title = re.sub(r"^(title:|#+|\*\*title\*\*:?)\s*", "", l, flags=re.IGNORECASE).strip()
        elif not re.match(r"^(step\s*#|step,)", l, re.IGNORECASE):
            parts = re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", l)
            if len(parts) >= 3:
                act = parts[1].strip('"').strip()
                exp = parts[2].strip('"').strip()
                steps.append({"action": act, "expected": exp})
            elif len(parts) == 2:
                act = parts[0].strip('"').strip()
                exp = parts[1].strip('"').strip()
                steps.append({"action": act, "expected": exp})
                
        # Heuristic invariant detection
        if any(keyword in l.lower() for keyword in ["must", "ensure", "shall", "cannot", "isolate"]):
            clean_rule = l.strip("-* 0123456789.,\"")
            if len(clean_rule) > 18:
                new_invariants.append(clean_rule)
                
    # Persist detected invariants into memory
    target_mem = st.session_state.memories.get(current_proj, {"invariants": [], "personas": []})
    existing = set(target_mem.get("invariants", []))
    added = [inv for inv in new_invariants if inv not in existing]
    
    if added:
        target_mem["invariants"] = list(dict.fromkeys(target_mem.get("invariants", []) + added))
        st.session_state.memories[current_proj] = target_mem
        save_memories(st.session_state.memories)
        
    return title, steps, added

# ---------------------------------------------------------
# Sidebar Configuration
# ---------------------------------------------------------
default_org, default_pat = get_azure_credentials()
st.sidebar.markdown("### ☁️ Azure DevOps REST")
azure_org = st.sidebar.text_input("Azure Org Name", value=default_org, placeholder="TrubluDental")
azure_pat = st.sidebar.text_input("Personal Access Token (PAT)", value=default_pat, type="password")

if "azure_projects" not in st.session_state:
    st.session_state.azure_projects = []

if st.sidebar.button("🔄 Connect & Fetch Projects", use_container_width=True):
    if azure_org and azure_pat:
        with st.spinner("Authenticating with Azure..."):
            projects = fetch_azure_projects(azure_org, azure_pat)
            if projects:
                st.session_state.azure_projects = projects
                st.sidebar.success(f"Connected! {len(projects)} projects found.")
            else:
                st.sidebar.error("Could not fetch projects. Check Org/PAT.")
    else:
        st.sidebar.warning("Enter both Org Name and PAT.")

selected_azure_project = None
if st.session_state.azure_projects:
    selected_azure_project = st.sidebar.selectbox("Active Azure Project", options=st.session_state.azure_projects)
else:
    st.sidebar.info("Fetch projects to enable direct publishing.")

# ---------------------------------------------------------
# Top Bar: Profile & Persona Control Hub
# ---------------------------------------------------------
st.markdown("## ⚡ Enterprise QA Workbench")

col_prof, col_persona = st.columns([1, 1])

# 1. Project Profile Selector
with col_prof:
    st.markdown("**📁 Project Memory Profile**")
    proj_keys = list(st.session_state.memories.keys())
    proj_options = proj_keys + ["➕ [Add New Project]"]
    active_proj_selection = st.selectbox("Project Profile", options=proj_options, label_visibility="collapsed")
    
    if active_proj_selection == "➕ [Add New Project]":
        new_proj_name = st.text_input("Name for new project workspace:", placeholder="e.g., DentalPortal")
        if st.button("Create Project Profile", type="primary"):
            if new_proj_name and new_proj_name not in st.session_state.memories:
                st.session_state.memories[new_proj_name] = {
                    "summary": f"Workspace for {new_proj_name}",
                    "invariants": [],
                    "personas": ["Super Admin", "Standard User"],
                    "learned_search_knowledge": []
                }
                save_memories(st.session_state.memories)
                st.rerun()
        st.stop()
    else:
        active_project = active_proj_selection

# 2. Persona Selector with Inline Creator
with col_persona:
    st.markdown("**👤 Active Execution Persona**")
    proj_data = st.session_state.memories.get(active_project, {})
    current_personas = proj_data.get("personas", ["Super Admin", "Standard User"])
    persona_options = current_personas + ["➕ [Add New Persona...]"]
    
    active_persona_selection = st.selectbox("Execution Persona", options=persona_options, label_visibility="collapsed")
    
    if active_persona_selection == "➕ [Add New Persona...]":
        new_persona_name = st.text_input("Enter new persona title:", placeholder="e.g., Regional Billing Specialist")
        if st.button("Save Persona to Project", type="primary"):
            if new_persona_name and new_persona_name not in current_personas:
                current_personas.append(new_persona_name)
                proj_data["personas"] = current_personas
                st.session_state.memories[active_project] = proj_data
                save_memories(st.session_state.memories)
                st.rerun()
        st.stop()
    else:
        active_persona = active_persona_selection

# Live Knowledge Banner
inv_count = len(proj_data.get("invariants", []))
persona_count = len(proj_data.get("personas", []))
st.markdown(f"""
<div style="margin-bottom: 16px;">
    <span class="metric-pill">📌 Active: <strong>{active_project}</strong></span>
    <span class="metric-pill">👤 Persona: <strong>{active_persona}</strong></span>
    <span class="metric-pill">🧠 {inv_count} Stored Invariants</span>
    <span class="metric-pill">👥 {persona_count} Configured Personas</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Dynamic Invariant Learning Notification Box
# ---------------------------------------------------------
if st.session_state.last_learning_delta:
    delta = st.session_state.last_learning_delta
    if delta.get("added_invariants"):
        st.markdown(f"""
        <div class="learning-box-new">
            <strong>✨ Learned {len(delta['added_invariants'])} New Rule(s) for {active_project}:</strong>
            <ul style="margin: 6px 0 0 16px;">
                {''.join(f'<li>{inv}</li>' for inv in delta['added_invariants'])}
            </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="learning-box-stable">
            ✓ Knowledge Base up to date — no new invariants detected in last scenario.
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# Workspace Tabs
# ---------------------------------------------------------
tab_ingest, tab_kb = st.tabs([
    "📋 Off-Grid Ingestor & Publisher", 
    "🧠 Project Knowledge Base"
])

# TAB 1: Ingestion & Publishing
with tab_ingest:
    col_wit, col_target = st.columns([1, 1])
    with col_wit:
        target_wit = st.selectbox(
            "Target Azure Work Item",
            ["Test Case", "Bug", "User Story", "Task", "Feature", "Epic", "Issue"]
        )
    with col_target:
        target_disp = selected_azure_project if selected_azure_project else "None selected (Set PAT in sidebar)"
        st.text_input("Destination Azure Project", value=target_disp, disabled=True)

    raw_input = st.text_area(
        "Paste Raw Gemini Text / CSV Output",
        height=170,
        placeholder="Title: Verify Practice tab completed practices\nStep #,Action,Expected Result\n1,Log in as Super Admin and open Practice view,Completed practices list displays\n2,Click column header sorting,Table updates cleanly without state reset"
    )

    if st.button("📥 Parse, Learn & Format", type="primary", use_container_width=True):
        if not raw_input.strip():
            st.warning("Please paste scenario text first.")
        else:
            parsed_title, steps, learned = extract_steps_and_learn(raw_input, active_project, active_persona)
            tcm_xml = convert_to_tcm_xml(steps)
            desc_html = f"<h3>Scope & Verification</h3><p>Scenario authored for <strong>{active_project}</strong> under role <strong>{active_persona}</strong>.</p>"
            
            st.session_state.last_learning_delta = {"added_invariants": learned}
            st.session_state.last_parsed = {
                "title": parsed_title,
                "wit": target_wit,
                "desc_html": desc_html,
                "tcm_xml": tcm_xml,
                "steps_count": len(steps)
            }
            st.rerun()

    # Publishing controls when data is parsed
    if "last_parsed" in st.session_state:
        item = st.session_state.last_parsed
        st.markdown("---")
        st.markdown(f"#### 🎯 Formatted Item: `{item['title']}`")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Field 1: Description / Scope (HTML)**")
            st.markdown(f'<div class="code-display">{item["desc_html"]}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f"**Field 2: Native Steps (TCM XML - {item['steps_count']} steps)**")
            disp_xml = item["tcm_xml"] if item["tcm_xml"] else "(No CSV steps formatted)"
            st.markdown(f'<div class="code-display">{disp_xml}</div>', unsafe_allow_html=True)

        if st.button(f"🚀 Publish Directly to Azure DevOps ({item['wit']})", type="primary", use_container_width=True):
            if not azure_org or not azure_pat or not selected_azure_project:
                st.error("Please provide Azure Org, PAT, and select an Azure Project in the sidebar first.")
            else:
                with st.spinner("Submitting REST Payload to Azure..."):
                    success, msg = publish_work_item(
                        org=azure_org,
                        pat=azure_pat,
                        project=selected_azure_project,
                        wit_type=item["wit"],
                        title=item["title"],
                        description_html=item["desc_html"],
                        tcm_xml=item["tcm_xml"]
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

# TAB 2: Knowledge Base Management
with tab_kb:
    st.markdown(f"### 🧠 Stored Knowledge for `{active_project}`")
    mem = st.session_state.memories.get(active_project, {})
    
    st.markdown(f"**Architecture Summary:** {mem.get('summary', 'Standard enterprise architecture.')}")
    
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        st.markdown("#### 👥 Registered Personas")
        for p in mem.get("personas", []):
            st.markdown(f"- **{p}**")
            
    with col_k2:
        st.markdown("#### 🛡️ Learned System Invariants")
        invariants = mem.get("invariants", [])
        if invariants:
            for inv in invariants:
                st.markdown(f"- {inv}")
        else:
            st.info("No invariants recorded yet. Ingest scenarios to automatically absorb rules.")