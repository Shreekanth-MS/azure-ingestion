import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from PIL import Image
from streamlit_paste_button import paste_image_button
from brain import (
    DomainBrain,
    format_for_azure_clipboard,
    load_project_memories,
    register_new_project,
    ingest_raw_gemini_text,
    fetch_azure_projects,
    create_azure_work_item,
    ALL_AZURE_WITS
)

st.set_page_config(
    page_title="Enterprise QA & Azure Ingestion Engine",
    page_icon="🛡️",
    layout="wide"
)

# ---------------------------------------------------------
# PERSISTENT SESSION STATE
# ---------------------------------------------------------
if "clipboard_images" not in st.session_state:
    st.session_state.clipboard_images = []

if "uploaded_image_cache" not in st.session_state:
    st.session_state.uploaded_image_cache = []

if "azure_projects" not in st.session_state:
    st.session_state.azure_projects = []

# ---------------------------------------------------------
# SECURITY: Gatekeeper Authentication
# ---------------------------------------------------------
def check_password() -> bool:
    if st.session_state.get("authenticated", False):
        return True

    st.subheader("🔒 Enterprise QA Engine Access")
    st.caption("Authorized enterprise access only. Multi-project memory & visual intelligence.")
    pwd_input = st.text_input("Enter Access Key", type="password", key="auth_password")

    if st.button("Authenticate", type="primary"):
        expected_pwd = None
        try:
            if "APP_PASSWORD" in st.secrets:
                expected_pwd = st.secrets["APP_PASSWORD"]
        except Exception:
            pass

        if not expected_pwd:
            expected_pwd = os.getenv("APP_PASSWORD", "EnterpriseSecure2026!")

        if pwd_input == expected_pwd:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Access Denied: Invalid credentials.")

    return False

if not check_password():
    st.stop()

# ---------------------------------------------------------
# AZURE DEVOPS SIDEBAR CONNECTION
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ☁️ Azure DevOps Integration")
    st.caption("Connect your Azure organization to discover projects and push items directly.")

    default_org = ""
    default_pat = ""
    try:
        if "AZURE_ORG" in st.secrets:
            default_org = st.secrets["AZURE_ORG"]
        if "AZURE_PAT" in st.secrets:
            default_pat = st.secrets["AZURE_PAT"]
    except Exception:
        pass

    azure_org_input = st.text_input(
        "Azure Org Name / URL",
        value=default_org or os.getenv("AZURE_ORG", ""),
        placeholder="e.g. MyEnterpriseOrg",
        help="Your Azure DevOps organization name ([dev.azure.com/YourOrgName](https://dev.azure.com/YourOrgName))"
    )

    azure_pat_input = st.text_input(
        "Personal Access Token (PAT)",
        value=default_pat or os.getenv("AZURE_PAT", ""),
        type="password",
        help="PAT with Work Items (Read, write, & manage) permissions"
    )

    if st.button("🔄 Connect & Fetch Azure Projects", use_container_width=True):
        if azure_org_input and azure_pat_input:
            with st.spinner("Connecting to Azure DevOps REST API..."):
                projs = fetch_azure_projects(azure_org_input, azure_pat_input)
                if projs:
                    st.session_state.azure_projects = projs
                    st.success(f"Connected! Found {len(projs)} project(s).")
                else:
                    st.error("Could not fetch projects. Check your Organization name and PAT permissions.")
        else:
            st.warning("Please provide both Azure Org and PAT.")

    if st.session_state.azure_projects:
        azure_target_project = st.selectbox(
            "📌 Destination Azure Project",
            st.session_state.azure_projects,
            key="azure_target_project_select"
        )
    else:
        azure_target_project = None
        st.info("Provide your PAT above to select destination projects.")

# ---------------------------------------------------------
# LOCAL PROJECT WORKSPACE SELECTION & PERSISTENT MEMORY
# ---------------------------------------------------------
project_memories = load_project_memories()
project_list = list(project_memories.keys())

if "selected_project_name" not in st.session_state:
    st.session_state.selected_project_name = project_list[0] if project_list else "New Project"

dropdown_options = project_list + ["➕ [Add New Project]"]

col_proj_sel, col_proj_new = st.columns([2, 1.2])

with col_proj_sel:
    current_idx = (
        dropdown_options.index(st.session_state.selected_project_name)
        if st.session_state.selected_project_name in dropdown_options
        else 0
    )
    selected_option = st.selectbox(
        "📁 Local Learning Memory Profile",
        dropdown_options,
        index=current_idx,
        key="project_dropdown_widget"
    )

