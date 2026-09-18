import os
import sqlite3
import tempfile
import unittest

from pychess.Database import model


class DatabaseModelTests(unittest.TestCase):
    def test_schema_version_is_committed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "database.sqlite")
            engine = model.get_engine(path)
            engine.dispose()

            with sqlite3.connect(path) as connection:
                self.assertEqual(
                    [(1, model.SCHEMA_VERSION)],
                    connection.execute(
                        "SELECT id, version FROM schema_version"
                    ).fetchall(),
                )


if __name__ == "__main__":
    unittest.main()
