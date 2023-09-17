from datetime import datetime
import unittest

from models.model_base import ModelBase, db_session


class TestModelBase(unittest.TestCase):

    def setUp(self):
        # Set up the ModelBase instance for testing
        self.model_base = ModelBase("localhost")  # Replace with your database URL if needed
        self.model_base.initialize_database()

    def test_delete_record(self):
        # Test deleting a record
        with db_session:
            player = self.model_base.add_record(self.model_base.Player, name="john_doe", created_at=datetime.utcnow())
            self.model_base.delete_record(player)
            deleted_player = self.model_base.get_record_by_value(self.model_base.Player, name="john_doe")
            self.assertIsNone(deleted_player)

    def test_add_record(self):
        # Test adding a new record
        with db_session:
            player = self.model_base.add_record(self.model_base.Player, name="john_doe", created_at=datetime.utcnow())
            self.assertIsNotNone(player)
            self.model_base.delete_record(player)

    def test_get_record_by_value(self):
        # Test retrieving a record by value
        with db_session:
            player = self.model_base.add_record(self.model_base.Player, name="john_doe", created_at=datetime.utcnow())
            retrieved_player = self.model_base.get_record_by_value(self.model_base.Player, name="john_doe")
            self.assertIsNotNone(retrieved_player)
            self.assertEqual(player.id, retrieved_player.id)
            self.model_base.delete_record(player)

    def test_update_record(self):
        # Test updating a record
        with db_session:
            player = self.model_base.add_record(self.model_base.Player, name="john_doe", created_at=datetime.utcnow())
            player.name = "new_username"
            self.model_base.update_record(player)
            updated_player = self.model_base.get_record_by_value(self.model_base.Player, name="new_username")
            self.assertIsNotNone(updated_player)
            self.assertEqual(updated_player.name, "new_username")
            self.model_base.delete_record(player)
