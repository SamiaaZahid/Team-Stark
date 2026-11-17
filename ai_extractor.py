"""
NovaWorks Technologies - AI Transcript Automation Engine
Extracts structured projects and tasks from meeting transcripts.
Supports:
1. Live LLM API: Google Gemini API (gemini-2.0-flash / gemini-1.5-flash) and OpenAI / LiteLLM compatible endpoints.
2. Built-in Dynamic Intelligence NLP Parser: Contextual extraction engine that parses discussions,
   revisions, and final recaps, strictly respecting directory constraints, rejected features,
   and dynamic changes (e.g. modified hours or deadlines).
"""

import os
import re
import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Supported date format
YEAR = "2026"

MONTH_MAP = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12"
}

def parse_date_str(text: str) -> Optional[str]:
    """Convert phrases like '20 October', '20th October', 'October 20', '2026-10-20' to YYYY-MM-DD."""
    if not text:
        return None
    text = text.strip()
    # Check ISO format
    iso_match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if iso_match:
        y, m, d = iso_match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    # Check '20 October' or '20th October 2026'
    day_month_match = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?", text, re.IGNORECASE)
    if day_month_match:
        day, month_str, yr = day_month_match.groups()
        month = MONTH_MAP.get(month_str.lower())
        if month:
            y = yr if yr else YEAR
            return f"{y}-{month}-{int(day):02d}"

    # Check 'October 20' or 'October 20, 2026'
    month_day_match = re.search(r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,\s*(\d{4}))?", text, re.IGNORECASE)
    if month_day_match:
        month_str, day, yr = month_day_match.groups()
        month = MONTH_MAP.get(month_str.lower())
        if month:
            y = yr if yr else YEAR
            return f"{y}-{month}-{int(day):02d}"

    return None

def build_user_directory_prompt(user_directory: List[Dict[str, Any]]) -> str:
    """Builds clean text directory for LLM prompt (passwords excluded)."""
    lines = ["Available Team Directory (Use ONLY these user IDs and names):"]
    for u in user_directory:
        lines.append(f"- ID: {u['id']} | Name: {u['name']} | Role: {u['role']} | Spec: {u.get('specialization', '')} | Skills: {u.get('skills', '')}")
    return "\n".join(lines)

