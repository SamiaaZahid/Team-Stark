"""
NovaWorks Technologies - AI Project Manager (Meeting to Execution)
The Infinity Hack '26 MVP
Built with Streamlit & SQLite
"""

import streamlit as st
import os
import time
from datetime import datetime
from database import (
    init_db,
    authenticate_user,
    get_all_users,
    get_projects_for_user,
    get_tasks_for_project,
    get_project_by_id_scoped,
    get_agent_my_tasks,
    get_stats_overview,
    save_extracted_projects,
    clear_all_projects_and_tasks
)
from seeder import seed_demo_users, DEMO_ACCOUNTS
from ai_extractor import extract_projects

# Page configuration
st.set_page_config(
    page_title="NovaWorks CRM | AI Project Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished, professional UI
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .project-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.1s ease;
    }
    .project-card:hover {
        border-color: #3B82F6;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        margin-right: 0.5rem;
    }
    .badge-admin { background-color: #FEE2E2; color: #991B1B; }
    .badge-manager { background-color: #FEF3C7; color: #92400E; }
    .badge-agent { background-color: #DBEAFE; color: #1E40AF; }
    .task-box {
        background-color: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 6px 6px 0;
    }
</style>
""", unsafe_allow_html=True)

# Ensure database is initialized & demo accounts seeded
if "db_initialized" not in st.session_state:
    init_db()
    seed_demo_users()
    st.session_state["db_initialized"] = True

# Session State for logged-in user
if "user" not in st.session_state:
    st.session_state["user"] = None

if "selected_project_id" not in st.session_state:
    st.session_state["selected_project_id"] = None

# ==========================================
# AUTHENTICATION SCREEN
# ==========================================
def render_login():
    st.markdown("<div style='text-align: center; margin-top: 2rem; margin-bottom: 2rem;'>", unsafe_allow_html=True)
    st.markdown("<h1>⚡ NovaWorks Technologies</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B;'>The Infinity Hack '26 &mdash; AI Project Manager: Meeting to Execution</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("### 🔐 Sign In")
        st.caption("Sign in with any of the 10 seeded demo accounts. Default password: `Demo123!`")

        # Quick selector for hackathon judges & testers
        st.markdown("#### ⚡ 1-Click Quick Demo Login (Judges Shortcut)")
        quick_user_options = {
            f"[{acc['role']}] {acc['name']} ({acc['email']})": acc for acc in DEMO_ACCOUNTS
        }
        selected_quick_label = st.selectbox(
            "Select Demo Account to fill credentials:",
            ["-- Choose Demo Account --"] + list(quick_user_options.keys()),
            key="quick_login_select"
        )

        default_email = ""
        default_pwd = ""
        if selected_quick_label != "-- Choose Demo Account --":
            acc = quick_user_options[selected_quick_label]
            default_email = acc["email"]
            default_pwd = acc["password"]

        with st.form("login_form"):
            email_input = st.text_input("Demo Email", value=default_email, placeholder="e.g. admin@novaworks.example")
            password_input = st.text_input("Password", value=default_pwd, type="password", placeholder="Demo123!")
            submit_btn = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submit_btn:
                if not email_input.strip() or not password_input.strip():
                    st.error("Please enter both email and password.")
                else:
                    user_session = authenticate_user(email_input, password_input)
                    if user_session:
                        st.session_state["user"] = user_session
                        st.session_state["selected_project_id"] = None
                        st.success(f"Welcome back, {user_session['name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please verify your demo email and password.")

        with st.expander("📋 View Seeded Demo Accounts Table"):
            st.table([
                {
                    "Role": u["role"],
                    "Name": u["name"],
                    "Email": u["email"],
                    "Password": u["password"],
                    "Specialization": u["specialization"]
                }
                for u in DEMO_ACCOUNTS
            ])

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
def render_sidebar():
    user = st.session_state["user"]
    st.sidebar.markdown(f"### ⚡ NovaWorks CRM")
    
    role_badge_class = f"badge-{user['role'].lower()}"
    st.sidebar.markdown(
        f"<div><span class='badge {role_badge_class}'>{user['role']}</span> <b>{user['name']}</b></div>",
        unsafe_allow_html=True
    )
    st.sidebar.caption(f"{user['email']} • {user.get('specialization', '')}")
    st.sidebar.divider()

    # Dynamic Navigation options based on role
    nav_options = []
    if user["role"] == "ADMIN":
        nav_options = ["📊 Projects Dashboard", "🤖 Create from Transcript", "👥 Team Directory"]
    elif user["role"] == "MANAGER":
        nav_options = ["📁 My Managed Projects", "👥 Team Directory"]
    elif user["role"] == "AGENT":
        nav_options = ["✅ My Assigned Tasks", "📁 Related Projects", "👥 Team Directory"]

    choice = st.sidebar.radio("Navigation", nav_options, key="nav_choice")

    st.sidebar.divider()
    
    # Quick Switch Account feature for judging
    st.sidebar.markdown("**Switch Demo User:**")
    switch_options = {f"[{u['role'][:3]}] {u['name']}": u for u in DEMO_ACCOUNTS}
    current_label = next((k for k, v in switch_options.items() if v["id"] == user["id"]), None)
    new_user_label = st.sidebar.selectbox("Quick Switch:", list(switch_options.keys()), index=list(switch_options.keys()).index(current_label) if current_label else 0)
    if new_user_label and switch_options[new_user_label]["id"] != user["id"]:
        switched_user = switch_options[new_user_label]
        auth_session = authenticate_user(switched_user["email"], switched_user["password"])
        st.session_state["user"] = auth_session
        st.session_state["selected_project_id"] = None
        st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state["user"] = None
        st.session_state["selected_project_id"] = None
        st.rerun()

    return choice

# ==========================================
# ADMIN: CREATE FROM TRANSCRIPT
# ==========================================
def render_transcript_creator():
    st.markdown("<div class='main-header'>🤖 Create Projects & Tasks from Transcript</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Paste a meeting transcript to automatically extract client projects, task assignments, deadlines, and effort hours.</div>", unsafe_allow_html=True)

    # Transcript sample loader
    sample_path = os.path.join(os.path.dirname(__file__), "sample_transcript.txt")
    sample_text = ""
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as f:
            sample_text = f.read()

    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown("#### ⚡ Quick Actions")
        if st.button("📄 Load Official Transcript", use_container_width=True):
            st.session_state["transcript_input"] = sample_text
            st.rerun()
            
        if st.button("🧪 Load Modified Test Transcript", use_container_width=True, help="Suggested test from Challenge Pack: changes QuickServe integration to 12h, deadline 23 Oct"):
            modified_text = sample_text.replace(
                "Usman owns Mobile integration and testing: 10 hours, 22 October.",
                "Usman owns Mobile integration and testing: 12 hours, 23 October."
            ).replace(
                "Mobile integration and testing, Usman, 10 hours, 22 October.",
                "Mobile integration and testing, Usman, 12 hours, 23 October."
            )
            st.session_state["transcript_input"] = modified_text
            st.rerun()

        if st.button("🗑️ Reset Projects & Tasks", use_container_width=True, help="Clear database projects/tasks to test extraction again."):
            clear_all_projects_and_tasks()
            st.session_state["selected_project_id"] = None
            st.success("Database cleared. Ready for fresh transcript conversion.")
            st.rerun()

        st.markdown("---")
        st.markdown("#### ⚙️ AI Engine Settings")
        api_mode = st.radio("AI Provider:", ["Built-in Intelligent NLP Engine", "Google Gemini API", "OpenAI API"], index=0)
        gemini_key = ""
        openai_key = ""
        if api_mode == "Google Gemini API":
            gemini_key = st.text_input("Gemini API Key", value=os.environ.get("GEMINI_API_KEY", ""), type="password")
            st.caption("Leave empty or invalid to use Built-in Intelligent NLP Engine automatically.")
        elif api_mode == "OpenAI API":
            openai_key = st.text_input("OpenAI API Key", value=os.environ.get("OPENAI_API_KEY", ""), type="password")

    with col1:
        current_val = st.session_state.get("transcript_input", "")
        transcript_content = st.text_area(
            "Paste Meeting Transcript:",
            value=current_val,
            height=380,
            placeholder="Paste meeting transcript here...",
            key="transcript_area"
        )

        create_disabled = st.session_state.get("is_processing", False)
        
        if st.button("🚀 Create from Transcript", type="primary", use_container_width=True, disabled=create_disabled):
            if not transcript_content.strip():
                st.error("Please paste or load a meeting transcript before creating.")
            else:
                st.session_state["is_processing"] = True
                with st.spinner("AI is analyzing transcript, resolving assignees, and extracting projects..."):
                    time.sleep(0.5)  # brief visual feedback
                    users = get_all_users()
                    extracted_data, engine_used = extract_projects(
                        transcript_content,
                        users,
                        gemini_api_key=gemini_key if api_mode == "Google Gemini API" else None,
                        openai_api_key=openai_key if api_mode == "OpenAI API" else None
                    )

                    if not extracted_data or "projects" not in extracted_data:
                        st.error(f"AI Extraction Failed: {engine_used}. Unresolved fields or invalid format.")
                        st.session_state["is_processing"] = False
                    else:
                        # Transactional save with complete validation
                        projects = extracted_data["projects"]
                        success, message, p_count, t_count = save_extracted_projects(projects)
                        st.session_state["is_processing"] = False

                        if success:
                            st.success(f"🎉 Success! {message}")
                            st.info(f"Engine Used: **{engine_used}**")
                            
                            # Display extraction summary table
                            summary_rows = []
                            for p in projects:
                                mgr = next((u["name"] for u in users if u["id"] == p["managerId"]), p["managerId"])
                                for t in p["tasks"]:
                                    assignee = next((u["name"] for u in users if u["id"] == t["assigneeId"]), t["assigneeId"])
                                    summary_rows.append({
                                        "Project": p["name"],
                                        "Client": p["clientName"],
                                        "Manager": mgr,
                                        "Project Deadline": p["deadline"],
                                        "Task Title": t["title"],
                                        "Task Assignee": assignee,
                                        "Task Deadline": t["deadline"],
                                        "Hours": t["estimatedHours"]
                                    })
                            st.dataframe(summary_rows, use_container_width=True)
                        else:
                            st.error(f"Validation / Transaction Error: {message}")
                            st.warning("All-or-nothing protection: No partially created projects were saved.")

# ==========================================
# PROJECTS LIST & PROJECT DETAIL VIEW
# ==========================================
def render_projects_dashboard(role_title: str = "Projects Dashboard"):
    user = st.session_state["user"]
    st.markdown(f"<div class='main-header'>📁 {role_title}</div>", unsafe_allow_html=True)
    
    projects = get_projects_for_user(user)

    if not projects:
        st.info("No projects found for your account. If you are an Admin, use 'Create from Transcript' to seed projects.")
        return

    # Check if a project detail is selected
    selected_id = st.session_state.get("selected_project_id")
    if selected_id:
        render_project_detail(selected_id)
        return

    # Overview Metrics
    total_proj = len(projects)
    total_tasks = sum(p["task_count"] for p in projects)
    total_hrs = sum(p["total_hours"] for p in projects)

    m1, m2, m3 = st.columns(3)
    m1.metric("Visible Projects", total_proj)
    m2.metric("Total Tasks", total_tasks)
    m3.metric("Total Estimated Effort", f"{total_hrs:g} hrs")
    st.write("")

    # Project Cards
    cols = st.columns(3)
    for idx, p in enumerate(projects):
        with cols[idx % 3]:
            st.markdown(f"""
            <div class='project-card'>
                <h4 style='margin: 0 0 0.5rem 0; color: #1E293B;'>{p['name']}</h4>
                <p style='color: #64748B; font-size: 0.85rem; margin-bottom: 0.5rem;'>
                    <b>Client:</b> {p['client_name']}<br>
                    <b>Manager:</b> {p.get('manager_name', p['manager_id'])}<br>
                    <b>Deadline:</b> 📅 {p['deadline']}
                </p>
                <div style='margin-bottom: 0.75rem;'>
                    <span class='badge' style='background: #EEF2F6; color: #334155;'>📌 {p['task_count']} Tasks</span>
                    <span class='badge' style='background: #E0F2FE; color: #0369A1;'>⏱️ {p['total_hours']:g} Hours</span>
                </div>
                <p style='font-size: 0.8rem; color: #475569;'>{p.get('description', '')[:120]}...</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"🔍 View Details & Tasks", key=f"view_proj_{p['id']}", use_container_width=True):
                st.session_state["selected_project_id"] = p["id"]
                st.rerun()

def render_project_detail(project_id: str):
    user = st.session_state["user"]
    res = get_project_by_id_scoped(user, project_id)
    
    if not res:
        st.error("Access Denied: You do not have permission to view this project.")
        if st.button("⬅️ Back to Projects"):
            st.session_state["selected_project_id"] = None
            st.rerun()
        return

    project, tasks = res

    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state["selected_project_id"] = None
            st.rerun()
    with col_title:
        st.markdown(f"### {project['name']} <span style='font-size: 1rem; color: #64748B;'>({project['client_name']})</span>", unsafe_allow_html=True)

    # Details overview
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Project Manager", project.get("manager_name", project["manager_id"]))
    c2.metric("Project Deadline", project["deadline"])
    c3.metric("Tasks (Scoped)", len(tasks))
    c4.metric("Total Hours", f"{sum(t['estimated_hours'] for t in tasks):g} hrs")

    st.markdown(f"**Project Scope / Description:**")
    st.info(project.get("description", "No description provided."))

    st.markdown("#### 📋 Tasks Breakdown")
    if not tasks:
        st.warning("No tasks found or assigned to you in this project.")
    else:
        for t in tasks:
            st.markdown(f"""
            <div class='task-box'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h4 style='margin: 0; color: #0F172A;'>{t['title']}</h4>
                    <div>
                        <span class='badge' style='background: #EFF6FF; color: #1D4ED8;'>👤 {t.get('assignee_name', t['assignee_id'])}</span>
                        <span class='badge' style='background: #FEF3C7; color: #B45309;'>📅 Due: {t['deadline']}</span>
                        <span class='badge' style='background: #DCFCE7; color: #15803D;'>⏱️ {t['estimated_hours']:g} hrs</span>
                    </div>
                </div>
                <p style='margin: 0.4rem 0 0 0; font-size: 0.85rem; color: #475569;'>{t.get('description', '')}</p>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# AGENT: MY ASSIGNED TASKS VIEW
# ==========================================
def render_agent_my_tasks():
    user = st.session_state["user"]
    st.markdown("<div class='main-header'>✅ My Assigned Tasks</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Tasks specifically assigned to you across all projects.</div>", unsafe_allow_html=True)

    tasks = get_agent_my_tasks(user)

    if not tasks:
        st.info("You have no assigned tasks yet.")
        return

    total_hours = sum(t["estimated_hours"] for t in tasks)
    c1, c2 = st.columns(2)
    c1.metric("My Total Tasks", len(tasks))
    c2.metric("My Total Allocated Hours", f"{total_hours:g} hrs")
    st.write("")

    for t in tasks:
        st.markdown(f"""
        <div class='task-box'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <h4 style='margin: 0; color: #0F172A;'>{t['title']}</h4>
                    <span style='font-size: 0.8rem; color: #64748B;'>Project: <b>{t['project_name']}</b> ({t['client_name']}) • Manager: {t['manager_name']}</span>
                </div>
                <div>
                    <span class='badge' style='background: #FEF3C7; color: #B45309;'>📅 Due: {t['deadline']}</span>
                    <span class='badge' style='background: #DCFCE7; color: #15803D;'>⏱️ {t['estimated_hours']:g} hrs</span>
                </div>
            </div>
            <p style='margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #475569;'>{t.get('description', '')}</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# READ-ONLY TEAM DIRECTORY
# ==========================================
def render_team_directory():
    st.markdown("<div class='main-header'>👥 Team Directory</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Read-only directory of NovaWorks Technologies employees.</div>", unsafe_allow_html=True)

    users = get_all_users()
    
    # Filter controls
    role_filter = st.selectbox("Filter by Role:", ["All Roles", "ADMIN", "MANAGER", "AGENT"])
    if role_filter != "All Roles":
        users = [u for u in users if u["role"] == role_filter]

    cols = st.columns(2)
    for idx, u in enumerate(users):
        with cols[idx % 2]:
            role_badge = f"badge-{u['role'].lower()}"
            st.markdown(f"""
            <div class='project-card'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h4 style='margin: 0; color: #1E293B;'>{u['name']}</h4>
                    <span class='badge {role_badge}'>{u['role']}</span>
                </div>
                <p style='color: #64748B; font-size: 0.85rem; margin: 0.4rem 0;'>
                    <b>ID:</b> <code>{u['id']}</code> | <b>Email:</b> {u['email']}<br>
                    <b>Role / Spec:</b> {u.get('specialization', 'N/A')}
                </p>
                <div style='background: #F8FAFC; padding: 0.5rem; border-radius: 4px; font-size: 0.8rem;'>
                    <b>Skills:</b> {u.get('skills', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# MAIN ROUTING
# ==========================================
def main():
    if not st.session_state["user"]:
        render_login()
    else:
        page = render_sidebar()
        user = st.session_state["user"]

        if page == "🤖 Create from Transcript":
            if user["role"] == "ADMIN":
                render_transcript_creator()
            else:
                st.error("Access Restricted: Only Administrators can create projects from transcripts.")
        elif page == "📊 Projects Dashboard":
            render_projects_dashboard("All Projects Dashboard")
        elif page == "📁 My Managed Projects":
            render_projects_dashboard("My Managed Projects")
        elif page == "📁 Related Projects":
            render_projects_dashboard("My Related Projects")
        elif page == "✅ My Assigned Tasks":
            render_agent_my_tasks()
        elif page == "👥 Team Directory":
            render_team_directory()

if __name__ == "__main__":
    main()
