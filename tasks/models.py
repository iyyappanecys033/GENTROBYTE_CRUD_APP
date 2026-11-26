from django.db import models
from django.db.models import Index
from django.urls import reverse


class TeamMember(models.Model):
    name = models.CharField(
        max_length=120,
        verbose_name="full name",
        help_text="The name shown on task assignments.",
    )
    email = models.EmailField(
        unique=True,
        verbose_name="work email",
        help_text="Used to identify this team member in the directory.",
    )
    role = models.CharField(
        max_length=100,
        blank=True,
        help_text="A concise role or discipline, such as Product designer.",
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="The team or department this person belongs to.",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="active",
        help_text="Inactive members remain in history but cannot receive new tasks.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="created")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="last updated")

    class Meta:
        ordering = ["name"]
        verbose_name = "team member"
        verbose_name_plural = "team members"
        indexes = [Index(fields=["is_active", "name"], name="member_active_name_idx")]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tasks:member_detail", kwargs={"pk": self.pk})


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        COMPLETED = "completed", "Completed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    CATEGORY_CHOICES = [
        ("product", "Product"),
        ("engineering", "Engineering"),
        ("design", "Design"),
        ("operations", "Operations"),
        ("customer", "Customer"),
    ]

    title = models.CharField(
        max_length=180,
        verbose_name="task title",
        help_text="Use a clear, action-oriented title.",
        db_index=True,
    )
    description = models.TextField(
        blank=True,
        help_text="Add the context or outcome the assignee needs.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        help_text="The current state of this work.",
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        help_text="How urgently the team should address this work.",
        db_index=True,
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="operations",
        help_text="The discipline primarily responsible for this work.",
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
        help_text="The team member responsible for moving this work forward.",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Leave blank if this work has no target date.",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="created")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="last updated")

    class Meta:
        ordering = ["due_date", "-priority", "title"]
        indexes = [
            Index(fields=["status", "due_date"], name="task_status_due_idx"),
            Index(fields=["assigned_to", "status"], name="task_owner_status_idx"),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("tasks:task_detail", kwargs={"pk": self.pk})

    @property
    def is_overdue(self):
        from django.utils import timezone

        return (
            self.due_date is not None
            and self.due_date < timezone.localdate()
            and self.status != self.Status.COMPLETED
        )
