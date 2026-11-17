"""
NovaWorks Technologies - Demo Accounts Seeder
Populates the 10 fictional demo accounts specified in the Challenge Pack:
- 1 Admin
- 3 Project Managers (PM01, PM02, PM03)
- 6 Developer Agents (DEV01 - DEV06)
Password for all demo accounts: 'Demo123!'
Re-running does not duplicate accounts (upsert / check on email).
"""

from database import init_db, get_connection, hash_password

DEMO_ACCOUNTS = [
    {
        "id": "ADMIN",
        "name": "Admin",
        "email": "admin@novaworks.example",
        "role": "ADMIN",
        "specialization": "Administrator",
        "skills": "Company overview, transcript creation",
        "password": "Demo123!"
    },
    {
        "id": "PM01",
        "name": "Ayesha Khan",
        "email": "ayesha@novaworks.example",
        "role": "MANAGER",
        "specialization": "Manager / Web PM",
        "skills": "Web projects, client coordination",
        "password": "Demo123!"
    },
    {
        "id": "PM02",
        "name": "Bilal Ahmed",
        "email": "bilal@novaworks.example",
        "role": "MANAGER",
        "specialization": "Manager / Mobile PM",
        "skills": "Mobile projects, delivery planning",
        "password": "Demo123!"
    },
    {
        "id": "PM03",
        "name": "Hina Malik",
        "email": "hina@novaworks.example",
        "role": "MANAGER",
        "specialization": "Manager / AI PM",
        "skills": "AI projects, requirement review",
        "password": "Demo123!"
    },
    {
        "id": "DEV01",
        "name": "Ali Raza",
        "email": "ali@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / Full-Stack",
        "skills": "React, frontend integration",
        "password": "Demo123!"
    },
    {
        "id": "DEV02",
        "name": "Hamza Shah",
        "email": "hamza@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / Full-Stack",
        "skills": "Node.js, databases, APIs",
        "password": "Demo123!"
    },
    {
        "id": "DEV03",
        "name": "Sara Noor",
        "email": "sara@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / App Developer",
        "skills": "Flutter, mobile UI",
        "password": "Demo123!"
    },
    {
        "id": "DEV04",
        "name": "Usman Tariq",
        "email": "usman@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / App Developer",
        "skills": "Flutter, integration, testing",
        "password": "Demo123!"
    },
    {
        "id": "DEV05",
        "name": "Zain Abbas",
        "email": "zain@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / AI Developer",
        "skills": "LLMs, extraction, prompts",
        "password": "Demo123!"
    },
    {
        "id": "DEV06",
        "name": "Maryam Asif",
        "email": "maryam@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / AI Developer",
        "skills": "Retrieval, document processing",
        "password": "Demo123!"
    }
]

def seed_demo_users():
    """Seeds the 10 demo users if not present or updates their info."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    inserted_or_updated = 0
    for acc in DEMO_ACCOUNTS:
        pwd_hash = hash_password(acc["password"])
        cur.execute("""
        INSERT INTO users (id, name, email, password_hash, role, specialization, skills)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            password_hash=excluded.password_hash,
            role=excluded.role,
            specialization=excluded.specialization,
            skills=excluded.skills
        """, (
            acc["id"],
            acc["name"],
            acc["email"],
            pwd_hash,
            acc["role"],
            acc["specialization"],
            acc["skills"]
        ))
        inserted_or_updated += 1

    conn.commit()
    conn.close()
    print(f"[Seeder] Successfully seeded/verified {inserted_or_updated} demo accounts.")

if __name__ == "__main__":
    seed_demo_users()
