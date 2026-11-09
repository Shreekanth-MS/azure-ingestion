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
    ingest_raw_gemini_text
)

st.set_page_config(
    page_title="Enterprise QA & Architecture Workbench",
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
# PROJECT SELECTION & PERSISTENT MEMORY
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
        "📁 Active Project Workspace (Remembers Previous Learnings)",
        dropdown_options,
        index=current_idx,
        key="project_dropdown_widget"
    )

if selected_option == "➕ [Add New Project]":
    with col_proj_new:
        new_proj_name = st.text_input("Enter Project Name", placeholder="e.g., Billing Service", key="new_proj_input_box")
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
    f"🧠 **Active Workspace:** `{active_project_name}` — "
    f"{invariants_count} stored invariant(s), {personas_count} persona(s), "
    f"{search_learnings_count} learned search insight(s) remembered."
)

# ---------------------------------------------------------
# UI TABS
# ---------------------------------------------------------
tab_run, tab_offgrid, tab_memory, tab_boundary = st.tabs([
    "🚀 Ticket Generator & Analysis",
    "📋 Off-Grid Paste Ingestor",
    "🧠 Project Knowledge Base",
    "⚙️ Search & Boundary Conditions"
])

# ---------------------------------------------------------
# TAB 1: RUN ENGINE (API Mode)
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
            ["User Story", "Bug", "Test Case", "Feature", "Epic", "Task", "Issue"],
            index=2
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

                    st.success(f"Generated {target_wit} for '{active_project_name}'!")

                    st.markdown("### 1. Title (Copy into Azure 'Title')")
                    st.code(formatted["title"], language="text")

                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        st.markdown(f"### 2. {formatted['field_1_name']}")
                        with st.expander("👁️ Rendered Preview", expanded=True):
                            st.markdown(formatted["field_1_content"], unsafe_allow_html=True)
                        st.caption(f"Click copy icon below to paste into Azure '{formatted['field_1_name']}':")
                        st.code(formatted["field_1_content"], language="html")

                    with col_f2:
                        st.markdown(f"### 3. {formatted['field_2_name']}")
                        with st.expander("👁️ Rendered Preview", expanded=True):
                            st.markdown(formatted["field_2_content"], unsafe_allow_html=True)
                        st.caption(f"Click copy icon below to paste into Azure '{formatted['field_2_name']}':")
                        st.code(formatted["field_2_content"], language="html")

                except Exception as e:
                    st.error(f"Execution Error: {e}")

# ---------------------------------------------------------
# TAB 2: OFF-GRID INGESTOR (Direct Paste from Gemini Web)
# ---------------------------------------------------------
with tab_offgrid:
    st.markdown(f"### 📋 Direct Gemini Web Clipboard Ingestion (`{active_project_name}`)")
    st.caption("Paste any raw response directly from this Gemini conversation. It formats Azure DevOps blocks and saves rules into project memory with zero API quota or connection timeouts.")

    col_paste_mode, col_wit = st.columns([2, 1])
    with col_wit:
        offgrid_wit = st.selectbox(
            "Target Work Item Type",
            ["Test Case", "User Story", "Bug", "Feature", "Epic"],
            key="offgrid_wit_select"
        )

    pasted_raw_text = st.text_area(
        "Paste Raw Gemini Text / JSON Output Here",
        placeholder="Paste response text or JSON directly from your Gemini web conversation...",
        height=260,
        key="offgrid_paste_area"
    )

    if st.button("📥 Parse & Format for Azure", type="primary", use_container_width=True):
        if not pasted_raw_text.strip():
            st.warning("Please paste an answer first.")
        else:
            formatted_res = ingest_raw_gemini_text(
                raw_text=pasted_raw_text,
                project_name=active_project_name,
                work_item_type=offgrid_wit
            )

            st.success(f"Absorbed learnings into '{active_project_name}' and formatted for Azure DevOps!")

            st.markdown("### 1. Title (Copy into Azure 'Title')")
            st.code(formatted_res["title"], language="text")

            col_o1, col_o2 = st.columns(2)
            with col_o1:
                st.markdown(f"### 2. {formatted_res['field_1_name']}")
                with st.expander("👁️ Rendered Preview", expanded=True):
                    st.markdown(formatted_res["field_1_content"], unsafe_allow_html=True)
                st.code(formatted_res["field_1_content"], language="html")

            with col_o2:
                st.markdown(f"### 3. {formatted_res['field_2_name']}")
                with st.expander("👁️ Rendered Preview", expanded=True):
                    st.markdown(formatted_res["field_2_content"], unsafe_allow_html=True)
                st.code(formatted_res["field_2_content"], language="html")

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
            st.caption("No external search knowledge saved yet. Web search queries will record learnings here automatically.")

# ---------------------------------------------------------
# TAB 4: BOUNDARY CONDITIONS
# ---------------------------------------------------------
with tab_boundary:
    st.markdown("### 🎯 Grounding Boundaries & Scope Invariants")
    st.info("The engine treats these rules as non-negotiable boundaries during analysis.")

    default_guardrails = (
        "[MANDATORY ARCHITECTURAL & TEST DESIGN GUARDRAILS]\n\n"
        "1. BIG PICTURE TAB REASONING (NO MICRO-INTERACTIONS):\n"
        "   - Focus strictly on tabs and views at a macroscopic business level.\n"
        "   - DO NOT write individual click, hover, or micro-interaction steps.\n\n"
        "2. MULTI-TAB SHARED PURPOSE RULE:\n"
        "   - Consolidate related configuration views into a single unified lifecycle scenario.\n\n"
        "3. USER INTENT & BUSINESS-DRIVEN NAVIGATION:\n"
        "   - Frame navigation around business state changes and system validation.\n\n"
        "4. END-TO-END LIFECYCLE (START TO FINISH):\n"
        "   - Map from initial entry through dependent tabs to persisted business outcome.\n\n"
        "5. ZERO DUPLICATION OF COMPLETED FLOWS:\n"
        "   - State prerequisites once in preconditions; proceed directly to novel transitions.\n\n"
        "6. CROSS-TAB STATE MUTATION & PERSISTENCE INVARIANTS:\n"
        "   - Verify state coherence and rollback on abandoned multi-tab entries.\n\n"
        "7. RBAC & MULTI-TENANT PERMISSION GATING:\n"
        "   - Verify workflow execution against permission tiers (Super Admin, Tenant Admin, Standard User).\n\n"
        "8. ADVERSARIAL CONCURRENCY & DEFENSIVE BOUNDARIES:\n"
        "   - Cover state conflicts, simultaneous updates, and negative boundaries.\n\n"
        "9. DETERMINISTIC VERIFICATION OUTPUT:\n"
        "   - Structure verification points as '[Business Trigger] -> [Concrete Persisted Outcome]'."
    )

    boundary_text = st.text_area(
        "Negative Boundaries / Scoping Rules",
        value=default_guardrails,
        height=320,
        key="custom_boundaries"
    )