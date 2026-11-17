"""
NovaWorks Technologies - Project Management CRM
Database Module (SQLite) with strict Role-Based Access Control (RBAC) and Transactional Integrity.
"""

import sqlite3
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "novaworks.db")
SALT = "novaworks_infinity_hack_2026"

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    return hashlib.sha256(f"{SALT}:{password}".encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return hash_password(plain_password) == hashed_password

def get_connection(db_file: str = DB_PATH) -> sqlite3.Connection:
    """Create a sqlite3 connection with Row factory and Foreign Keys enabled."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_file: str = DB_PATH) -> None:
    """Initialize database schema if tables do not exist."""
    conn = get_connection(db_file)
    cur = conn.cursor()
    
    # 1. Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('ADMIN', 'MANAGER', 'AGENT')),
        specialization TEXT,
        skills TEXT
    );
    """)

    # 2. Projects table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        client_name TEXT NOT NULL,
        description TEXT,
        manager_id TEXT NOT NULL,
        deadline TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (manager_id) REFERENCES users(id)
    );
    """)

    # 3. Tasks table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        assignee_id TEXT NOT NULL,
        deadline TEXT NOT NULL,
        estimated_hours REAL NOT NULL CHECK(estimated_hours > 0),
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (assignee_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    conn.close()

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user record by email."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user record by id (excludes password_hash for safety)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role, specialization, skills FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_users() -> List[Dict[str, Any]]:
    """Get all team directory users (no passwords)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, role, specialization, skills FROM users ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate credentials and return user session dict if valid."""
    user = get_user_by_email(email)
    if not user:
        return None
    if verify_password(password, user["password_hash"]):
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "specialization": user["specialization"],
            "skills": user["skills"]
        }
    return None

# ==========================================
# Strict Role-Based Access Control Functions
# ==========================================

def get_projects_for_user(current_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Role-based visibility for projects:
    - ADMIN -> all projects
    - MANAGER -> projects where manager_id == currentUser.id
    - AGENT -> distinct projects containing tasks assigned to currentUser.id
    """
    role = current_user.get("role")
    user_id = current_user.get("id")
    conn = get_connection()
    cur = conn.cursor()

    if role == "ADMIN":
        query = """
        SELECT p.*, u.name AS manager_name,
               (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) AS task_count,
               (SELECT COALESCE(SUM(t.estimated_hours), 0) FROM tasks t WHERE t.project_id = p.id) AS total_hours
        FROM projects p
        LEFT JOIN users u ON p.manager_id = u.id
        ORDER BY p.deadline ASC
        """
        cur.execute(query)
    elif role == "MANAGER":
        query = """
        SELECT p.*, u.name AS manager_name,
               (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) AS task_count,
               (SELECT COALESCE(SUM(t.estimated_hours), 0) FROM tasks t WHERE t.project_id = p.id) AS total_hours
        FROM projects p
        LEFT JOIN users u ON p.manager_id = u.id
        WHERE p.manager_id = ?
        ORDER BY p.deadline ASC
        """
        cur.execute(query, (user_id,))
    elif role == "AGENT":
        query = """
        SELECT DISTINCT p.*, u.name AS manager_name,
               (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.assignee_id = ?) AS task_count,
               (SELECT COALESCE(SUM(t.estimated_hours), 0) FROM tasks t WHERE t.project_id = p.id AND t.assignee_id = ?) AS total_hours
        FROM projects p
        INNER JOIN tasks t ON t.project_id = p.id
        LEFT JOIN users u ON p.manager_id = u.id
        WHERE t.assignee_id = ?
        ORDER BY p.deadline ASC
        """
        cur.execute(query, (user_id, user_id, user_id))
    else:
        conn.close()
        return []

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_tasks_for_project(current_user: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
    """
    Role-based visibility for tasks within a project:
    - ADMIN -> all tasks in project_id
    - MANAGER -> all tasks in project_id ONLY IF they manage project_id
    - AGENT -> ONLY tasks assigned to currentUser.id in project_id (never other agents' tasks)
    """
    role = current_user.get("role")
    user_id = current_user.get("id")
    conn = get_connection()
    cur = conn.cursor()

    if role == "ADMIN":
        query = """
        SELECT t.*, u.name AS assignee_name, u.specialization AS assignee_specialization
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        WHERE t.project_id = ?
        ORDER BY t.deadline ASC
        """
        cur.execute(query, (project_id,))
    elif role == "MANAGER":
        # Check if this manager owns this project
        cur.execute("SELECT manager_id FROM projects WHERE id = ?", (project_id,))
        proj = cur.fetchone()
        if not proj or proj["manager_id"] != user_id:
            conn.close()
            return []  # Rejected
        query = """
        SELECT t.*, u.name AS assignee_name, u.specialization AS assignee_specialization
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        WHERE t.project_id = ?
        ORDER BY t.deadline ASC
        """
        cur.execute(query, (project_id,))
    elif role == "AGENT":
        query = """
        SELECT t.*, u.name AS assignee_name, u.specialization AS assignee_specialization
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        WHERE t.project_id = ? AND t.assignee_id = ?
        ORDER BY t.deadline ASC
        """
        cur.execute(query, (project_id, user_id))
    else:
        conn.close()
        return []

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_project_by_id_scoped(current_user: Dict[str, Any], project_id: str) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """
    Fetch a project and its scoped tasks.
    Rejects and returns None if the project is outside get_projects_for_user(current_user).
    """
    permitted_projects = get_projects_for_user(current_user)
    matching_project = next((p for p in permitted_projects if p["id"] == project_id), None)
    if not matching_project:
        return None
    tasks = get_tasks_for_project(current_user, project_id)
    return (matching_project, tasks)

def get_agent_my_tasks(current_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Direct 'My Tasks' view for AGENTs: returns only tasks assigned to the current agent across all projects.
    """
    if current_user.get("role") != "AGENT":
        return []
    user_id = current_user.get("id")
    conn = get_connection()
    cur = conn.cursor()
    query = """
    SELECT t.*, p.name AS project_name, p.client_name, u.name AS manager_name
    FROM tasks t
    INNER JOIN projects p ON t.project_id = p.id
    LEFT JOIN users u ON p.manager_id = u.id
    WHERE t.assignee_id = ?
    ORDER BY t.deadline ASC
    """
    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats_overview() -> Dict[str, Any]:
    """Admin summary counts."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM projects")
    num_projects = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tasks")
    num_tasks = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(estimated_hours), 0) FROM tasks")
    total_hours = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users")
    num_users = cur.fetchone()[0]
    conn.close()
    return {
        "projects_count": num_projects,
        "tasks_count": num_tasks,
        "total_hours": total_hours,
        "users_count": num_users
    }

