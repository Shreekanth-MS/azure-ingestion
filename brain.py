import os
import json
import re
import time
import io
import base64
from typing import Optional
import requests
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(BASE_DIR, "projects_memory.json")

DEFAULT_GLOBAL_BOUNDARIES = (
    "- Zero Outbound Data Leakage: Strictly prohibit transmitting, exposing, or echoing proprietary schemas, internal API endpoints, tenant IDs, PII, or project memory contents to external web search queries or third-party endpoints.\n"
    "- One-Way Inbound Learning Only: Absorb rules, edge cases, and domain patterns from external user-provided inputs, pasted text, and uploaded screenshots, but never use internal project memory as outbound search context.\n"
    "- Sanitized Search Query Isolation: When Live Google Search Grounding is active, outbound search queries must contain only generic public industry standards, protocols, or framework terms—never project names, client names, or internal business logic.\n"
    "- Visual Context Air-Gap: Whenever UI screenshots or visual artifacts are uploaded, external web search grounding must be completely disabled so analysis relies 100% on local visual data and stored project memory."
)

# All 7 supported Azure DevOps Work Item types
ALL_AZURE_WITS = [
    "Bug",
    "Epic",
    "Feature",
    "Issue",
    "Task",
    "Test Case",
    "User Story"
]


# ----------------------------------------------------------------------
# 1. PERSISTENT MULTI-PROJECT MEMORY
# ----------------------------------------------------------------------
def _read_raw_store() -> dict:
    """Reads the full memory store, auto-migrating legacy flat schemas if present."""
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    if "projects" in data:
                        data.setdefault("global_boundaries", DEFAULT_GLOBAL_BOUNDARIES)
                        return data
                    return {
                        "active_project": list(data.keys())[0],
                        "global_boundaries": DEFAULT_GLOBAL_BOUNDARIES,
                        "projects": data
                    }
        except Exception:
            pass
    return {
        "active_project": "New Project",
        "global_boundaries": DEFAULT_GLOBAL_BOUNDARIES,
        "projects": {
            "New Project": {
                "summary": "Enterprise multi-tenant cloud application workspace.",
                "invariants": ["Tenant isolation and role-based permissions must be enforced."],
                "personas": ["Super Admin", "Standard User"],
                "learned_search_knowledge": []
            }
        }
    }


def load_project_memories() -> dict:
    """Loads long-term project knowledge and invariants."""
    return _read_raw_store().get("projects", {})


def register_new_project(project_name: str) -> dict:
    """Explicitly creates and persists a new project profile immediately."""
    clean_name = project_name.strip()
    store = _read_raw_store()
    memories = store["projects"]
    if clean_name not in memories:
        memories[clean_name] = {
            "summary": f"Enterprise architecture and QA workspace for {clean_name}.",
            "invariants": [],
            "personas": ["Super Admin", "Standard User"],
            "learned_search_knowledge": []
        }
    store["active_project"] = clean_name
    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not write project memory: {e}")
    return memories


def save_project_memory(
    project_name: str,
    new_summary: str,
    new_invariants: list[str],
    new_personas: list[str],
    new_search_learnings: list[str] = None
):
    """Appends discovered invariants, personas, and web search discoveries to the project profile."""
    store = _read_raw_store()
    memories = store["projects"]
    if project_name not in memories:
        memories[project_name] = {
            "summary": new_summary,
            "invariants": [],
            "personas": [],
            "learned_search_knowledge": []
        }

    existing = memories[project_name]
    if new_summary and len(new_summary) > len(existing.get("summary", "")):
        existing["summary"] = new_summary

    combined_invariants = list(dict.fromkeys(existing.get("invariants", []) + (new_invariants or [])))
    combined_personas = list(dict.fromkeys(existing.get("personas", []) + (new_personas or [])))
    combined_search_learnings = list(
        dict.fromkeys(existing.get("learned_search_knowledge", []) + (new_search_learnings or []))
    )

    existing["invariants"] = combined_invariants[-25:]
    existing["personas"] = combined_personas[-10:]
    existing["learned_search_knowledge"] = combined_search_learnings[-20:]

    memories[project_name] = existing
    store["active_project"] = project_name

    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not persist project memory: {e}")


