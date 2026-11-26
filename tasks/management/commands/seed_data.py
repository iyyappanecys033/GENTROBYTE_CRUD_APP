from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tasks.models import Task, TeamMember


class Command(BaseCommand):
    help = "Create illustrative team members and 18 sample tasks for the demo."

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.DEBUG:
            user_model = get_user_model()
            if not user_model.objects.filter(
                username=settings.DEMO_ACCOUNT_USERNAME
            ).exists():
                user_model.objects.create_user(
                    username=settings.DEMO_ACCOUNT_USERNAME,
                    password=settings.DEMO_ACCOUNT_PASSWORD,
                )

        members = [
            ("Maya Chen", "maya.chen@example.test", "Product designer", "Product"),
            ("Theo Martin", "theo.martin@example.test", "Staff engineer", "Engineering"),
            ("Ari Patel", "ari.patel@example.test", "Operations lead", "Operations"),
            ("Nina Okafor", "nina.okafor@example.test", "Researcher", "Product"),
            ("Sam Rivera", "sam.rivera@example.test", "Frontend engineer", "Engineering"),
            ("Jules Park", "jules.park@example.test", "Customer partner", "Customer"),
            ("Rory Bennett", "rory.bennett@example.test", "Visual designer", "Design"),
        ]
        member_by_email = {}
        members_created = 0
        for name, email, role, department in members:
            member, created = TeamMember.objects.get_or_create(
                email=email,
                defaults={
                    "name": name,
                    "role": role,
                    "department": department,
                    "is_active": True,
                },
            )
            member_by_email[email] = member
            members_created += int(created)

        today = timezone.localdate()
        task_rows = [
            ("Map the first-run onboarding journey", "Outline the key decisions and handoffs a new workspace needs.", "in_progress", "high", "product", 0, 3),
            ("Review account recovery edge cases", "Confirm the support path for expired links and locked accounts.", "todo", "normal", "engineering", 2, 5),
            ("Prepare the November research readout", "Bring the interview themes and open questions into one review.", "completed", "normal", "product", 3, -2),
            ("Refine the workspace navigation", "Test the hierarchy against the task list and member directory.", "in_progress", "urgent", "design", 0, 1),
            ("Add export audit logging", "Record who generated an export and when, without storing its contents.", "blocked", "high", "engineering", 1, -1),
            ("Draft the release handoff checklist", "Capture owners, verification steps, and the support contact.", "todo", "low", "operations", 2, 8),
            ("Validate keyboard flow in task forms", "Check focus order, visible focus, and errors with keyboard only.", "in_progress", "high", "design", 6, 4),
            ("Document the API error contract", "Align response examples with the cases used by the client.", "todo", "normal", "engineering", 4, 10),
            ("Close the billing feedback loop", "Summarize unresolved customer questions for the next product review.", "todo", "urgent", "customer", 5, 2),
            ("Refresh the empty-state copy", "Make the first action clear when a list has no records.", "completed", "low", "product", 3, -5),
            ("Check mobile table overflow", "Verify filters and task actions remain reachable at narrow widths.", "in_progress", "normal", "design", 6, 6),
            ("Triage the permissions backlog", "Separate confirmed access issues from future policy questions.", "blocked", "urgent", "operations", 2, 0),
            ("Add timezone handling notes", "Clarify how dates are displayed and stored in the demo.", "todo", "low", "engineering", 1, 13),
            ("Review customer handoff notes", "Make sure each open request has a clear next owner.", "completed", "normal", "customer", 5, -1),
            ("Prototype the member capacity view", "Show assignments per person without implying tracked hours.", "todo", "high", "design", 0, 7),
            ("Verify seeded sample records", "Check that the demo dataset reads as illustrative rather than production data.", "completed", "normal", "operations", 2, -3),
            ("Consolidate status definitions", "Use the same labels in the app, admin, and documentation.", "todo", "normal", "product", 3, 11),
            ("Write the restore procedure", "Document a safe local backup and restore workflow for SQLite.", "in_progress", "low", "operations", 2, 15),
        ]
        tasks_created = 0
        for title, description, status, priority, category, member_index, day_offset in task_rows:
            assignee_email = members[member_index][1]
            _, created = Task.objects.get_or_create(
                title=title,
                defaults={
                    "description": description,
                    "status": status,
                    "priority": priority,
                    "category": category,
                    "assigned_to": member_by_email[assignee_email],
                    "due_date": today + timedelta(days=day_offset),
                },
            )
            tasks_created += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {members_created} team members and "
                f"{tasks_created} tasks created; existing sample records were kept."
            )
        )
        if settings.DEBUG:
            self.stdout.write(
                f"Local demo sign-in: {settings.DEMO_ACCOUNT_USERNAME} "
                "(existing account password was not changed)."
            )
