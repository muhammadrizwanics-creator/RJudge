import shutil
from unittest import skipUnless

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from . import judge
from .models import Problem, Submission
from .models import TestCase as Case

SUM_PY = "a, b = map(int, input().split())\nprint(a + b)\n"
SUM_C = '#include <stdio.h>\nint main(){int a,b;scanf("%d %d",&a,&b);printf("%d\\n",a+b);return 0;}\n'


def make_problem():
    problem = Problem.objects.create(title="Sum", statement="Add.", is_published=True, time_limit=1,
                                     sample_input="5 7", sample_output="12")
    for i, (inp, out, hidden) in enumerate([("5 7", "12", False), ("-3 3", "0", True), ("0 0", "0", True)]):
        Case.objects.create(problem=problem, input_data=inp, expected_output=out, is_hidden=hidden, order=i)
    return problem


class JudgeTests(TestCase):
    def setUp(self):
        self.problem = make_problem()
        self.cases = list(self.problem.testcases.all())

    def run_py(self, code):
        return judge.evaluate(code, "python", self.cases, 1)

    def test_python_accepted(self):
        self.assertEqual(self.run_py(SUM_PY)["verdict"], "AC")

    def test_hardcoded_sample_is_not_accepted(self):
        result = self.run_py("print(12)\n")
        self.assertEqual(result["verdict"], "WA")
        self.assertTrue(result["results"][0]["ok"])      # sample passes
        self.assertFalse(result["results"][1]["ok"])     # hidden test catches it

    def test_runtime_error(self):
        self.assertEqual(self.run_py("print(1/0)\n")["verdict"], "RE")

    def test_time_limit(self):
        self.assertEqual(self.run_py("while True:\n    pass\n")["verdict"], "TLE")

    def test_hidden_test_error_text_is_not_leaked(self):
        code = "import sys\nx = input()\nif x != '5 7':\n    sys.stderr.write(x)\n    sys.exit(1)\nprint(12)\n"
        self.assertEqual(self.run_py(code)["message"], "")

    @skipUnless(shutil.which("gcc"), "gcc is not installed")
    def test_c_accepted_and_compile_error(self):
        self.assertEqual(judge.evaluate(SUM_C, "c", self.cases, 1)["verdict"], "AC")
        bad = judge.evaluate("int main( { return 0 }", "c", self.cases, 1)
        self.assertEqual(bad["verdict"], "CE")
        self.assertTrue(bad["message"])


