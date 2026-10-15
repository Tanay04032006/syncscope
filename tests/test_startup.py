import errno
import unittest
from unittest.mock import MagicMock, patch

from app import run


class StartupTests(unittest.TestCase):
    @patch("app.ThreadingHTTPServer")
    def test_busy_port_uses_next_port_and_closes_server(self, server_type):
        server = MagicMock()
        server.server_address = ("127.0.0.1", 8766)
        server.serve_forever.side_effect = KeyboardInterrupt
        server_type.side_effect = [OSError(errno.EADDRINUSE, "busy"), server]
        run(auto_port=True)
        self.assertEqual(server_type.call_args_list[1].args[0], ("127.0.0.1", 8766))
        server.server_close.assert_called_once()

    @patch("app.ThreadingHTTPServer", side_effect=OSError(errno.EADDRINUSE, "busy"))
    def test_explicit_port_failure_does_not_silently_switch(self, server_type):
        with self.assertRaises(OSError):
            run(auto_port=False)
        self.assertEqual(server_type.call_count, 1)
