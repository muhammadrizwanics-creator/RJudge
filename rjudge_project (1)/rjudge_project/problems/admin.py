from django import forms
from django.contrib import admin
from django.db import models

from .models import Problem, Submission, TestCase


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 3
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 3, "cols": 30})}
    }


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("title", "difficulty", "is_published", "time_limit", "created_at")
    list_filter = ("difficulty", "is_published")
    search_fields = ("title",)
    inlines = [TestCaseInline]
    actions = ["publish", "unpublish"]

    @admin.action(description="Publish selected problems")
    def publish(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description="Unpublish selected problems")
    def unpublish(self, request, queryset):
        queryset.update(is_published=False)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "problem", "language", "verdict", "passed", "total")
    list_filter = ("verdict", "language", "problem")
    search_fields = ("user__username", "user__email", "problem__title")
    readonly_fields = [f.name for f in Submission._meta.fields]

    def has_add_permission(self, request):
        return False
