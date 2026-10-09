from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import judge
from .models import Problem, Submission

MAX_CODE_BYTES = 50_000
SUBMIT_COOLDOWN_SECONDS = 5


def index(request):
    return render(request, "index.html")


def problem_list(request, pk=None):
    problems = Problem.objects.filter(is_published=True)
    solved = set()
    if request.user.is_authenticated:
        solved = set(Submission.objects.filter(user=request.user, verdict="AC").values_list("problem_id", flat=True))
    problem = get_object_or_404(problems, pk=pk) if pk else None
    submission = None
    sub_id = request.GET.get("s", "")
    if problem and request.user.is_authenticated and sub_id.isdigit():
        submission = Submission.objects.filter(pk=sub_id, user=request.user, problem=problem).first()
    context = {"problems": problems, "problem": problem, "solved": solved, "submission": submission}
    return render(request, "problems.html", context)


@login_required
@require_POST
def submit(request, pk):
    problem = get_object_or_404(Problem, pk=pk, is_published=True)
    back = redirect("problem_detail", pk=pk)

    last = Submission.objects.filter(user=request.user).first()
    if last and (timezone.now() - last.created_at).total_seconds() < SUBMIT_COOLDOWN_SECONDS:
        messages.error(request, f"Please wait {SUBMIT_COOLDOWN_SECONDS} seconds between submissions.")
        return back

    uploaded = request.FILES.get("code_file")
    language = request.POST.get("language", "c")
    if uploaded:
        name = uploaded.name.lower()
        if not name.endswith((".c", ".py")):
            messages.error(request, "Only .c and .py files are accepted.")
            return back
        if uploaded.size > MAX_CODE_BYTES:
            messages.error(request, "File is too large (max 50 KB).")
            return back
        code = uploaded.read().decode("utf-8", errors="replace")
        language = "python" if name.endswith(".py") else "c"
    else:
        code = request.POST.get("code_text", "")
        if len(code.encode()) > MAX_CODE_BYTES:
            messages.error(request, "Code is too large (max 50 KB).")
            return back
    if language not in ("c", "python"):
        language = "c"
    if not code.strip():
        messages.error(request, "Choose a file or paste your code first.")
        return back

    result = judge.evaluate(code, language, list(problem.testcases.all()), problem.time_limit)
    results = result["results"]
    submission = Submission.objects.create(
        user=request.user, problem=problem, language=language, source_code=code,
        verdict=result["verdict"], passed=sum(1 for r in results if r["ok"]), total=len(results),
        results=results, message=result["message"],
    )
    if submission.verdict == "AC":
        messages.success(request, "Accepted! Problem solved.")
    return redirect(f"{back.url}?s={submission.pk}")
