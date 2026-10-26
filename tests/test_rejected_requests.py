"""Rejected HTTP requests must still deliver readable errors on Windows."""
import http.client
import socket
import time
import unittest
from test_local import HTTP


class RejectedRequests(HTTP):
    def test_delayed_rejected_body_returns_403_and_preserves_data(self):
        with socket.create_connection(('127.0.0.1', self.server.server_port), timeout=5) as client:
            headers = (f'POST /api/commands HTTP/1.1\r\nHost: 127.0.0.1:{self.server.server_port}\r\n'
                       f'Cookie: thu_session={self.server.session}\r\nOrigin: https://example.com\r\n'
                       'Content-Type: application/json\r\nContent-Length: 4096\r\n\r\n')
            client.sendall(headers.encode())
            time.sleep(.02)
            client.sendall(b' ' * 4096)
            response = http.client.HTTPResponse(client)
            response.begin()
            self.assertEqual(response.status, 403)
            self.assertIn('Nguồn yêu cầu', response.read().decode())
        self.assertEqual(self.server.service.stores['real'].read()['_revision'], 0)

    def test_repeated_rejections_preserve_status_and_state(self):
        for _ in range(25):
            for headers, expected in (({'Origin': 'https://example.com'}, 403),
                                      ({'X-Tool-CSRF': 'bad'}, 403),
                                      ({'Cookie': 'thu_session=expired'}, 401)):
                status, body = self.request('/api/commands', {}, headers=headers)
                self.assertEqual(status, expected)
                self.assertIn('error', body)
        self.assertEqual(self.server.service.stores['real'].read()['_revision'], 0)


def load_tests(loader, suite, pattern):
    return unittest.TestSuite(RejectedRequests(name) for name in (
        'test_delayed_rejected_body_returns_403_and_preserves_data',
        'test_repeated_rejections_preserve_status_and_state'))
