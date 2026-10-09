from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Problem(models.Model):
    DIFFICULTIES = [("Easy", "Easy"), ("Medium", "Medium"), ("Hard", "Hard")]

    title = models.CharField(max_length=150)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTIES, default="Easy")
    statement = models.TextField()
    input_format = models.TextField(blank=True)
    output_format = models.TextField(blank=True)
    sample_input = models.TextField(blank=True)
    sample_output = models.TextField(blank=True)
    time_limit = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Seconds allowed per test case (1 to 10).",
    )
    is_published = models.BooleanField(default=False, help_text="Only published problems are visible to students.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="testcases")
    input_data = models.TextField(blank=True)
    expected_output = models.TextField()
    is_hidden = models.BooleanField(default=True, help_text="Hidden tests never show their input or output to students.")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Test {self.order} of {self.problem}"


class Submission(models.Model):
    VERDICTS = [
        ("AC", "Accepted"),
        ("WA", "Wrong Answer"),
        ("CE", "Compilation Error"),
        ("RE", "Runtime Error"),
        ("TLE", "Time Limit Exceeded"),
        ("IE", "Internal Error"),
    ]
    LANGUAGES = [("c", "C"), ("python", "Python")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    language = models.CharField(max_length=10, choices=LANGUAGES)
    source_code = models.TextField()
    verdict = models.CharField(max_length=4, choices=VERDICTS)
    passed = models.PositiveSmallIntegerField(default=0)
    total = models.PositiveSmallIntegerField(default=0)
    results = models.JSONField(default=list, blank=True)  # per test: number, hidden flag, verdict (never hidden data)
    message = models.TextField(blank=True)  # compiler error or sample-test error text
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.problem} - {self.verdict}"