# ----------------------------------------------------------------------
# 2. SANITIZATION & AZURE FORMATTING
# ----------------------------------------------------------------------
def sanitize_input(text: str) -> str:
    """Masks emails, internal IP addresses, API secrets, and DB connection strings."""
    if not text:
        return ""
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    text = re.sub(r'\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b', '[INTERNAL_IP]', text)
    text = re.sub(r'(bearer\s+[A-Za-z0-9_\-\.]{20,}|ghp_[A-Za-z0-9]{36}|AIza[0-9A-Za-z-_]{35})', '[REDACTED_SECRET]', text, flags=re.IGNORECASE)
    text = re.sub(r'(postgres|mysql|mongodb|redis):\/\/[^\s]+', '[REDACTED_DB_URI]', text, flags=re.IGNORECASE)
    return text


def format_for_azure_clipboard(ticket_data: dict, work_item_type: str) -> dict:
    """Formats JSON output into Azure DevOps-compatible HTML blocks for clean copy-pasting."""
    title = ticket_data.get("title_suggestion", "Architectural Requirement")
    arch_summary = ticket_data.get("architecture_summary", "")
    invariants = ticket_data.get("system_invariants", [])
    stories = ticket_data.get("reciprocal_user_stories", [])
    scenarios = ticket_data.get("adversarial_edge_cases_and_test_scenarios", [])
    search_insights = ticket_data.get("external_search_learnings", [])

    insights_html = ""
    if search_insights:
        insights_html = "<h3>Learned External Standards / Findings</h3><ul>" + "".join([f"<li>{x}</li>" for x in search_insights]) + "</ul>"

    if work_item_type in ["User Story", "Feature", "Epic", "Issue"]:
        desc_lines = [
            "<h3>Architecture & Flow Boundaries</h3>",
            f"<p>{arch_summary}</p>",
            "<h3>Core System Invariants</h3>",
            "<ul>" + "".join([f"<li>{inv}</li>" for inv in invariants]) + "</ul>",
            insights_html
        ]
        ac_lines = ["<h3>Acceptance Criteria & Reciprocal Stories</h3>"]
        for s in stories:
            ac_lines.append(
                f"<p><strong>As a</strong> {s.get('as_a')}<br/>"
                f"<strong>I want to</strong> {s.get('i_want')}<br/>"
                f"<strong>So that</strong> {s.get('so_that')}</p>"
                f"<blockquote><pre>{s.get('acceptance_criteria')}</pre></blockquote><hr/>"
            )
        prefix = f"[{work_item_type}] " if work_item_type in ["Feature", "Epic", "Issue"] else ""
        return {
            "title": f"{prefix}{title}",
            "field_1_name": "Description",
            "field_1_content": "\n".join([x for x in desc_lines if x]),
            "field_2_name": "Acceptance Criteria",
            "field_2_content": "\n".join(ac_lines)
        }

    elif work_item_type == "Task":
        task_desc = [
            f"<h3>Task Objective</h3><p>{arch_summary}</p>",
            "<h3>System Invariants & Technical Rules</h3>",
            "<ul>" + "".join([f"<li>{inv}</li>" for inv in invariants]) + "</ul>",
            insights_html
        ]
        task_steps = ["<h3>Implementation & Verification Tasks</h3><ol>"]
        for sc in scenarios:
            task_steps.append(f"<li><strong>{sc.get('title')}</strong>: {sc.get('action')} &rarr; <em>{sc.get('expected_behavior')}</em></li>")
        task_steps.append("</ol>")
        return {
            "title": f"[Task] {title}",
            "field_1_name": "Description",
            "field_1_content": "\n".join([x for x in task_desc if x]),
            "field_2_name": "Implementation Steps",
            "field_2_content": "\n".join(task_steps)
        }

    elif work_item_type == "Bug":
        repro_lines = [
            "<h3>Architectural Failure Context</h3>",
            f"<p>{arch_summary}</p>",
            "<h3>Reproduction & Adversarial Trigger Scenarios</h3>"
        ]
        for sc in scenarios:
            repro_lines.append(
                f"<h4>[{sc.get('scenario_type')}] {sc.get('title')}</h4>"
                f"<p><strong>Preconditions:</strong> {sc.get('preconditions')}<br/>"
                f"<strong>Trigger Action:</strong> {sc.get('action')}<br/>"
                f"<strong>Expected Defensive Behavior:</strong> {sc.get('expected_behavior')}</p>"
            )
        inv_lines = [
            "<h3>Violated System Invariants</h3>",
            "<ul>" + "".join([f"<li>{inv}</li>" for inv in invariants]) + "</ul>",
            insights_html
        ]
        return {
            "title": f"[Bug] {title}",
            "field_1_name": "Repro Steps",
            "field_1_content": "\n".join(repro_lines),
            "field_2_name": "System Info / Constraints",
            "field_2_content": "\n".join([x for x in inv_lines if x])
        }

    elif work_item_type == "Test Case":
        precondition_lines = [
            f"<h3>Objective & Test Scope</h3><p>{arch_summary}</p>",
            "<h3>Preconditions & Guardrail Invariants</h3>",
            "<ul>" + "".join([f"<li>{inv}</li>" for inv in invariants]) + "</ul>",
            insights_html
        ]
        steps_lines = [
            "<h3>Execution Sequence & Verification Grid</h3>",
            "<table border='1' cellpadding='6' style='border-collapse:collapse; width:100%;'>",
            "<tr style='background-color:#f0f0f0;'><th>#</th><th>Trigger / Action</th><th>Expected Defensive Result</th></tr>"
        ]
        for idx, sc in enumerate(scenarios, 1):
            steps_lines.append(
                f"<tr>"
                f"<td><strong>{idx}</strong></td>"
                f"<td><strong>{sc.get('title')}</strong><br/>{sc.get('action')}</td>"
                f"<td>{sc.get('expected_behavior')}</td>"
                f"</tr>"
            )
        steps_lines.append("</table>")
        return {
            "title": f"[Test Case] {title}",
            "field_1_name": "Summary & Preconditions",
            "field_1_content": "\n".join([x for x in precondition_lines if x]),
            "field_2_name": "Steps to Run",
            "field_2_content": "\n".join(steps_lines)
        }

    default_content = [
        f"<h3>Summary</h3><p>{arch_summary}</p>",
        "<h3>Invariants & Technical Scope</h3>",
        "<ul>" + "".join([f"<li>{inv}</li>" for inv in invariants]) + "</ul>",
        insights_html
    ]
    return {
        "title": title,
        "field_1_name": "Description",
        "field_1_content": "\n".join([x for x in default_content if x]),
        "field_2_name": "Technical Notes",
        "field_2_content": "<p>Review schema boundaries and edge cases prior to implementation.</p>"
    }