class WebFlowTests(TestCase):
    def setUp(self):
        self.problem = make_problem()

    def register(self):
        return self.client.post(reverse("register"), {
            "name": "Ali Khan", "username": "ali", "email": "ali@uni.edu.pk",
            "university": "PU", "password": "Str0ng-pass-99"})

    def test_register_login_logout(self):
        self.assertRedirects(self.register(), reverse("dashboard"))
        self.client.post(reverse("logout"))
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("login") + "?next=/dashboard/")
        self.assertRedirects(self.client.post(reverse("login"), {"username": "ALI@uni.edu.pk", "password": "Str0ng-pass-99"}),
                             reverse("dashboard"))

    def test_duplicate_registration_rejected(self):
        self.register()
        self.client.post(reverse("logout"))
        self.assertEqual(self.register().status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_submit_file_and_see_verdict_without_hidden_data(self):
        self.register()
        url = reverse("submit", args=[self.problem.pk])
        response = self.client.post(url, {"code_file": SimpleUploadedFile("sol.py", SUM_PY.encode())})
        sub = Submission.objects.get()
        self.assertEqual(sub.verdict, "AC")
        self.assertRedirects(response, f"{reverse('problem_detail', args=[self.problem.pk])}?s={sub.pk}")
        page = self.client.get(response.url).content.decode()
        self.assertIn("Accepted", page)
        self.assertNotIn("-3 3", page)  # hidden test input is never shown

    def test_rate_limit_and_bad_extension(self):
        self.register()
        url = reverse("submit", args=[self.problem.pk])
        self.client.post(url, {"code_text": SUM_PY, "language": "python"})
        self.client.post(url, {"code_text": SUM_PY, "language": "python"})
        self.assertEqual(Submission.objects.count(), 1)  # second one blocked by cooldown

    def test_anonymous_cannot_submit(self):
        response = self.client.post(reverse("submit", args=[self.problem.pk]), {"code_text": "x"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.count(), 0)


# ---------------------------------------------------------------------------
# Judge0 backend, tested against a small fake Judge0 server (no internet needed)
import base64
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from django.test import override_settings


def _d(text):
    return base64.b64decode(text).decode()


def _e(text):
    return base64.b64encode(text.encode()).decode()


class FakeJudge0(BaseHTTPRequestHandler):
    store, polls = {}, {"n": 0}

    def log_message(self, *args):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        return self.headers.get("X-Auth-Token") == "secret"

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if not self._authorized():
            return self._send({"error": "no"}, 403)
        tokens = []
        for sub in data["submissions"]:
            token = f"tok{len(FakeJudge0.store)}"
            FakeJudge0.store[token] = sub
            tokens.append({"token": token})
        self._send(tokens, 201)

    def do_GET(self):
        if not self._authorized():
            return self._send({"error": "no"}, 403)
        FakeJudge0.polls["n"] += 1
        out = []
        for token in parse_qs(urlparse(self.path).query)["tokens"][0].split(","):
            sub = FakeJudge0.store[token]
            if FakeJudge0.polls["n"] == 1:  # first poll: still processing
                out.append({"token": token, "status": {"id": 2}})
                continue
            source, stdin = _d(sub["source_code"]), _d(sub["stdin"])
            if sub["language_id"] == 50 and "BAD" in source:
                out.append({"token": token, "status": {"id": 6}, "compile_output": _e("error: expected ';'")})
                continue
            try:
                p = subprocess.run([sys.executable, "-c", source], input=stdin.encode(),
                                   capture_output=True, timeout=sub["cpu_time_limit"])
            except subprocess.TimeoutExpired:
                out.append({"token": token, "status": {"id": 5}})
                continue
            if p.returncode == 0:
                out.append({"token": token, "status": {"id": 3}, "stdout": _e(p.stdout.decode())})
            else:
                out.append({"token": token, "status": {"id": 11}, "stderr": _e(p.stderr.decode())})
        self._send({"submissions": out})


class Judge0BackendTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = HTTPServer(("127.0.0.1", 0), FakeJudge0)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        super().tearDownClass()

    def setUp(self):
        FakeJudge0.store.clear()
        FakeJudge0.polls["n"] = 0
        self.cases = list(make_problem().testcases.all())
        self.settings = override_settings(
            JUDGE_BACKEND="judge0", JUDGE0_URL=f"http://127.0.0.1:{self.server.server_port}",
            JUDGE0_HEADERS={"X-Auth-Token": "secret"}, JUDGE0_POLL_INTERVAL=0.05)
        self.settings.enable()
        self.addCleanup(self.settings.disable)

    def test_accepted_wrong_answer_and_polling(self):
        self.assertEqual(judge.evaluate(SUM_PY, "python", self.cases, 1)["verdict"], "AC")
        FakeJudge0.polls["n"] = 0
        result = judge.evaluate("print(12)\n", "python", self.cases, 1)
        self.assertEqual(result["verdict"], "WA")
        self.assertEqual([r["ok"] for r in result["results"]], [True, False, False])

    def test_compile_error_runtime_error_and_timeout(self):
        ce = judge.evaluate("BAD", "c", self.cases, 1)
        self.assertEqual((ce["verdict"], ce["message"]), ("CE", "error: expected ';'"))
        self.assertEqual(judge.evaluate("print(1/0)\n", "python", self.cases, 1)["verdict"], "RE")
        self.assertEqual(judge.evaluate("while True: pass\n", "python", self.cases, 1)["verdict"], "TLE")

    def test_wrong_api_key_gives_internal_error(self):
        with override_settings(JUDGE0_HEADERS={"X-Auth-Token": "wrong"}):
            result = judge.evaluate(SUM_PY, "python", self.cases, 1)
        self.assertEqual(result["verdict"], "IE")

    def test_server_down_gives_internal_error(self):
        with override_settings(JUDGE0_URL="http://127.0.0.1:1"):
            self.assertEqual(judge.evaluate(SUM_PY, "python", self.cases, 1)["verdict"], "IE")
