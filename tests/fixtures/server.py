"""
Mock the Pelletronic Touch v4 - Oekofen JSON Interface V4.00b.

Touch4 response headers are (no more no less):
    HTTP/1.1 200 OK
    Date: Mon, 23 Sep 2024 18:32:41 GMT
    Content-length: 4313

Body is a binay encoded ISO-8859-1 JSON payload.
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class MyHandler(BaseHTTPRequestHandler):

    protocol_version = "HTTP/1.1"

    # Get initial data from downloaded files
    with open("all", "rb") as f:
        data = json.loads(f.read().decode(encoding="ISO-8859-1"))

    with open("all+meta", "rb") as f:
        data_meta = json.loads(f.read().decode(encoding="ISO-8859-1"))

    def do_GET(self):
        print(f"Request: {self.requestline}")
        try:
            empty, passwd, target = self.path.split("/")
            if empty:
                self._send_syntax_error()
        except ValueError:
            self._send_syntax_error()
        else:
            self._parse_target(target)

    def _parse_assignment(self, target):
        try:
            abs_attr, value = target.split("=")
            section, attr = abs_attr.split(".")
        except ValueError:
            self._send_syntax_error()
        else:
            try:
                self.data[section][attr] = value
            except KeyError as e:
                self.send_error(500, explain=f"Key not found: {e}")
            else:
                self._send_data(target)

    def _parse_getter(self, target):
        try:
            section, attr = target.split(".")
        except ValueError:
            self._send_syntax_error()
        else:
            try:
                data = json.dumps({section: {attr: self.data[section][attr]}})
            except KeyError as e:
                self.send_error(500, explain=f"Key not found: {e}")
            else:
                self._send_data(data)

    def _parse_target(self, target):
        if target == "all":
            self._send_data(json.dumps(self.data))
        elif target == "all?":
            self._send_data(json.dumps(self.data_meta))
        elif "=" in target:
            self._parse_assignment(target)
        else:
            self._parse_getter(target)

    def _send_data(self, data):
        body = data.encode(encoding="ISO-8859-1")
        self.send_response_only(200)
        self.send_header("Date", self.date_time_string())
        self.send_header("Content-length", len(body))
        self.end_headers()
        if data:
            self.wfile.write(body)

        print(f"answer: {body[:70]}{'…' if len(body) > 80 else ''}")

    def _send_syntax_error(self):
        self.send_error(
            400,
            explain='Supported path syntax is: "/" PASSWD "/" ( "all" [ "?" ] | ATTRIBUTE [ "=" VALUE ] )',
        )


def run(server_class=HTTPServer):
    print("Start mocked Oekofen JSON interface V4.00b on 0.0.0.0:3938")
    server_address = ("", 3938)
    httpd = server_class(server_address, MyHandler)
    httpd.serve_forever()


if __name__ == "__main__":
    run()