def ingest_raw_gemini_text(raw_text: str, project_name: str, work_item_type: str = "Test Case") -> dict:
    """Parses unstructured text or JSON pasted directly from a Gemini web session."""
    clean_text = raw_text.strip()

    parsed_json = None
    if "{" in clean_text and "}" in clean_text:
        match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
        if match:
            try:
                parsed_json = json.loads(match.group(1))
            except Exception:
                pass

    if parsed_json and isinstance(parsed_json, dict):
        save_project_memory(
            project_name=project_name,
            new_summary=parsed_json.get("architecture_summary", ""),
            new_invariants=parsed_json.get("system_invariants", []),
            new_personas=parsed_json.get("involved_personas", []),
            new_search_learnings=parsed_json.get("external_search_learnings", [])
        )
        return format_for_azure_clipboard(parsed_json, work_item_type)

    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]

    title = f"[{work_item_type}] {project_name} - Integration Workflow"
    for line in lines[:5]:
        if any(line.lower().startswith(p) for p in ["title:", "# ", "**title**:", "scenario:"]):
            title = re.sub(r"^(#+|\*\*title\*\*:?|title:?)\s*", "", line, flags=re.IGNORECASE).strip()
            break

    discovered_invariants = []
    for line in lines:
        if line.startswith(("-", "*", "•")) and any(k in line.lower() for k in ["must", "invariant", "rule", "required", "ensure"]):
            clean_inv = re.sub(r"^[-*•]\s*", "", line).strip()
            discovered_invariants.append(clean_inv)

    html_content = re.sub(r"^### (.*)", r"<h3>\1</h3>", clean_text, flags=re.MULTILINE)
    html_content = re.sub(r"^## (.*)", r"<h2>\1</h2>", html_content, flags=re.MULTILINE)
    html_content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html_content)
    html_content = html_content.replace("\n", "<br/>")

    if discovered_invariants:
        save_project_memory(
            project_name=project_name,
            new_summary=f"Pasted off-grid knowledge for {project_name}.",
            new_invariants=discovered_invariants,
            new_personas=[]
        )

    return {
        "title": title,
        "field_1_name": "Description / Summary",
        "field_1_content": f"<h3>Ingested Analysis ({project_name})</h3>\n<p>{html_content}</p>",
        "field_2_name": "Steps & Verification",
        "field_2_content": f"<h3>Extracted Steps</h3>\n<p>{html_content}</p>"
    }