# ========================================================
# All-or-Nothing Transactional Save for Extracted Projects
# ========================================================

def save_extracted_projects(projects_data: List[Dict[str, Any]]) -> Tuple[bool, str, int, int]:
    """
    Save projects and tasks extracted from transcript in an all-or-nothing database transaction.
    Performs complete schema and logic validation:
    - Validates project fields (name, client, managerId, deadline)
    - Validates manager belongs to existing MANAGER user
    - Validates each task (title, assigneeId, deadline, positive estimatedHours)
    - Validates assignee belongs to existing AGENT user
    - Validates task deadline <= project deadline
    If any check fails, rolls back and returns (False, error_msg, 0, 0).
    """
    if not projects_data:
        return False, "No project data supplied to save.", 0, 0

    conn = get_connection()
    cur = conn.cursor()

    try:
        # 1. Fetch valid users to validate roles
        cur.execute("SELECT id, role FROM users")
        user_rows = cur.fetchall()
        user_role_map = {row["id"]: row["role"] for row in user_rows}

        total_projects = 0
        total_tasks = 0
        now_str = datetime.now().isoformat()

        # Begin transaction
        cur.execute("BEGIN TRANSACTION;")

        for p_idx, p in enumerate(projects_data):
            p_name = p.get("name", "").strip()
            client_name = p.get("clientName", "").strip()
            p_desc = p.get("description", "").strip()
            manager_id = p.get("managerId", "").strip()
            p_deadline = p.get("deadline", "").strip()
            tasks = p.get("tasks", [])

            if not p_name:
                raise ValueError(f"Project #{p_idx+1} is missing a name.")
            if not client_name:
                raise ValueError(f"Project '{p_name}' is missing a client name.")
            if not manager_id:
                raise ValueError(f"Project '{p_name}' is missing a manager ID.")
            if manager_id not in user_role_map or user_role_map[manager_id] != "MANAGER":
                raise ValueError(f"Project '{p_name}' managerId '{manager_id}' does not belong to an existing MANAGER.")
            if not p_deadline:
                raise ValueError(f"Project '{p_name}' is missing a valid deadline (YYYY-MM-DD).")
            
            try:
                p_date = datetime.strptime(p_deadline, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Project '{p_name}' deadline '{p_deadline}' is not in YYYY-MM-DD format.")

            # Generate project ID e.g. PRJ-01, PRJ-02 or slug
            project_id = p.get("id")
            if not project_id:
                cur.execute("SELECT COUNT(*) FROM projects")
                cnt = cur.fetchone()[0]
                project_id = f"PRJ-{cnt + p_idx + 1:02d}"

            # Insert project (or replace if ID matches)
            cur.execute("""
            INSERT INTO projects (id, name, client_name, description, manager_id, deadline, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, p_name, client_name, p_desc, manager_id, p_deadline, now_str))
            total_projects += 1

            for t_idx, t in enumerate(tasks):
                t_title = t.get("title", "").strip()
                t_desc = t.get("description", "").strip()
                assignee_id = t.get("assigneeId", "").strip()
                t_deadline = t.get("deadline", "").strip()
                estimated_hours = t.get("estimatedHours")

                if not t_title:
                    raise ValueError(f"Project '{p_name}', Task #{t_idx+1} is missing a title.")
                if not assignee_id:
                    raise ValueError(f"Task '{t_title}' in '{p_name}' is missing an assignee.")
                if assignee_id not in user_role_map or user_role_map[assignee_id] != "AGENT":
                    raise ValueError(f"Task '{t_title}' assigneeId '{assignee_id}' does not belong to an existing developer AGENT.")
                if estimated_hours is None or float(estimated_hours) <= 0:
                    raise ValueError(f"Task '{t_title}' must have positive estimated hours (got {estimated_hours}).")
                if not t_deadline:
                    raise ValueError(f"Task '{t_title}' is missing a valid deadline (YYYY-MM-DD).")
                
                try:
                    t_date = datetime.strptime(t_deadline, "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError(f"Task '{t_title}' deadline '{t_deadline}' is not in YYYY-MM-DD format.")

                if t_date > p_date:
                    raise ValueError(f"Task '{t_title}' deadline ({t_deadline}) cannot exceed Project '{p_name}' deadline ({p_deadline}).")

                task_id = t.get("id")
                if not task_id:
                    task_id = f"{project_id}-T{t_idx+1:02d}"

                cur.execute("""
                INSERT INTO tasks (id, project_id, title, description, assignee_id, deadline, estimated_hours, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (task_id, project_id, t_title, t_desc, assignee_id, t_deadline, float(estimated_hours), now_str))
                total_tasks += 1

        conn.commit()
        conn.close()
        return True, f"Successfully created {total_projects} projects and {total_tasks} tasks.", total_projects, total_tasks

    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e), 0, 0

def clear_all_projects_and_tasks() -> None:
    """Utility to reset all projects and tasks for demo reset."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks")
    cur.execute("DELETE FROM projects")
    conn.commit()
    conn.close()
