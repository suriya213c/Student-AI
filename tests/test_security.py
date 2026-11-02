import hashlib
import socket
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from AI import resources
import database


class ResourceURLSecurityTests(unittest.TestCase):
    def test_rejects_non_http_schemes_and_embedded_credentials(self):
        for url in (
            "file:///etc/passwd",
            "ftp://example.com/resource",
            "https://user:password@example.com/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    resources._validate_url(url)

    def test_rejects_private_and_special_ip_addresses(self):
        for url in (
            "http://127.0.0.1/",
            "http://10.0.0.1/",
            "http://169.254.169.254/",
            "http://[::1]/",
            "http://[fe80::1]/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    resources._validate_url(url)

    @patch("AI.resources.socket.getaddrinfo")
    def test_rejects_a_hostname_resolving_to_a_private_address(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", 0))
        ]

        with self.assertRaises(ValueError):
            resources._validate_url("https://study.example/")

    @patch("AI.resources.socket.getaddrinfo")
    def test_rejects_mixed_public_and_private_dns_answers(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0)),
        ]

        with self.assertRaises(ValueError):
            resources._validate_url("https://study.example/")

    @patch("AI.resources.socket.getaddrinfo")
    @patch("AI.resources.urllib3.HTTPSConnectionPool")
    def test_https_connection_is_pinned_to_checked_ip_and_original_host(
        self, connection_pool, getaddrinfo
    ):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
        ]

        resources._request_pinned("https://study.example/lesson?q=1")

        connection_pool.assert_called_once()
        args, kwargs = connection_pool.call_args
        self.assertEqual(kwargs["host"], "93.184.216.34")
        self.assertEqual(kwargs["assert_hostname"], "study.example")
        self.assertEqual(kwargs["server_hostname"], "study.example")
        connection_pool.return_value.request.assert_called_once()
        request_args, request_kwargs = connection_pool.return_value.request.call_args
        self.assertEqual(request_args, ("GET", "/lesson?q=1"))
        self.assertEqual(request_kwargs["headers"]["Host"], "study.example")
        connection_pool.return_value.close.assert_called_once()

    @patch("AI.resources.socket.getaddrinfo")
    @patch("AI.resources.urllib3.HTTPConnectionPool")
    def test_redirect_to_loopback_is_rejected_before_a_second_request(
        self, connection_pool, getaddrinfo
    ):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
        ]
        redirect_response = unittest.mock.Mock(
            status=302,
            headers={"Location": "http://127.0.0.1/admin"},
        )
        connection_pool.return_value.request.return_value = redirect_response

        result = resources.get_webpage_text("http://study.example/start")

        self.assertIn("RESOURCE_ERROR", result)
        connection_pool.return_value.request.assert_called_once()

    @patch("AI.resources.socket.getaddrinfo")
    @patch("AI.resources.urllib3.HTTPConnectionPool")
    def test_redirect_to_private_dns_result_is_rejected_before_request(
        self, connection_pool, getaddrinfo
    ):
        def resolve(host, *_args, **_kwargs):
            address = "93.184.216.34" if host == "study.example" else "10.1.2.3"
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0))]

        getaddrinfo.side_effect = resolve
        redirect_response = unittest.mock.Mock(
            status=302,
            headers={"Location": "http://internal.example/admin"},
        )
        connection_pool.return_value.request.return_value = redirect_response

        result = resources.get_webpage_text("http://study.example/start")

        self.assertIn("RESOURCE_ERROR", result)
        connection_pool.return_value.request.assert_called_once()


class PasswordSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.database_path = patch.object(
            database,
            "DATABASE",
            str(Path(self.temp_dir.name) / "test.db"),
        )
        self.database_path.start()
        self.addCleanup(self.database_path.stop)
        database.create_table()

    def test_password_hashes_are_salted_and_verifiable(self):
        first_hash = database.hash_password("correct horse battery staple")
        second_hash = database.hash_password("correct horse battery staple")

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(database.verify_password("correct horse battery staple", first_hash))
        self.assertFalse(database.verify_password("wrong password", first_hash))
        self.assertTrue(first_hash.startswith("pbkdf2_sha256$"))

    def test_successful_legacy_login_migrates_password_hash(self):
        legacy_hash = hashlib.sha256(b"correct horse battery staple").hexdigest()
        with closing(sqlite3.connect(database.DATABASE)) as connection:
            connection.execute(
                """
                INSERT INTO users (name, email, username, password)
                VALUES (?, ?, ?, ?)
                """,
                ("Student", "student@example.com", "student", legacy_hash),
            )
            connection.commit()

        user = database.login_user("student", "correct horse battery staple")
        with closing(sqlite3.connect(database.DATABASE)) as connection:
            migrated_hash = connection.execute(
                "SELECT password FROM users WHERE username = ?",
                ("student",),
            ).fetchone()[0]

        self.assertEqual(user[3], "student")
        self.assertNotEqual(migrated_hash, legacy_hash)
        self.assertTrue(database.verify_password("correct horse battery staple", migrated_hash))

    def test_failed_legacy_login_does_not_change_stored_hash(self):
        legacy_hash = hashlib.sha256(b"correct horse battery staple").hexdigest()
        with closing(sqlite3.connect(database.DATABASE)) as connection:
            connection.execute(
                """
                INSERT INTO users (name, email, username, password)
                VALUES (?, ?, ?, ?)
                """,
                ("Student", "student@example.com", "student", legacy_hash),
            )
            connection.commit()

        self.assertIsNone(database.login_user("student", "wrong password"))
        with closing(sqlite3.connect(database.DATABASE)) as connection:
            stored_hash = connection.execute(
                "SELECT password FROM users WHERE username = ?",
                ("student",),
            ).fetchone()[0]
        self.assertEqual(stored_hash, legacy_hash)


if __name__ == "__main__":
    unittest.main()