# ----------------------------------------------------------------------
# 3. AZURE DEVOPS REST API INTEGRATION
# ----------------------------------------------------------------------
def get_azure_auth_headers(pat: str) -> dict:
    b64_pat = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {b64_pat}",
        "Content-Type": "application/json"
    }


def fetch_azure_projects(org_name: str, pat: str) -> list[str]:
    """Retrieves list of project names accessible by the given Azure PAT."""
    clean_org = org_name.strip().rstrip("/").split("/")[-1]
    url = f"https://dev.azure.com/{clean_org}/_apis/projects?api-version=7.1-preview.4"
    try:
        res = requests.get(url, headers=get_azure_auth_headers(pat), timeout=10)
        if res.status_code == 200:
            data = res.json()
            return [p["name"] for p in data.get("value", [])]
        return []
    except Exception as e:
        print(f"Error fetching Azure DevOps projects: {e}")
        return []


def create_azure_work_item(
    org_name: str,
    project: str,
    work_item_type: str,
    title: str,
    field_1_name: str,
    field_1_content: str,
    field_2_name: str,
    field_2_content: str,
    pat: str
) -> dict:
    """Creates a work item across all 7 types via REST API and returns item ID and web URL."""
    clean_org = org_name.strip().rstrip("/").split("/")[-1]
    wit_clean = work_item_type.replace(" ", "%20")
    url = f"https://dev.azure.com/{clean_org}/{project}/_apis/wit/workitems/${wit_clean}?api-version=7.1"

    b64_pat = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    patch_headers = {
        "Authorization": f"Basic {b64_pat}",
        "Content-Type": "application/json-patch+json"
    }

    patch_doc = [
        {"op": "add", "path": "/fields/System.Title", "value": title}
    ]

    if work_item_type in ["User Story", "Feature", "Epic", "Issue"]:
        patch_doc.append({"op": "add", "path": "/fields/System.Description", "value": field_1_content})
        patch_doc.append({"op": "add", "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria", "value": field_2_content})
    elif work_item_type == "Bug":
        patch_doc.append({"op": "add", "path": "/fields/Microsoft.VSTS.TCM.ReproSteps", "value": field_1_content})
        patch_doc.append({"op": "add", "path": "/fields/Microsoft.VSTS.TCM.SystemInfo", "value": field_2_content})
    elif work_item_type == "Test Case":
        patch_doc.append({"op": "add", "path": "/fields/System.Description", "value": field_1_content})
        patch_doc.append({"op": "add", "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria", "value": field_2_content})
    elif work_item_type == "Task":
        patch_doc.append({"op": "add", "path": "/fields/System.Description", "value": f"{field_1_content}<hr/>{field_2_content}"})
    else:
        patch_doc.append({"op": "add", "path": "/fields/System.Description", "value": f"{field_1_content}<hr/>{field_2_content}"})

    res = requests.post(url, headers=patch_headers, json=patch_doc, timeout=15)

    if res.status_code in [200, 201]:
        res_data = res.json()
        item_id = res_data.get("id")
        web_url = res_data.get("_links", {}).get("html", {}).get("href", f"https://dev.azure.com/{clean_org}/{project}/_workitems/edit/{item_id}")
        return {"success": True, "id": item_id, "url": web_url}
    else:
        return {"success": False, "error": f"Status {res.status_code}: {res.text}"}


