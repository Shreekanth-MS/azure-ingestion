import streamlit as st
import json
import os
import re
import requests
import base64
from typing import Dict, Any, List, Tuple

# ---------------------------------------------------------
# Page Setup & Modern SaaS UI Styling
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
        margin-bottom: 6px;
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
# Dynamic Memory Persistence Engine (Disk + Cloud GitHub Sync)
# ---------------------------------------------------------
def get_gh_headers() -> Dict[str, str]:
    token = ""
    if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets:
        token = st.secrets["GITHUB_TOKEN"]
    else:
        token = os.getenv("GITHUB_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def load_memories() -> Dict[str, Any]:
    repo = ""
    if hasattr(st, "secrets") and "GITHUB_REPO" in st.secrets:
        repo = st.secrets["GITHUB_REPO"]
    else:
        repo = os.getenv("GITHUB_REPO", "")

    # 1. Attempt to fetch latest memory state from GitHub repo
    if repo and (hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets or os.getenv("GITHUB_TOKEN")):
        try:
            url = f"https://api.github.com/repos/{repo}/contents/{MEMORY_FILE}"
            res = requests.get(url, headers=get_gh_headers(), timeout=5)
            if res.status_code == 200:
                raw_json = base64.b64decode(res.json()["content"]).decode("utf-8")
                return json.loads(raw_json)
        except Exception:
            pass

    # 2. Local physical file fallback
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # 3. Default fallback state
    return {
        "TB Direct": {
            "summary": "Enterprise architecture and QA workspace for TB Direct / Trublu Dental.",
            "invariants": [
                "Macroscopic big-picture view: omit trivial micro-interaction click steps.",
                "Consolidate multiple related tabs into a single unified end-to-end lifecycle scenario.",
                "Strict RBAC validation: isolate permissions across administrative and standard roles.",
                "Cross-tab state persistence: ensure upstream modifications propagate without data loss.",
                "Impersonation sessions must cleanly terminate and restore Super Admin context without leaked tokens."
            ],
            "personas": ["Super Admin", "System Admin", "Practice Admin", "Standard User"],
            "learned_search_knowledge": []
        },
        "Default SaaS Project": {
            "summary": "Initial multi-tenant SaaS architecture workspace.",
            "invariants": [
                "Tenant isolation and role-based permissions must be enforced.",
                "Cross-tab state changes must validate rollback behavior on cancel."
            ],
            "personas": ["Super Admin", "Standard User"],
            "learned_search_knowledge": []
        }
    }

def save_memories(data: Dict[str, Any]):
    # Save locally to immediate runtime disk
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

    # Push to GitHub repository in background if configured
    repo = ""
    if hasattr(st, "secrets") and "GITHUB_REPO" in st.secrets:
        repo = st.secrets["GITHUB_REPO"]
    else:
        repo = os.getenv("GITHUB_REPO", "")

    token = ""
    if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets:
        token = st.secrets["GITHUB_TOKEN"]
    else:
        token = os.getenv("GITHUB_TOKEN", "")

    if repo and token:
        try:
            url = f"https://api.github.com/repos/{repo}/contents/{MEMORY_FILE}"
            headers = get_gh_headers()
            sha = ""
            get_res = requests.get(url, headers=headers, timeout=5)
            if get_res.status_code == 200:
                sha = get_res.json().get("sha", "")

            content_b64 = base64.b64encode(json.dumps(data, indent=2).encode("utf-8")).decode("utf-8")
            payload = {
                "message": "sync: dynamic project memory update [skip ci]",
                "content": content_b64
            }
            if sha:
                payload["sha"] = sha

            requests.put(url, headers=headers, json=payload, timeout=8)
        except Exception:
            pass

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
# Azure DevOps REST Integration Helpers
# ---------------------------------------------------------
def get_azure_credentials() -> Tuple[str, str, str]:
    org = ""
    pat = ""
    gemini_key = ""
    if hasattr(st, "secrets"):
        org = st.secrets.get("AZURE_ORG", "")
        pat = st.secrets.get("AZURE_PAT", "")
        gemini_key = st.secrets.get("GEMINI_API_KEYS", "") or st.secrets.get("GEMINI_API_KEY", "")
    return org, pat, gemini_key

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
# TCM Steps XML & Heuristic Invariant Extraction
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
                
        if any(keyword in l.lower() for keyword in ["must", "ensure", "shall", "cannot", "isolate"]):
            clean_rule = l.strip("-* 0123456789.,\"")
            if len(clean_rule) > 18:
                new_invariants.append(clean_rule)
                
    target_mem = st.session_state.memories.get(current_proj, {"invariants": [], "personas": [], "learned_search_knowledge": []})
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
default_org, default_pat, default_gemini = get_azure_credentials()
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

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 Model Engine")
gemini_key_input = st.sidebar.text_input("Gemini API Key", value=default_gemini, type="password")

# ---------------------------------------------------------
# Top Bar: Profile & Dynamic Persona Control Hub
# ---------------------------------------------------------
st.markdown("## ⚡ Enterprise QA Workbench")

col_prof, col_persona = st.columns([1, 1])

# 1. Dynamic Project Profile Selector
with col_prof:
    st.markdown("**📁 Local Learning Memory Profile**")
    proj_keys = list(st.session_state.memories.keys())
    proj_options = proj_keys + ["➕ [Add New Project]"]
    active_proj_selection = st.selectbox("Project Profile", options=proj_options, label_visibility="collapsed")
    
    if active_proj_selection == "➕ [Add New Project]":
        new_proj_name = st.text_input("Enter new project workspace name:", placeholder="e.g., DentalPortal")
        if st.button("Create Project Profile", type="primary"):
            if new_proj_name.strip() and new_proj_name.strip() not in st.session_state.memories:
                st.session_state.memories[new_proj_name.strip()] = {
                    "summary": f"Workspace for {new_proj_name.strip()}",
                    "invariants": [],
                    "personas": ["Super Admin", "Standard User"],
                    "learned_search_knowledge": []
                }
                save_memories(st.session_state.memories)
                st.rerun()
        st.stop()
    else:
        active_project = active_proj_selection

# 2. Dynamic Persona Selector with Inline Edit/Delete
with col_persona:
    st.markdown("**👤 Active Execution Persona**")
    proj_data = st.session_state.memories.get(active_project, {})
    current_personas = proj_data.get("personas", ["Super Admin", "Standard User"])
    
    action_options = ["➕ [Add New Persona...]", "✏️ [Edit Active Persona...]", "🗑️ [Delete Active Persona]"]
    persona_options = current_personas + action_options
    
    default_idx = 0
    if "selected_persona_name" in st.session_state and st.session_state.selected_persona_name in current_personas:
        default_idx = current_personas.index(st.session_state.selected_persona_name)

    active_persona_selection = st.selectbox(
        "Execution Persona", 
        options=persona_options, 
        index=default_idx,
        label_visibility="collapsed"
    )
    
    # Action A: Add New Persona
    if active_persona_selection == "➕ [Add New Persona...]":
        new_persona_name = st.text_input("Enter new persona title:", placeholder="e.g., Regional Billing Specialist")
        if st.button("Save Persona to Project", type="primary"):
            if new_persona_name.strip() and new_persona_name.strip() not in current_personas:
                current_personas.append(new_persona_name.strip())
                proj_data["personas"] = current_personas
                st.session_state.memories[active_project] = proj_data
                st.session_state.selected_persona_name = new_persona_name.strip()
                save_memories(st.session_state.memories)
                st.rerun()
        st.stop()

    # Action B: Edit Active Persona
    elif active_persona_selection == "✏️ [Edit Active Persona...]":
        target_to_edit = st.session_state.get("selected_persona_name", current_personas[0] if current_personas else "")
        edited_name = st.text_input(f"Rename persona '{target_to_edit}':", value=target_to_edit)
        col_save_e, col_cancel_e = st.columns([1, 1])
        with col_save_e:
            if st.button("Update Persona Name", type="primary"):
                if edited_name.strip() and edited_name.strip() != target_to_edit:
                    idx = current_personas.index(target_to_edit)
                    current_personas[idx] = edited_name.strip()
                    proj_data["personas"] = current_personas
                    st.session_state.memories[active_project] = proj_data
                    st.session_state.selected_persona_name = edited_name.strip()
                    save_memories(st.session_state.memories)
                    st.rerun()
        with col_cancel_e:
            if st.button("Cancel"):
                st.rerun()
        st.stop()

    # Action C: Delete Active Persona
    elif active_persona_selection == "🗑️ [Delete Active Persona]":
        target_to_delete = st.session_state.get("selected_persona_name", current_personas[0] if current_personas else "")
        if len(current_personas) <= 1:
            st.error("Cannot delete the only persona in this project.")
            if st.button("Go Back"):
                st.rerun()
        else:
            st.warning(f"Are you sure you want to delete persona **'{target_to_delete}'**?")
            col_del_c, col_del_cancel = st.columns([1, 1])
            with col_del_c:
                if st.button("Yes, Confirm Delete", type="primary"):
                    current_personas.remove(target_to_delete)
                    proj_data["personas"] = current_personas
                    st.session_state.memories[active_project] = proj_data
                    st.session_state.selected_persona_name = current_personas[0]
                    save_memories(st.session_state.memories)
                    st.rerun()
            with col_del_cancel:
                if st.button("Cancel"):
                    st.rerun()
        st.stop()

    else:
        active_persona = active_persona_selection
        st.session_state.selected_persona_name = active_persona

# Visual Metric Badge Bar
inv_count = len(proj_data.get("invariants", []))
persona_count = len(proj_data.get("personas", []))
search_count = len(proj_data.get("learned_search_knowledge", []))
st.markdown(f"""
<div style="margin-bottom: 16px;">
    <span class="metric-pill">📌 Active: <strong>{active_project}</strong></span>
    <span class="metric-pill">👤 Persona: <strong>{active_persona}</strong></span>
    <span class="metric-pill">🧠 {inv_count} Stored Invariants</span>
    <span class="metric-pill">👥 {persona_count} Personas</span>
    <span class="metric-pill">🌐 {search_count} Search Learnings</span>
</div>
""", unsafe_allow_html=True)

# Learning Delta Notification Box
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
# Workspace Core Tabs
# ---------------------------------------------------------
tab_ingest, tab_gen, tab_kb, tab_boundary = st.tabs([
    "📋 Off-Grid Paste Ingestor & Azure Publisher", 
    "🚀 Full Ticket Generator & Analysis", 
    "🧠 Project Knowledge Base",
    "⚙️ Boundary Conditions"
])

# ---------------------------------------------------------
# TAB 1: Off-Grid Paste Ingestor & Publisher
# ---------------------------------------------------------
with tab_ingest:
    st.markdown("### Direct Gemini Web Ingestion & Azure DevOps Publisher")
    st.caption("Paste any raw scenario or test case generated in your chat. The brain absorbs rules into local memory, renders Azure-ready HTML, and pushes directly to Azure DevOps.")

    col_wit, col_target = st.columns([1, 1])
    with col_wit:
        target_wit = st.selectbox(
            "Target Azure Work Item",
            ["Test Case", "Bug", "User Story", "Task", "Feature", "Epic", "Issue"],
            key="ingest_wit"
        )
    with col_target:
        target_disp = selected_azure_project if selected_azure_project else "None selected (Configure PAT in sidebar)"
        st.text_input("Target Azure Project", value=target_disp, disabled=True, key="ingest_disp")

    raw_input = st.text_area(
        "Paste Raw Gemini Text / JSON Output Here",
        height=180,
        placeholder="Paste response text or JSON directly from your Gemini web conversation...",
        key="ingest_raw"
    )

    if st.button("📥 Parse, Learn & Format", type="primary", use_container_width=True, key="btn_parse_ingest"):
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

        if st.button(f"🚀 Publish Directly to Azure DevOps ({item['wit']})", type="primary", use_container_width=True, key="btn_publish_ingest"):
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

# ---------------------------------------------------------
# TAB 2: Full Ticket Generator & Live Search Grounding
# ---------------------------------------------------------
with tab_gen:
    st.markdown("### Generative Ticket Authoring & Search Grounding")
    st.caption("Generate complete work items grounded with real-time web intelligence and learned project memory.")

    col_req, col_gen_ctrl = st.columns([2, 1])
    with col_req:
        gen_prompt = st.text_area(
            "Feature / Requirement / Defect Context",
            height=120,
            placeholder=f"e.g., In {active_project}, generate integration test case for administrative checkout and permission configuration."
        )
    with col_gen_ctrl:
        gen_wit = st.selectbox(
            "Target Azure Work Item",
            ["Test Case", "Bug", "User Story", "Task", "Feature", "Epic", "Issue"],
            key="gen_wit"
        )
        use_search_grounding = st.checkbox("🌐 Live Google Search Grounding", value=True)

    st.markdown("#### 📸 Visual Reference (Persistent Staging)")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("**Option A: Paste Screenshot from Clipboard**")
        st.info("💡 You can capture a screenshot (`Win + Shift + S`) and paste it into the Gemini Web chat, or upload the file directly on the right.")
    with col_v2:
        st.markdown("**Option B: Upload Screenshot Files**")
        uploaded_img = st.file_uploader("Select files across the workflow", type=["png", "jpg", "jpeg", "webp"], key="screen_upload")
        if uploaded_img:
            st.image(uploaded_img, caption="Staged Visual Evidence", use_column_width=True)

    if st.button("🚀 Generate Ticket with Memory & Grounding", type="primary", use_container_width=True):
        if not gen_prompt.strip():
            st.warning("Please provide feature or defect context.")
        elif not gemini_key_input:
            st.error("Please provide a Gemini API Key in the left sidebar to use in-app generation.")
        else:
            with st.spinner("Authoring ticket with project invariants and search grounding..."):
                try:
                    mem_invariants = proj_data.get("invariants", [])
                    invariants_text = "\n".join([f"- {inv}" for inv in mem_invariants])
                    system_rules = f"""You are the Lead QA Architect for {active_project}.
Active Persona: {active_persona}
Learned Project Rules:
{invariants_text}

Output format:
Title: <Actionable Title>
Step #,Action,Expected Result
1,<Action>,"<Expected Result>"
"""
                    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key_input}"
                    
                    tools_payload = []
                    if use_search_grounding:
                        tools_payload.append({"google_search": {}})

                    req_body = {
                        "contents": [
                            {"role": "user", "parts": [{"text": f"{system_rules}\n\nUser Request:\n{gen_prompt}"}]}
                        ]
                    }
                    if tools_payload:
                        req_body["tools"] = tools_payload

                    api_res = requests.post(endpoint, json=req_body, timeout=30)
                    if api_res.status_code == 200:
                        gen_text = api_res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        
                        parsed_title, steps, learned = extract_steps_and_learn(gen_text, active_project, active_persona)
                        tcm_xml = convert_to_tcm_xml(steps)
                        desc_html = f"<h3>Scope & Preconditions</h3><p>Generated for <strong>{active_project}</strong> ({active_persona}). Grounded: {use_search_grounding}</p>"

                        st.session_state.last_learning_delta = {"added_invariants": learned}
                        st.session_state.last_parsed = {
                            "title": parsed_title,
                            "wit": gen_wit,
                            "desc_html": desc_html,
                            "tcm_xml": tcm_xml,
                            "steps_count": len(steps)
                        }
                        st.success("Ticket generated! Switch to Tab 1 to review and publish to Azure DevOps.")
                    else:
                        st.error(f"Generation error ({api_res.status_code}): {api_res.text}")
                except Exception as e:
                    st.error(f"Generation failed: {str(e)}")