if selected_option == "➕ [Add New Project]":
    with col_proj_new:
        new_proj_name = st.text_input("Enter Project Name", placeholder="e.g., DentalPortal", key="new_proj_input_box")
        if st.button("Create Project Profile", type="primary", use_container_width=True):
            if new_proj_name.strip():
                clean_name = new_proj_name.strip()
                register_new_project(clean_name)
                st.session_state.selected_project_name = clean_name
                st.rerun()
            else:
                st.warning("Please type a project name.")
else:
    st.session_state.selected_project_name = selected_option

active_project_name = st.session_state.selected_project_name

proj_data = project_memories.get(active_project_name, {})
invariants_count = len(proj_data.get("invariants", []))
personas_count = len(proj_data.get("personas", []))
search_learnings_count = len(proj_data.get("learned_search_knowledge", []))

st.caption(
    f"🧠 **Active Memory Profile:** `{active_project_name}` — "
    f"{invariants_count} stored invariant(s), {personas_count} persona(s), "
    f"{search_learnings_count} learned search insight(s) retained."
)

# ---------------------------------------------------------
# UI TABS
# ---------------------------------------------------------
tab_offgrid, tab_run, tab_memory, tab_boundary = st.tabs([
    "📋 Off-Grid Paste Ingestor & Azure Publisher",
    "🚀 Full Ticket Generator & Analysis",
    "🧠 Project Knowledge Base",
    "⚙️ Boundary Conditions"
])

# ---------------------------------------------------------
# TAB 1: OFF-GRID INGESTOR (Direct Paste from Gemini Web)
# ---------------------------------------------------------
with tab_offgrid:
    st.markdown("### 📋 Direct Gemini Web Ingestion & Azure DevOps Publisher")
    st.caption("Paste any raw scenario or test case generated in your Gemini chat. The brain will absorb its rules into local memory, render Azure-ready HTML, and let you push it directly to Azure DevOps.")

    col_og_wit, col_og_dest = st.columns([1.5, 2])
    with col_og_wit:
        offgrid_wit = st.selectbox(
            "Target Azure Work Item",
            ALL_AZURE_WITS,
            index=ALL_AZURE_WITS.index("Test Case"),
            key="offgrid_wit_select"
        )
    with col_og_dest:
        dest_display = f"**{azure_target_project}**" if azure_target_project else "*None selected (Configure PAT in sidebar)*"
        st.markdown(f"Target Azure Project: {dest_display}")

    pasted_raw_text = st.text_area(
        "Paste Raw Gemini Text / JSON Output Here",
        placeholder="Paste response text or JSON directly from your Gemini web conversation...",
        height=240,
        key="offgrid_paste_area"
    )

    if st.button("📥 Parse, Learn & Format", type="primary", use_container_width=True):
        if not pasted_raw_text.strip():
            st.warning("Please paste content from Gemini first.")
        else:
            formatted_res = ingest_raw_gemini_text(
                raw_text=pasted_raw_text,
                project_name=active_project_name,
                work_item_type=offgrid_wit
            )
            st.session_state["last_parsed_result"] = formatted_res
            st.session_state["last_parsed_wit"] = offgrid_wit
            st.success(f"Absorbed learnings into memory for `{active_project_name}`!")

    # Display results and direct push action
    if "last_parsed_result" in st.session_state:
        res = st.session_state["last_parsed_result"]
        current_wit = st.session_state.get("last_parsed_wit", "Test Case")

        st.markdown("---")

        if azure_target_project and azure_pat_input:
            if st.button(f"🚀 Publish Directly to Azure DevOps ({azure_target_project})", type="primary", use_container_width=True):
                with st.spinner("Submitting to Azure DevOps REST API..."):
                    push_res = create_azure_work_item(
                        org_name=azure_org_input,
                        project=azure_target_project,
                        work_item_type=current_wit,
                        title=res["title"],
                        field_1_name=res["field_1_name"],
                        field_1_content=res["field_1_content"],
                        field_2_name=res["field_2_name"],
                        field_2_content=res["field_2_content"],
                        pat=azure_pat_input
                    )
                    if push_res.get("success"):
                        st.balloons()
                        st.success(f"🎉 Created {current_wit} #{push_res['id']} in Azure DevOps!")
                        st.markdown(f"👉 **[Open Work Item #{push_res['id']} in Azure DevOps]({push_res['url']})**")
                    else:
                        st.error(f"Failed to publish to Azure: {push_res.get('error')}")
        else:
            st.info("💡 Tip: Connect your Azure Org and PAT in the left sidebar to enable direct 1-click publishing.")

        st.markdown("### 1. Title")
        st.code(res["title"], language="text")

        col_o1, col_o2 = st.columns(2)
        with col_o1:
            st.markdown(f"### 2. {res['field_1_name']}")
            with st.expander("👁️ Rendered Preview", expanded=True):
                st.markdown(res["field_1_content"], unsafe_allow_html=True)
            st.caption("Azure HTML snippet:")
            st.code(res["field_1_content"], language="html")

        with col_o2:
            st.markdown(f"### 3. {res['field_2_name']}")
            with st.expander("👁️ Rendered Preview", expanded=True):
                st.markdown(res["field_2_content"], unsafe_allow_html=True)
            st.caption("Azure HTML snippet:")
            st.code(res["field_2_content"], language="html")

