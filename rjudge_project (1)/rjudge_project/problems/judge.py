"""Compiles and runs student code, then compares the output with the test cases.

Two backends, chosen by JUDGE_BACKEND in settings:
  "local"  - runs student code directly on this computer. Fine on your own laptop
             for development. It is NOT a sandbox: never use it on a public server.
  "judge0" - sends the code to a Judge0 server (sandboxed). Use this for the public site.
The rest of the project only calls evaluate() and uses the dictionary it returns.
"""
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from django.conf import settings

log = logging.getLogger(__name__)

COMPILE_TIMEOUT = 15      # seconds
MAX_OUTPUT = 1_000_000    # bytes of output we keep per test
MEMORY_MB = 256           # memory limit (Linux/macOS only)
SAFE_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "LANG")

LABELS = {"AC": "Passed", "WA": "Wrong answer", "RE": "Runtime error", "TLE": "Time limit exceeded"}


def _normalize(text):
    """Ignore trailing spaces and blank lines at the end, nothing else."""
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _limits(time_limit):
    if os.name != "posix":
        return None
    import resource

    def apply():
        resource.setrlimit(resource.RLIMIT_CPU, (time_limit + 1, time_limit + 1))
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_MB << 20, MEMORY_MB << 20))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT, MAX_OUTPUT))
    return apply


def _run(cmd, workdir, stdin_text, time_limit):
    """Run one test. Returns (status, stdout_text, stderr_text); status is OK, RE or TLE."""
    env = {k: v for k, v in os.environ.items() if k in SAFE_ENV_KEYS}
    env["PYTHONIOENCODING"] = "utf-8"
    out_path, err_path = os.path.join(workdir, "out.txt"), os.path.join(workdir, "err.txt")
    with open(out_path, "wb") as out, open(err_path, "wb") as err:
        try:
            proc = subprocess.run(
                cmd, input=stdin_text.encode(), stdout=out, stderr=err, cwd=workdir,
                timeout=time_limit, env=env, preexec_fn=_limits(time_limit),
            )
        except subprocess.TimeoutExpired:
            return "TLE", "", ""
    with open(out_path, "rb") as f:
        stdout = f.read(MAX_OUTPUT).decode("utf-8", "replace")
    with open(err_path, "rb") as f:
        stderr = f.read(2000).decode("utf-8", "replace")
    return ("OK" if proc.returncode == 0 else "RE"), stdout, stderr


def _internal(message):
    return {"verdict": "IE", "results": [], "message": message}