# ---------------------------------------------------------
# TAB 3: Project Knowledge Base
# ---------------------------------------------------------
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
        st.markdown("#### 🌐 Learned Search Knowledge (From Google)")
        search_kn = mem.get("learned_search_knowledge", [])
        if search_kn:
            for sk in search_kn:
                st.markdown(f"- {sk}")
        else:
            st.info("No external search knowledge saved yet.")

    st.markdown("---")
    st.markdown("#### 🛡️ Learned System Invariants")
    invariants = mem.get("invariants", [])
    if invariants:
        for inv in invariants:
            st.markdown(f"- {inv}")
    else:
        st.info("No invariants recorded yet. Ingest scenarios to automatically absorb rules.")

# ---------------------------------------------------------
# TAB 4: Boundary Conditions
# ---------------------------------------------------------
with tab_boundary:
    st.markdown(f"### ⚙️ Boundary Conditions & Testing Edge Cases for `{active_project}`")
    st.caption("Active boundary definitions that enforce role separation, tenant limits, and validation rules.")
    
    st.markdown("""
    - **Authentication Limits:** Impersonation tokens expire upon session close or navigation away from tenant portal.
    - **RBAC Boundaries:** Standard users attempting administrative endpoints must trigger HTTP 403 Forbidden redirects.
    - **Data Persistence:** Form drafts across multi-tab workflows must retain dirty-state flags until explicit submission or cancellation.
    """)