# ----------------------------------------------------------------------
# 4. KEY ROTATOR & GEMINI ENGINE
# ----------------------------------------------------------------------
class KeyRotator:
    def __init__(self, keys: list[str]):
        self.keys = [k.strip() for k in keys if k.strip()]
        self.current_idx = 0
        if not self.keys:
            raise ValueError("No valid GEMINI_API_KEYS found.")

    def get_client(self) -> genai.Client:
        return genai.Client(api_key=self.keys[self.current_idx])

    def rotate(self) -> genai.Client:
        self.current_idx = (self.current_idx + 1) % len(self.keys)
        masked_key = f"...{self.keys[self.current_idx][-6:]}"
        print(f"Switched to API key [{self.current_idx + 1}/{len(self.keys)}] ({masked_key})")
        return self.get_client()


class DomainBrain:
    def __init__(self):
        keys_env = ""
        try:
            import streamlit as st
            if "GEMINI_API_KEYS" in st.secrets:
                keys_env = st.secrets["GEMINI_API_KEYS"]
        except Exception:
            pass

        if not keys_env:
            keys_env = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""

        keys_list = [k.strip() for k in keys_env.split(",") if k.strip()]
        if not keys_list:
            raise ValueError("GEMINI_API_KEYS not configured in environment or secrets.")

        self.rotator = KeyRotator(keys_list)

    def think_hybrid(
        self,
        requirement: str,
        project_name: str = "New Project",
        mode: str = "Test Case",
        images: Optional[list[Image.Image]] = None,
        boundaries: str = "",
        enable_web_search: bool = True
    ) -> dict:
        clean_req = sanitize_input(requirement)
        clean_boundaries = sanitize_input(boundaries)

        raw_store = _read_raw_store()
        memories = raw_store.get("projects", {})
        global_boundaries = raw_store.get("global_boundaries", "").strip()
        proj_mem = memories.get(project_name, {})

        known_summary = proj_mem.get("summary", "Enterprise cloud SaaS system.")
        known_invariants = "\n- ".join(proj_mem.get("invariants", []))
        known_personas = ", ".join(proj_mem.get("personas", []))
        known_search = "\n- ".join(proj_mem.get("learned_search_knowledge", []))

        all_boundaries = f"{global_boundaries}\n{clean_boundaries}".strip()

        memory_context = f"""
INTERNAL BRAIN MEMORY FOR PROJECT [{project_name}]:
- Architecture Summary: {known_summary}
- Known Personas: {known_personas if known_personas else "Super Admin, Standard User"}
- Established System Invariants:
- {known_invariants if known_invariants else "Standard enterprise RBAC and tenant isolation."}
- Previous Search Learnings:
- {known_search if known_search else "None recorded yet"}
"""

        has_images = bool(images and len(images) > 0)

        active_tools = []
        search_instruction = ""
        if enable_web_search and not has_images:
            active_tools = [{"google_search": {}}]
            search_instruction = """
ONE-WAY INBOUND LEARNING & ZERO-LEAKAGE GUARDRAIL:
1. Never include internal project names, proprietary domain terms, credentials, or internal data inside Google Search queries.
2. Search ONLY for public technical standards, regulatory rules, or generic software patterns.
3. Absorb external standards and user-provided inputs into 'external_search_learnings' and 'system_invariants' without exposing internal context outward.
"""
        elif has_images:
            search_instruction = """
PRIVACY BOUNDARY: Visual screenshots provided. Base all reasoning strictly on local UI context. Web Search is disabled.
"""

        system_instruction = f"""
You are an Enterprise SaaS Architect & Principal QA Strategist.
ACTIVE WORKSPACE: {project_name}
TARGET ARTIFACT: {mode}

{memory_context}

{search_instruction}

GLOBAL NEGATIVE BOUNDARIES & GUARDRAILS:
{all_boundaries}

INSTRUCTIONS:
1. Brain First: Treat project memory and inputs as the single source of truth.
2. Macroscopic: Consolidate multi-tab flows into a unified test lifecycle without micro-interaction clicks.
3. Return strictly valid JSON matching the schema.
"""

        prompt_text = f"""
{system_instruction}

CONTEXT / REQUIREMENT:
{clean_req if clean_req else "Analyze attached screen(s) under declared project invariants."}

OUTPUT JSON SCHEMA:
{{
  "mode": "{mode}",
  "title_suggestion": "Concise standard title for the ticket",
  "architecture_summary": "Architecture summary and cross-tab/data flow boundaries",
  "involved_personas": ["Persona 1", "Persona 2"],
  "external_search_learnings": [
    "Key standards, API behaviors, or compliance rules newly learned from Google Search"
  ],
  "reciprocal_user_stories": [
    {{
      "persona": "Role",
      "as_a": "Role",
      "i_want": "Action or capability",
      "so_that": "Business value",
      "acceptance_criteria": "Given/When/Then criteria"
    }}
  ],
  "adversarial_edge_cases_and_test_scenarios": [
    {{
      "scenario_type": "Boundary / Concurrency / State Invalidation",
      "title": "Scenario title",
      "preconditions": "Initial system state",
      "action": "Triggering action across workflow",
      "expected_behavior": "Defensive architectural response"
    }}
  ],
  "system_invariants": [
    "Non-negotiable business rules"
  ]
}}
"""

        contents = []
        if has_images:
            for img in images:
                clean_img = img.convert("RGB")
                max_dim = 960
                if max(clean_img.size) > max_dim:
                    clean_img.thumbnail((max_dim, max_dim), Image.Resampling.BILINEAR)

                buf = io.BytesIO()
                clean_img.save(buf, format="JPEG", quality=65, optimize=True)
                contents.append(
                    types.Part.from_bytes(
                        data=buf.getvalue(),
                        mime_type="image/jpeg"
                    )
                )

        contents.append(prompt_text)

        candidate_models = [
            "gemini-3.8-flash",
            "gemini-3.8-pro",
            "gemini-2.5-pro"
        ]
        errors_logged = []

        for attempt in range(len(self.rotator.keys)):
            client = self.rotator.get_client()

            for model_name in candidate_models:
                try:
                    config_args = {
                        "temperature": 0.1,
                        "max_output_tokens": 4096,
                        "response_mime_type": "application/json"
                    }
                    if active_tools:
                        config_args["tools"] = active_tools

                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(**config_args)
                    )

                    raw_text = (response.text or "").strip()

                    if raw_text.startswith("```"):
                        raw_text = re.sub(r"^```[a-zA-Z]*\n", "", raw_text)
                        raw_text = re.sub(r"\n```$", "", raw_text)

                    json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
                    if json_match:
                        raw_text = json_match.group(1)

                    result_json = json.loads(raw_text)

                    save_project_memory(
                        project_name=project_name,
                        new_summary=result_json.get("architecture_summary", ""),
                        new_invariants=result_json.get("system_invariants", []),
                        new_personas=result_json.get("involved_personas", []),
                        new_search_learnings=result_json.get("external_search_learnings", [])
                    )

                    return result_json

                except Exception as e:
                    err_str = f"[{model_name} / Key {self.rotator.current_idx + 1}]: {str(e)}"
                    errors_logged.append(err_str)

                    if any(x in str(e) for x in ["503", "UNAVAILABLE", "404", "NOT_FOUND"]):
                        continue

                    if any(x in str(e) for x in ["429", "RESOURCE_EXHAUSTED"]):
                        self.rotator.rotate()
                        time.sleep(1.0)
                        break

                    raise e

        raise RuntimeError("Generation failed across all candidate models. Details:\n" + "\n".join(errors_logged))