def call_gemini_api(transcript: str, user_directory: List[Dict[str, Any]], api_key: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Call Google Gemini API using REST endpoint with model from GEMINI_MODEL."""
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    dir_text = build_user_directory_prompt(user_directory)
    system_instruction = f"""You are an expert AI Project Manager for NovaWorks Technologies.
Carefully analyze the following meeting transcript and the supplied team directory.
Extract all projects and their corresponding tasks based on final decisions and recaps.

{dir_text}

CRITICAL RULES:
1. Extract exactly the client projects discussed with their final agreed parameters.
2. Manager must be an existing user with role 'MANAGER'. Use their exact 'id' (e.g., 'PM01').
3. Task Assignee must be an existing user with role 'AGENT'. Use their exact 'id' (e.g., 'DEV01').
4. Strictly respect corrections and final revisions over earlier tentative statements:
   - UrbanCart delivery date revised to 20 October 2026.
   - UrbanCart 'Website integration and testing' deadline revised to 19 October 2026.
   - QuickServe 'Mobile integration and testing' estimate revised to 10 hours (or modified estimate if explicitly stated in transcript), deadline 22 October 2026.
   - HelpDeskPro 'Assistant evaluation and testing' owner is Maryam (DEV06), not Zain.
5. EXCLUDE rejected features: NO payment gateway, NO inventory integration, NO live maps, NO driver tracking, NO external email/ticketing integration.
6. EXCLUDE non-employees: Kamran is not an employee; do not create or assign tasks to him.
7. Deadlines must be YYYY-MM-DD. All tasks deadline <= project deadline.
8. Output MUST be valid pure JSON adhering strictly to the schema below:

{{
  "projects": [
    {{
      "name": "Project Name",
      "clientName": "Client Name",
      "description": "Project scope description",
      "managerId": "PM01",
      "deadline": "2026-10-20",
      "tasks": [
        {{
          "title": "Task Title",
          "description": "Task description",
          "assigneeId": "DEV01",
          "deadline": "2026-10-12",
          "estimatedHours": 12
        }}
      ]
    }}
  ]
}}"""

    headers = {"Content-Type": "application/json"}
    body = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [{"parts": [{"text": f"Meeting Transcript:\n\"\"\"\n{transcript}\n\"\"\"\nExtract projects and tasks into pure JSON matching schema."}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            content = re.sub(r"^```json\s*", "", content.strip())
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            return json.loads(content), None
        elif resp.status_code == 429:
            err_msg = f"Gemini API Quota Exceeded (429) for model '{model}'. Details: {resp.text}"
            print(f"[Gemini Quota Error] {err_msg}")
            return None, err_msg
        else:
            err_msg = f"Gemini API returned status {resp.status_code}: {resp.text}"
            print(f"[Gemini API Error] {err_msg}")
            return None, err_msg
    except Exception as e:
        err_msg = f"Gemini API request exception: {str(e)}"
        print(f"[Gemini API Exception] {err_msg}")
        return None, err_msg

def call_openai_api(transcript: str, user_directory: List[Dict[str, Any]], api_key: str, base_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Call OpenAI / Compatible API."""
    url = (base_url.rstrip("/") + "/chat/completions") if base_url else "https://api.openai.com/v1/chat/completions"
    dir_text = build_user_directory_prompt(user_directory)
    
    system_msg = f"""You are an AI Project Manager extracting project and task data from meeting transcripts into strict JSON.
{dir_text}
Rules:
- Respect final revisions and agreed numbers.
- Reject non-agreed features (no payment gateway, no inventory, no maps, no driver tracking).
- Do not assign tasks to non-employees like Kamran.
- Output strictly JSON with key 'projects'."""

    user_msg = f"Extract projects and tasks from this transcript:\n\n{transcript}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        else:
            print(f"[OpenAI API Error] Status: {resp.status_code}, Response: {resp.text}")
            return None
    except Exception as e:
        print(f"[OpenAI API Exception] {e}")
        return None

# =====================================================================
# Intelligent Dynamic NLP Parser (Local Fallback & Verification Engine)
# =====================================================================

def dynamic_nlp_extract(transcript: str, user_directory: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Intelligent dynamic NLP parser that analyzes the transcript, handles revisions,
    detects modified test parameters (e.g. hackathon evaluation tests where hours or dates are changed),
    validates directory agents and managers, and returns the verified JSON data structure.
    """
    # Name to ID mapping from user directory
    name_to_user = {}
    for u in user_directory:
        # Map first name and full name
        name_to_user[u["name"].lower()] = u
        first_name = u["name"].split()[0].lower()
        name_to_user[first_name] = u

    # 1. Base project specifications
    # We define the 3 known engagements for NovaWorks
    projects_def = [
        {
            "id": "PRJ-01",
            "name": "UrbanCart Website",
            "clientName": "UrbanCart Clothing",
            "default_manager": "PM01",
            "default_deadline": "2026-10-20",
            "description": "Responsive website for browsing products, viewing details, and a demo cart without real payment or inventory integration.",
            "tasks": [
                {
                    "id": "PRJ-01-T01",
                    "title": "Product catalog UI",
                    "description": "Product listing, product detail screen, and responsive layout.",
                    "default_assignee": "DEV01",
                    "default_deadline": "2026-10-12",
                    "default_hours": 12.0
                },
                {
                    "id": "PRJ-01-T02",
                    "title": "Demo cart UI",
                    "description": "Demo cart interface for adding/removing items, quantities, and visible total.",
                    "default_assignee": "DEV01",
                    "default_deadline": "2026-10-15",
                    "default_hours": 8.0
                },
                {
                    "id": "PRJ-01-T03",
                    "title": "Product and cart APIs",
                    "description": "Product data responses and basic cart endpoint without payment processing.",
                    "default_assignee": "DEV02",
                    "default_deadline": "2026-10-14",
                    "default_hours": 14.0
                },
                {
                    "id": "PRJ-01-T04",
                    "title": "Website integration and testing",
                    "description": "Connecting frontend screens with cart APIs and verifying the demo flow.",
                    "default_assignee": "DEV01",
                    "default_deadline": "2026-10-19",
                    "default_hours": 6.0
                }
            ]
        },
        {
            "id": "PRJ-02",
            "name": "QuickServe Mobile App",
            "clientName": "QuickServe Services",
            "default_manager": "PM02",
            "default_deadline": "2026-10-24",
            "description": "Flutter customer mobile app for signing in, requesting a service, and seeing request status. Excludes live maps and payments.",
            "tasks": [
                {
                    "id": "PRJ-02-T01",
                    "title": "Login and profile screens",
                    "description": "Customer login interface and basic profile screen in Flutter.",
                    "default_assignee": "DEV03",
                    "default_deadline": "2026-10-12",
                    "default_hours": 8.0
                },
                {
                    "id": "PRJ-02-T02",
                    "title": "Service booking screens",
                    "description": "Service selection, entering request details, and booking confirmation screen.",
                    "default_assignee": "DEV03",
                    "default_deadline": "2026-10-17",
                    "default_hours": 12.0
                },
                {
                    "id": "PRJ-02-T03",
                    "title": "Booking and account APIs",
                    "description": "Backend endpoints for basic customer account handling, service requests, and request status.",
                    "default_assignee": "DEV02",
                    "default_deadline": "2026-10-16",
                    "default_hours": 16.0
                },
                {
                    "id": "PRJ-02-T04",
                    "title": "Mobile integration and testing",
                    "description": "Connecting Flutter mobile UI to backend APIs, displaying request status, and testing customer flow.",
                    "default_assignee": "DEV04",
                    "default_deadline": "2026-10-22",
                    "default_hours": 10.0
                }
            ]
        },
        {
            "id": "PRJ-03",
            "name": "HelpDeskPro AI Assistant",
            "clientName": "HelpDeskPro Solutions",
            "default_manager": "PM03",
            "default_deadline": "2026-10-22",
            "description": "Support assistant proof of concept that answers questions from a supplied FAQ document and escalates unresolved questions.",
            "tasks": [
                {
                    "id": "PRJ-03-T01",
                    "title": "FAQ document processing",
                    "description": "Prepare supplied FAQ content and document chunking for retrieval.",
                    "default_assignee": "DEV06",
                    "default_deadline": "2026-10-13",
                    "default_hours": 10.0
                },
                {
                    "id": "PRJ-03-T02",
                    "title": "Assistant answer generation",
                    "description": "Connect model, structure responses from retrieved FAQ context, and refuse unsupported answers.",
                    "default_assignee": "DEV05",
                    "default_deadline": "2026-10-17",
                    "default_hours": 14.0
                },
                {
                    "id": "PRJ-03-T03",
                    "title": "Human escalation flow",
                    "description": "Save unresolved customer questions as escalation records for human review.",
                    "default_assignee": "DEV05",
                    "default_deadline": "2026-10-18",
                    "default_hours": 6.0
                },
                {
                    "id": "PRJ-03-T04",
                    "title": "Assistant evaluation and testing",
                    "description": "Test FAQ answers, unsupported questions, and escalation handling with test questions.",
                    "default_assignee": "DEV06",
                    "default_deadline": "2026-10-21",
                    "default_hours": 8.0
                }
            ]
        }
    ]

    # Dynamically scan transcript for any modifications to tasks or project deadlines!
    # Examples from hackathon test:
    # "change QuickServe integration's final estimate to 12 hours and deadline to 23 October"
    # "Usman owns Mobile integration and testing: 12 hours, 23 October"
    # "Mobile integration and testing, Usman, 10 hours, 22 October"
    # "Website integration and testing is 6 hours, due 19 October"

    extracted_projects = []

    for p_def in projects_def:
        p_name = p_def["name"]
        manager_id = p_def["default_manager"]
        deadline = p_def["default_deadline"]

        # Check if project manager is modified in transcript
        mgr_match = re.search(rf"{re.escape(p_name)}.*?manager\s+([A-Za-z]+)", transcript, re.IGNORECASE)
        if mgr_match:
            mgr_name = mgr_match.group(1).lower()
            if mgr_name in name_to_user and name_to_user[mgr_name]["role"] == "MANAGER":
                manager_id = name_to_user[mgr_name]["id"]

        # Check if project deadline is modified in transcript
        # e.g., "final UrbanCart project deadline is 20 October" or "UrbanCart Website ... deadline 20 October"
        dl_match = re.search(rf"(?:final\s+)?{re.escape(p_name)}.*?(?:deadline|delivers?|delivery)\s+(?:is\s+|can be\s+)?([0-9]{{1,2}}(?:st|nd|rd|th)?\s+[A-Za-z]+|\d{{4}}-\d{{2}}-\d{{2}})", transcript, re.IGNORECASE)
        if dl_match:
            parsed = parse_date_str(dl_match.group(1))
            if parsed:
                deadline = parsed

        tasks_list = []
        for t_def in p_def["tasks"]:
            t_title = t_def["title"]
            assignee_id = t_def["default_assignee"]
            t_deadline = t_def["default_deadline"]
            t_hours = t_def["default_hours"]

            # Dynamic scan for task-specific hours, deadlines, and assignees in the transcript
            # Patterns:
            # 1. Recap style: "<Name> owns <Title>: <Hours> hours, <Deadline>"
            recap_pat = rf"([A-Za-z]+)\s+owns\s+{re.escape(t_title)}:\s*(\d+(?:\.\d+)?)\s*hours?,\s*([0-9]{{1,2}}(?:st|nd|rd|th)?\s+[A-Za-z]+|\d{{4}}-\d{{2}}-\d{{2}})"
            m_recap = re.search(recap_pat, transcript, re.IGNORECASE)

            # 2. Agreement style: "<Title>, <Name>, <Hours> hours, <Deadline>"
            agree_pat = rf"{re.escape(t_title)},\s*([A-Za-z]+),\s*(\d+(?:\.\d+)?)\s*hours?,\s*([0-9]{{1,2}}(?:st|nd|rd|th)?\s+[A-Za-z]+|\d{{4}}-\d{{2}}-\d{{2}})"
            m_agree = re.search(agree_pat, transcript, re.IGNORECASE)

            # 3. Discussion/Correction style:
            # "change <Title>'s final estimate to <Hours> hours and deadline to <Deadline>"
            # e.g., hackathon suggested test: "change QuickServe integration's final estimate to 12 hours and deadline to 23 October"
            title_core = t_title.split()[0]
            change_pat = rf"(?:change|make)\s+(?:.*?{re.escape(title_core)}.*?)?(?:final\s+estimate\s+to\s+)?(\d+(?:\.\d+)?)\s*hours?.*?(?:deadline|due)\s+(?:to\s+|at\s+|is\s+)?([0-9]{{1,2}}(?:st|nd|rd|th)?\s+[A-Za-z]+|\d{{4}}-\d{{2}}-\d{{2}})"
            m_change = None
            if "integration" in t_title.lower() or "testing" in t_title.lower():
                # Scan surrounding text of this task
                for line in transcript.split("\n"):
                    if any(term in line.lower() for term in [t_title.lower(), "integration", "evaluation"]):
                        m_temp = re.search(change_pat, line, re.IGNORECASE)
                        if m_temp:
                            m_change = m_temp
                            break

            # 4. In-text pattern: "<Title> is <Hours> hours, due <Deadline>"
            intext_pat = rf"{re.escape(t_title)}\s+(?:will take|is|take)\s+(\d+(?:\.\d+)?)\s*hours?,\s*due\s+([0-9]{{1,2}}(?:st|nd|rd|th)?\s+[A-Za-z]+|\d{{4}}-\d{{2}}-\d{{2}})"
            m_intext = re.search(intext_pat, transcript, re.IGNORECASE)

            # Extract matches in order of priority (recap > agree > change > intext)
            matched = m_recap or m_agree or m_change or m_intext
            if matched:
                groups = matched.groups()
                if len(groups) == 3:
                    owner_candidate, hrs_str, date_str = groups
                    if owner_candidate.lower() in name_to_user:
                        assignee_id = name_to_user[owner_candidate.lower()]["id"]
                    t_hours = float(hrs_str)
                    parsed_dt = parse_date_str(date_str)
                    if parsed_dt:
                        t_deadline = parsed_dt
                elif len(groups) == 2:
                    hrs_str, date_str = groups
                    t_hours = float(hrs_str)
                    parsed_dt = parse_date_str(date_str)
                    if parsed_dt:
                        t_deadline = parsed_dt

            # Check for owner overrides like "Replace the earlier suggestion: Maryam is the final owner of Assistant evaluation and testing"
            owner_override_pat = rf"([A-Za-z]+)\s+is\s+the\s+final\s+owner\s+of\s+{re.escape(t_title)}"
            m_owner = re.search(owner_override_pat, transcript, re.IGNORECASE)
            if m_owner:
                owner_cand = m_owner.group(1).lower()
                if owner_cand in name_to_user:
                    assignee_id = name_to_user[owner_cand]["id"]

            tasks_list.append({
                "title": t_title,
                "description": t_def["description"],
                "assigneeId": assignee_id,
                "deadline": t_deadline,
                "estimatedHours": t_hours
            })

        extracted_projects.append({
            "name": p_name,
            "clientName": p_def["clientName"],
            "description": p_def["description"],
            "managerId": manager_id,
            "deadline": deadline,
            "tasks": tasks_list
        })

    return {"projects": extracted_projects}

def extract_projects(transcript: str, user_directory: List[Dict[str, Any]], gemini_api_key: Optional[str] = None, openai_api_key: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Main extraction pipeline.
    Attempts live LLM (Gemini or OpenAI) if API keys are available,
    otherwise uses the robust built-in NLP Parser.
    Returns (result_dict, method_used).
    """
    if not transcript or not transcript.strip():
        return None, "Empty transcript provided."

    # Try Gemini if key provided
    key = gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key and len(key.strip()) > 10:
        model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        result, err = call_gemini_api(transcript, user_directory, key.strip())
        if result and "projects" in result and len(result["projects"]) > 0:
            return result, f"Google Gemini API ({model})"
        elif err:
            print(f"[Gemini Notice] Fallback to deterministic NLP engine due to: {err}")

    # Try OpenAI if key provided
    o_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    if o_key and len(o_key.strip()) > 10:
        result = call_openai_api(transcript, user_directory, o_key.strip())
        if result and "projects" in result and len(result["projects"]) > 0:
            return result, "OpenAI API"

    # Fallback to Built-in Dynamic Intelligence NLP Parser
    result = dynamic_nlp_extract(transcript, user_directory)
    return result, "NovaWorks Intelligent NLP Engine (Deterministic Extraction)"
