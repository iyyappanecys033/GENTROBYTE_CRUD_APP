from django.contrib import admin
from .models import Task, TeamMember


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role", "department", "is_active", "updated_at")
    list_filter = ("is_active", "department")
    search_fields = ("name", "email", "role", "department")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "category",
        "assigned_to",
        "due_date",
        "updated_at",
    )
    list_filter = ("status", "priority", "category", "due_date")
    search_fields = ("title", "description", "assigned_to__name", "category")
    list_select_related = ("assigned_to",)
    date_hierarchy = "due_date"
    readonly_fields = ("created_at", "updated_at")
