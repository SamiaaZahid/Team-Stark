"""
NovaWorks Technologies - Verification Test Suite
Tests:
1. Seeding 10 demo accounts
2. Role-based access control (Admin, Manager, Agent)
3. AI transcript extraction & Organizer Verification Table matching (3 projects, 12 tasks, 124 hours)
4. Modified transcript test (changing QuickServe integration estimate & deadline)
5. Security / rejection tests (unauthorized access to other projects/tasks)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from database import (
    init_db, get_connection, authenticate_user,
    get_projects_for_user, get_tasks_for_project,
    get_project_by_id_scoped, get_agent_my_tasks,
    save_extracted_projects, clear_all_projects_and_tasks,
    get_all_users
)
from seeder import seed_demo_users
from ai_extractor import extract_projects

class TestNovaWorksCRM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_demo_users()

    def test_01_seeding_ten_accounts(self):
        users = get_all_users()
        self.assertEqual(len(users), 10, "Must have exactly 10 demo accounts")
        roles = [u["role"] for u in users]
        self.assertEqual(roles.count("ADMIN"), 1)
        self.assertEqual(roles.count("MANAGER"), 3)
        self.assertEqual(roles.count("AGENT"), 6)

    def test_02_authentication(self):
        # Admin auth
        admin = authenticate_user("admin@novaworks.example", "Demo123!")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "ADMIN")

        # Manager auth
        ayesha = authenticate_user("ayesha@novaworks.example", "Demo123!")
        self.assertIsNotNone(ayesha)
        self.assertEqual(ayesha["id"], "PM01")

        # Developer auth
        ali = authenticate_user("ali@novaworks.example", "Demo123!")
        self.assertIsNotNone(ali)
        self.assertEqual(ali["id"], "DEV01")

        # Invalid password
        invalid = authenticate_user("admin@novaworks.example", "WrongPassword")
        self.assertIsNone(invalid)

    def test_03_ai_extraction_organizer_match(self):
        clear_all_projects_and_tasks()
        transcript_path = os.path.join(os.path.dirname(__file__), "sample_transcript.txt")
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = f.read()

        users = get_all_users()
        extracted, method = extract_projects(transcript, users)
        self.assertIsNotNone(extracted)
        self.assertIn("projects", extracted)
        projects = extracted["projects"]

        # 3 projects
        self.assertEqual(len(projects), 3)

        # 12 tasks total
        total_tasks = sum(len(p["tasks"]) for p in projects)
        self.assertEqual(total_tasks, 12)

        # Save to database
        ok, msg, p_cnt, t_cnt = save_extracted_projects(projects)
        self.assertTrue(ok, f"Save failed: {msg}")
        self.assertEqual(p_cnt, 3)
        self.assertEqual(t_cnt, 12)

        # Check UrbanCart: Manager Ayesha (PM01), Deadline 2026-10-20, 4 tasks, 40 hours
        uc = next(p for p in projects if "UrbanCart" in p["name"])
        self.assertEqual(uc["managerId"], "PM01")
        self.assertEqual(uc["deadline"], "2026-10-20")
        uc_hours = sum(t["estimatedHours"] for t in uc["tasks"])
        self.assertEqual(uc_hours, 40.0)

        # Check QuickServe: Manager Bilal (PM02), Deadline 2026-10-24, 4 tasks, 46 hours
        qs = next(p for p in projects if "QuickServe" in p["name"])
        self.assertEqual(qs["managerId"], "PM02")
        self.assertEqual(qs["deadline"], "2026-10-24")
        qs_hours = sum(t["estimatedHours"] for t in qs["tasks"])
        self.assertEqual(qs_hours, 46.0)

        # Check HelpDeskPro: Manager Hina (PM03), Deadline 2026-10-22, 4 tasks, 38 hours
        hd = next(p for p in projects if "HelpDeskPro" in p["name"])
        self.assertEqual(hd["managerId"], "PM03")
        self.assertEqual(hd["deadline"], "2026-10-22")
        hd_hours = sum(t["estimatedHours"] for t in hd["tasks"])
        self.assertEqual(hd_hours, 38.0)

        # Total hours = 40 + 46 + 38 = 124
        total_hours = sum(t["estimatedHours"] for p in projects for t in p["tasks"])
        self.assertEqual(total_hours, 124.0)

        # Specific revised checks from organizer reference:
        # 1. UrbanCart website integration: due 19 Oct, 6 hrs, Ali
        t_uc_int = next(t for t in uc["tasks"] if "integration" in t["title"].lower())
        self.assertEqual(t_uc_int["assigneeId"], "DEV01")
        self.assertEqual(t_uc_int["deadline"], "2026-10-19")
        self.assertEqual(t_uc_int["estimatedHours"], 6.0)

        # 2. QuickServe mobile integration: due 22 Oct, 10 hrs, Usman
        t_qs_int = next(t for t in qs["tasks"] if "integration" in t["title"].lower())
        self.assertEqual(t_qs_int["assigneeId"], "DEV04")
        self.assertEqual(t_qs_int["deadline"], "2026-10-22")
        self.assertEqual(t_qs_int["estimatedHours"], 10.0)

        # 3. HelpDeskPro testing: Maryam (DEV06), 8 hrs, due 21 Oct
        t_hd_test = next(t for t in hd["tasks"] if "evaluation" in t["title"].lower())
        self.assertEqual(t_hd_test["assigneeId"], "DEV06")
        self.assertEqual(t_hd_test["deadline"], "2026-10-21")
        self.assertEqual(t_hd_test["estimatedHours"], 8.0)

    def test_04_role_based_access_control(self):
        admin = authenticate_user("admin@novaworks.example", "Demo123!")
        ayesha = authenticate_user("ayesha@novaworks.example", "Demo123!")
        bilal = authenticate_user("bilal@novaworks.example", "Demo123!")
        ali = authenticate_user("ali@novaworks.example", "Demo123!")
        hamza = authenticate_user("hamza@novaworks.example", "Demo123!")

        # Admin sees all 3 projects
        admin_projs = get_projects_for_user(admin)
        self.assertEqual(len(admin_projs), 3)

        # Ayesha (PM01) sees ONLY UrbanCart
        ayesha_projs = get_projects_for_user(ayesha)
        self.assertEqual(len(ayesha_projs), 1)
        self.assertEqual(ayesha_projs[0]["manager_id"], "PM01")
        self.assertIn("UrbanCart", ayesha_projs[0]["name"])

        # Ayesha cannot access Bilal's project tasks
        qs_id = next(p["id"] for p in admin_projs if "QuickServe" in p["name"])
        ayesha_qs_tasks = get_tasks_for_project(ayesha, qs_id)
        self.assertEqual(len(ayesha_qs_tasks), 0, "Ayesha must not be able to view tasks of Bilal's project")

        # Ali (DEV01) only has tasks in UrbanCart (3 tasks)
        ali_projs = get_projects_for_user(ali)
        self.assertEqual(len(ali_projs), 1)
        self.assertIn("UrbanCart", ali_projs[0]["name"])

        # When Ali requests tasks for UrbanCart, he sees ONLY his own 3 tasks, NOT Hamza's task!
        uc_id = next(p["id"] for p in admin_projs if "UrbanCart" in p["name"])
        ali_tasks = get_tasks_for_project(ali, uc_id)
        self.assertEqual(len(ali_tasks), 3)
        for t in ali_tasks:
            self.assertEqual(t["assignee_id"], "DEV01")

        # Hamza (DEV02) has 2 tasks across UrbanCart and QuickServe
        hamza_projs = get_projects_for_user(hamza)
        self.assertEqual(len(hamza_projs), 2)
        hamza_my_tasks = get_agent_my_tasks(hamza)
        self.assertEqual(len(hamza_my_tasks), 2)

    def test_05_modified_transcript_test(self):
        # As specified on page 11:
        # "Suggested changed-input test: change QuickServe integration's final estimate to 12 hours and deadline to 23 October.
        # Its generated task should reflect those values; other tasks should remain unchanged."
        transcript_path = os.path.join(os.path.dirname(__file__), "sample_transcript.txt")
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = f.read()

        # Modify the transcript
        modified_transcript = transcript.replace(
            "Usman owns Mobile integration and testing: 10 hours, 22 October.",
            "Usman owns Mobile integration and testing: 12 hours, 23 October."
        ).replace(
            "Mobile integration and testing, Usman, 10 hours, 22 October.",
            "Mobile integration and testing, Usman, 12 hours, 23 October."
        )

        users = get_all_users()
        extracted, method = extract_projects(modified_transcript, users)
        qs = next(p for p in extracted["projects"] if "QuickServe" in p["name"])
        t_int = next(t for t in qs["tasks"] if "integration" in t["title"].lower())

        self.assertEqual(t_int["estimatedHours"], 12.0, "Modified estimate must be 12 hours")
        self.assertEqual(t_int["deadline"], "2026-10-23", "Modified deadline must be 2026-10-23")

if __name__ == "__main__":
    unittest.main()