# ---------------------------------------------------------
# TAB 2: RUN ENGINE (API Mode)
# ---------------------------------------------------------
with tab_run:
    col_text, col_controls = st.columns([2.5, 1.2])

    with col_text:
        req_input = st.text_area(
            "Feature / Requirement / Defect Context",
            placeholder=f"e.g., In {active_project_name}, generate integration test case for administrative checkout and permission configuration.",
            height=130
        )

    with col_controls:
        target_wit = st.selectbox(
            "Target Azure Work Item",
            ALL_AZURE_WITS,
            index=ALL_AZURE_WITS.index("Test Case"),
            key="run_wit_select"
        )
        search_requested = st.checkbox("🌐 Live Google Search Grounding", value=True)
        st.caption("Auto-disabled when screenshots are staged.")

    st.markdown("### 📸 Visual Reference (Persistent Staging)")

    col_paste, col_upload = st.columns([1, 1.4])

    with col_paste:
        st.markdown("**Option A: Paste Screenshot from Clipboard**")
        paste_result = paste_image_button(
            label="📋 Click to Paste Image from Clipboard",
            text_color="#ffffff",
            background_color="#0066cc",
            hover_background_color="#004c99",
            key="clipboard_paster"
        )

        if paste_result.image_data is not None:
            pasted_pil = paste_result.image_data
            if not any(img.tobytes() == pasted_pil.tobytes() for img in st.session_state.clipboard_images):
                st.session_state.clipboard_images.append(pasted_pil)
                st.toast(f"Pasted screen #{len(st.session_state.clipboard_images)} staged!")

    with col_upload:
        st.markdown("**Option B: Upload Screenshot Files**")
        uploaded_files = st.file_uploader(
            "Select files across the workflow",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            help="Processed in RAM. Images remain staged until reset."
        )

        if uploaded_files:
            for file in uploaded_files:
                img = Image.open(file)
                if not any(cached.tobytes() == img.tobytes() for cached in st.session_state.uploaded_image_cache):
                    st.session_state.uploaded_image_cache.append(img)

    all_staged_images = st.session_state.clipboard_images + st.session_state.uploaded_image_cache

    enable_search = search_requested
    if all_staged_images:
        col_info, col_clear = st.columns([3, 1])
        with col_info:
            st.info(
                f"🔒 **Multi-Image Privacy Guardrail Active:** {len(all_staged_images)} screenshot(s) staged. "
                f"Web search disabled. Images remain ready for subsequent iterations."
            )
        with col_clear:
            if st.button("🗑️ Reset Staged Images", key="reset_images_btn", use_container_width=True):
                st.session_state.clipboard_images = []
                st.session_state.uploaded_image_cache = []
                st.rerun()

        enable_search = False

        with st.expander(f"👁️ Staged Workflow Screens ({len(all_staged_images)} Total)", expanded=True):
            cols = st.columns(min(len(all_staged_images), 4))
            for idx, img in enumerate(all_staged_images):
                with cols[idx % len(cols)]:
                    st.image(img, caption=f"Screen {idx + 1}", use_container_width=True)

    st.markdown("---")

    if st.button("🚀 Analyze & Generate Azure Format", type="primary", use_container_width=True):
        if not req_input.strip() and not all_staged_images:
            st.warning("Please provide either text context or application screenshots.")
        else:
            with st.spinner(f"Synthesizing for '{active_project_name}' under brain memory & boundaries..."):
                try:
                    fresh_brain = DomainBrain()
                    ticket_data = fresh_brain.think_hybrid(
                        requirement=req_input,
                        project_name=active_project_name,
                        mode=target_wit,
                        images=all_staged_images if all_staged_images else None,
                        boundaries=st.session_state.get("custom_boundaries", ""),
                        enable_web_search=enable_search
                    )
                    formatted = format_for_azure_clipboard(ticket_data, target_wit)
                    st.session_state["api_generated_result"] = formatted
                    st.session_state["api_generated_wit"] = target_wit
                    st.success(f"Generated {target_wit} for '{active_project_name}'!")
                except Exception as e:
                    st.error(f"Execution Error: {e}")

    if "api_generated_result" in st.session_state:
        formatted = st.session_state["api_generated_result"]
        gen_wit = st.session_state.get("api_generated_wit", "Test Case")

        if azure_target_project and azure_pat_input:
            if st.button(f"🚀 Publish Directly to Azure DevOps ({azure_target_project})", key="api_push_btn", type="primary", use_container_width=True):
                with st.spinner("Submitting to Azure..."):
                    push_res = create_azure_work_item(
                        org_name=azure_org_input,
                        project=azure_target_project,
                        work_item_type=gen_wit,
                        title=formatted["title"],
                        field_1_name=formatted["field_1_name"],
                        field_1_content=formatted["field_1_content"],
                        field_2_name=formatted["field_2_name"],
                        field_2_content=formatted["field_2_content"],
                        pat=azure_pat_input
                    )
                    if push_res.get("success"):
                        st.balloons()
                        st.success(f"🎉 Created {gen_wit} #{push_res['id']} in Azure DevOps!")
                        st.markdown(f"👉 **[Open Work Item #{push_res['id']}]({push_res['url']})**")
                    else:
                        st.error(f"Azure error: {push_res.get('error')}")

        st.markdown("### 1. Title")
        st.code(formatted["title"], language="text")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown(f"### 2. {formatted['field_1_name']}")
            with st.expander("👁️ Rendered Preview", expanded=True):
                st.markdown(formatted["field_1_content"], unsafe_allow_html=True)
            st.code(formatted["field_1_content"], language="html")

        with col_f2:
            st.markdown(f"### 3. {formatted['field_2_name']}")
            with st.expander("👁️ Rendered Preview", expanded=True):
                st.markdown(formatted["field_2_content"], unsafe_allow_html=True)
            st.code(formatted["field_2_content"], language="html")

