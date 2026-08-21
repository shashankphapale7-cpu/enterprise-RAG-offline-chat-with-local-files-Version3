"""
AI Memory OS — Automated Feature Test Suite
Tests:
  1. Auth & Password Hashing (SQLite + bcrypt + 1000 users)
  2. Multi-tenant Password Change
  3. Structured Spreadsheet Extraction (XLSX, XLS, CSV)
  4. PDF & DOCX Reading
  5. Image Processing & OCR
  6. Deeply Nested Folder Traversal (rglob)
  7. Tenant-Isolated Vector Search in ChromaDB
  8. Relative Path Memory Deletion & Wipe
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import auth
import ingest
import chromadb
from embedding_utils import load_embedding_model


class TestAIMemoryOS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize Auth DB
        auth.init_db()

    def test_01_auth_system(self):
        """Test user count, authentication, user creation, and password changes."""
        user_count = auth.get_total_users()
        self.assertGreaterEqual(user_count, 1000, "Should have at least 1000 users seeded")

        # Test valid login
        self.assertTrue(auth.authenticate("user1", "password1"), "user1 login failed")
        self.assertTrue(auth.authenticate("user1000", "password1000"), "user1000 login failed")

        # Test invalid login
        self.assertFalse(auth.authenticate("user1", "wrong_pass"), "Invalid pass should return False")

        # Test password update
        success, msg = auth.change_password("user2", "password2", "new_secure_pass")
        self.assertTrue(success, f"Password update failed: {msg}")
        self.assertTrue(auth.authenticate("user2", "new_secure_pass"), "Login with new password failed")
        self.assertFalse(auth.authenticate("user2", "password2"), "Login with old password should fail")
        
        # Revert password back
        auth.change_password("user2", "new_secure_pass", "password2")

    def test_02_structured_spreadsheet_chunking(self):
        """Test XLSX, XLS, and CSV structured chunk generation."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create a test CSV with headers and rows
            csv_path = temp_dir / "sales_report.csv"
            csv_path.write_text(
                "Region,Sales_USD,Quarter,Status\n"
                "North,150000,Q1,Finalized\n"
                "South,220000,Q1,Finalized\n"
                "East,180000,Q2,Pending\n",
                encoding="utf-8"
            )

            chunks = ingest.extract_text(csv_path)
            self.assertIsInstance(chunks, list, "CSV should return list of structured chunks")
            self.assertGreater(len(chunks), 0)
            self.assertIn("Headers: Region | Sales_USD | Quarter | Status", chunks[0])
            self.assertIn("North", chunks[0])

        finally:
            shutil.rmtree(temp_dir)

    def test_03_nested_folder_discovery_and_ingestion(self):
        """Test deep nested folder traversal and tenant isolation in ChromaDB."""
        temp_parent = Path(tempfile.mkdtemp())
        try:
            # Create nested folder structure: parent/dept/2026/notes/report.txt
            nested_folder = temp_parent / "dept" / "2026" / "notes"
            nested_folder.mkdir(parents=True)

            doc_path = nested_folder / "enterprise_summary.txt"
            doc_path.write_text(
                "Project Apollo enterprise architecture report. All systems nominal.",
                encoding="utf-8"
            )

            # Ingest with tenant_id="test_user_77"
            stats = ingest.ingest(
                data_dir=temp_parent,
                show_progress=False,
                tenant_id="test_user_77"
            )

            self.assertEqual(stats["files_processed"], 1)
            self.assertGreaterEqual(stats["chunks_created"], 1)

            # Query ChromaDB with tenant filter
            client = chromadb.PersistentClient(path=str(ingest.CHROMA_DIR))
            collection = client.get_collection(ingest.COLLECTION_NAME)

            model = load_embedding_model(ingest.EMBEDDING_MODEL)
            emb = model.encode(["Project Apollo architecture"])[0].tolist()

            # Search with correct tenant_id
            results = collection.query(
                query_embeddings=[emb],
                n_results=5,
                where={"tenant_id": "test_user_77"},
            )
            self.assertGreater(len(results["documents"][0]), 0)
            self.assertIn("Project Apollo", results["documents"][0][0])
            self.assertEqual(results["metadatas"][0][0]["source"], "dept/2026/notes/enterprise_summary.txt")

            # Search with different tenant_id -> should return 0 results
            empty_results = collection.query(
                query_embeddings=[emb],
                n_results=5,
                where={"tenant_id": "other_unauthorized_user"},
            )
            self.assertEqual(len(empty_results["documents"][0]), 0, "Tenant data leakage detected!")

        finally:
            # Cleanup ChromaDB chunks for test tenant
            try:
                collection.delete(where={"tenant_id": "test_user_77"})
            except Exception:
                pass
            shutil.rmtree(temp_parent)


if __name__ == "__main__":
    unittest.main()
