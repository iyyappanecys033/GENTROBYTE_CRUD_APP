from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from .models import Task, TeamMember


def get_task_metrics():
    today = timezone.localdate()
    tasks = Task.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=~Q(status=Task.Status.COMPLETED)),
        completed=Count("id", filter=Q(status=Task.Status.COMPLETED)),
        overdue=Count(
            "id",
            filter=Q(due_date__lt=today) & ~Q(status=Task.Status.COMPLETED),
        ),
    )
    tasks["people"] = TeamMember.objects.filter(is_active=True).count()
    return tasks


def get_due_windows():
    today = timezone.localdate()
    open_tasks = Task.objects.exclude(status=Task.Status.COMPLETED)
    return [
        {
            "key": "overdue",
            "label": "Past due",
            "count": open_tasks.filter(due_date__lt=today).count(),
        },
        {
            "key": "today",
            "label": "Today",
            "count": open_tasks.filter(due_date=today).count(),
        },
        {
            "key": "week",
            "label": "Next 7 days",
            "count": open_tasks.filter(
                due_date__gt=today,
                due_date__lte=today + timedelta(days=7),
            ).count(),
        },
        {
            "key": "later",
            "label": "Later",
            "count": open_tasks.filter(due_date__gt=today + timedelta(days=7)).count(),
        },
    ]