# ---------------------------------------------------------
# TAB 3: PROJECT MEMORY INSPECTOR
# ---------------------------------------------------------
with tab_memory:
    st.markdown(f"### 🧠 Stored Knowledge for `{active_project_name}`")
    st.write(f"**Architecture Summary:** {proj_data.get('summary', 'None established yet.')}")

    col_k1, col_k2 = st.columns(2)
    with col_k1:
        st.markdown("**Known Personas:**")
        st.write(", ".join(proj_data.get("personas", [])) or "None recorded yet.")
        st.markdown("**Learned System Invariants:**")
        invariants = proj_data.get("invariants", [])
        if invariants:
            for inv in invariants:
                st.markdown(f"- {inv}")
        else:
            st.caption("No invariants recorded yet.")

    with col_k2:
        st.markdown("**🌐 Learned Search Knowledge (From Google):**")
        search_learnings = proj_data.get("learned_search_knowledge", [])
        if search_learnings:
            for item in search_learnings:
                st.markdown(f"- 🔍 {item}")
        else:
            st.caption("No external search knowledge saved yet.")

# ---------------------------------------------------------
# TAB 4: BOUNDARY CONDITIONS
# ---------------------------------------------------------
with tab_boundary:
    st.markdown("### 🎯 Grounding Boundaries & Scope Invariants")
    default_guardrails = (
        "[MANDATORY ARCHITECTURAL & TEST DESIGN GUARDRAILS]\n\n"
        "1. BIG PICTURE TAB REASONING: Focus strictly on tabs and views at a macroscopic business level.\n"
        "2. CONSOLIDATED SCENARIO: Combine dependent tabs into one cohesive lifecycle scenario.\n"
        "3. NO MICRO-INTERACTION CLICKS: Avoid 'Click button X' or trivial UI movements.\n"
        "4. STRICT RBAC ISOLATION: Explicitly validate permissions across role tiers.\n"
        "5. CROSS-TAB STATE MUTATION: Validate state coherence and rollback on cancellation."
    )

    boundary_text = st.text_area(
        "Negative Boundaries / Scoping Rules",
        value=default_guardrails,
        height=260,
        key="custom_boundaries"
    )