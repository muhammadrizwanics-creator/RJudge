from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from problems.models import Problem, Submission

from .forms import AvatarForm, RegisterForm
from .models import Profile


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to RJudge! Your account is ready.")
        return redirect("dashboard")
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    error = ""
    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        if "@" in identifier:  # allow logging in with email
            match = User.objects.filter(email__iexact=identifier).first()
            identifier = match.username if match else identifier
        user = authenticate(request, username=identifier, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("dashboard")
        error = "Wrong username/email or password."
    return render(request, "login.html", {"error": error})


@login_required
def dashboard_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    solved = Problem.objects.filter(
        submissions__user=request.user, submissions__verdict="AC"
    ).distinct()
    total = Problem.objects.filter(is_published=True).count()
    history = Submission.objects.filter(user=request.user).select_related("problem")[:50]
    context = {
        "profile": profile,
        "solved": solved,
        "solved_count": solved.count(),
        "remaining": max(total - solved.count(), 0),
        "pct": round(100 * solved.count() / total) if total else 0,
        "history": history,
        "submission_count": Submission.objects.filter(user=request.user).count(),
    }
    return render(request, "dashboard.html", context)


@login_required
@require_POST
def avatar_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = AvatarForm(request.POST, request.FILES, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, "Profile picture updated.")
    else:
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect("dashboard")