def _evaluate_local(code, language, testcases, time_limit):
    with tempfile.TemporaryDirectory() as workdir:
        if language == "c":
            gcc = shutil.which("gcc")
            if not gcc:
                return _internal("The C compiler (gcc) is not available on the server.")
            source = os.path.join(workdir, "main.c")
            exe = os.path.join(workdir, "main.exe" if os.name == "nt" else "main")
            with open(source, "w", encoding="utf-8") as f:
                f.write(code)
            try:
                build = subprocess.run(
                    [gcc, "-O2", "-std=c11", "-o", exe, source, "-lm"],
                    capture_output=True, text=True, timeout=COMPILE_TIMEOUT, cwd=workdir,
                )
            except subprocess.TimeoutExpired:
                return {"verdict": "CE", "results": [], "message": "Compilation took too long."}
            if build.returncode != 0:
                return {"verdict": "CE", "results": [], "message": build.stderr.replace(workdir, "")[:2000]}
            cmd = [exe]
        elif language == "python":
            source = os.path.join(workdir, "main.py")
            with open(source, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = [sys.executable, "-I", source]
        else:
            return _internal("Unsupported language.")

        results, message = [], ""
        for number, case in enumerate(testcases, start=1):
            status, stdout, stderr = _run(cmd, workdir, case.input_data, time_limit)
            if status == "OK":
                verdict = "AC" if _normalize(stdout) == _normalize(case.expected_output) else "WA"
            else:
                verdict = status
            # Error text is shown only for sample tests, so a program cannot print
            # hidden input to stderr and read it back.
            if verdict == "RE" and not message and not case.is_hidden:
                message = stderr
            results.append({"n": number, "hidden": case.is_hidden, "verdict": verdict,
                            "label": LABELS[verdict], "ok": verdict == "AC"})

    return {"verdict": _final_verdict(results), "results": results, "message": message}


def _final_verdict(results):
    if all(r["ok"] for r in results):
        return "AC"
    return next(v for v in ("RE", "TLE", "WA") if any(r["verdict"] == v for r in results))


def evaluate(code, language, testcases, time_limit):
    """Returns {"verdict": code, "results": [...], "message": text}."""
    if not testcases:
        return _internal("This problem has no test cases yet. Tell your teacher.")
    if getattr(settings, "JUDGE_BACKEND", "local") == "judge0":
        return _evaluate_judge0(code, language, testcases, time_limit)
    return _evaluate_local(code, language, testcases, time_limit)


# ---------------------------------------------------------------- Judge0 backend
def _b64(text):
    return base64.b64encode(text.encode()).decode()


def _unb64(text):
    return base64.b64decode(text).decode("utf-8", "replace") if text else ""


def _judge0_request(method, path, payload=None):
    url = settings.JUDGE0_URL.rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json", "User-Agent": "RJudge/1.0", **settings.JUDGE0_HEADERS}
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def _evaluate_judge0(code, language, testcases, time_limit):
    language_id = settings.JUDGE0_LANGUAGE_IDS.get(language)
    if not language_id:
        return _internal("Unsupported language.")
    submissions = [{
        "language_id": language_id,
        "source_code": _b64(code),
        "stdin": _b64(case.input_data),
        "cpu_time_limit": time_limit,
        "wall_time_limit": time_limit * 2 + 1,
        "memory_limit": MEMORY_MB * 1024,  # Judge0 uses kilobytes
    } for case in testcases]
    try:
        created = _judge0_request("POST", "/submissions/batch?base64_encoded=true", {"submissions": submissions})
        tokens = [item.get("token") for item in created]
        if not tokens or None in tokens:
            log.error("Judge0 rejected the batch: %s", created)
            return _internal("The judge rejected this submission. Tell your teacher.")
        path = "/submissions/batch?base64_encoded=true&tokens=" + ",".join(tokens)
        deadline = time.monotonic() + settings.JUDGE0_POLL_TIMEOUT
        while True:
            by_token = {r["token"]: r for r in _judge0_request("GET", path)["submissions"]}
            if all(by_token[t]["status"]["id"] not in (1, 2) for t in tokens):
                break
            if time.monotonic() > deadline:
                return _internal("The judge took too long to answer. Please try again.")
            time.sleep(settings.JUDGE0_POLL_INTERVAL)
    except urllib.error.HTTPError as error:
        log.error("Judge0 HTTP error %s", error.code)
        if error.code in (401, 403):
            return _internal("The judge refused our login. Tell your teacher to check the API key.")
        if error.code == 429:
            return _internal("The judge is busy or its quota is finished. Try again later.")
        return _internal(f"The judge returned an error ({error.code}).")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
        log.error("Judge0 unreachable or bad reply: %s", error)
        return _internal("The judge service is not reachable right now. Try again later.")

    results, message = [], ""
    for number, (token, case) in enumerate(zip(tokens, testcases), start=1):
        item = by_token[token]
        status = item["status"]["id"]
        if status == 6:  # compilation error: same for every test, show it once
            return {"verdict": "CE", "results": [], "message": _unb64(item.get("compile_output"))[:2000]}
        if status == 13:
            return _internal("The judge had an internal problem. Please try again.")
        if status == 3:
            verdict = "AC" if _normalize(_unb64(item.get("stdout"))) == _normalize(case.expected_output) else "WA"
        elif status == 5:
            verdict = "TLE"
        else:  # 7-12 runtime errors, 14 exec format error, anything else
            verdict = "RE"
        if verdict == "RE" and not message and not case.is_hidden:
            message = (_unb64(item.get("stderr")) or _unb64(item.get("message")))[:2000]
        results.append({"n": number, "hidden": case.is_hidden, "verdict": verdict,
                        "label": LABELS[verdict], "ok": verdict == "AC"})
    return {"verdict": _final_verdict(results), "results": results, "message": message}
