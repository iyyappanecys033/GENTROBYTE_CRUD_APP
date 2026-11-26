from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import TaskForm, TeamMemberForm
from .models import Task, TeamMember


class TaskModelAndFormTests(TestCase):
    def setUp(self):
        self.member = TeamMember.objects.create(
            name="Maya Chen",
            email="maya@example.test",
            role="Designer",
            department="Product",
        )

    def test_task_creation_and_overdue_state(self):
        task = Task.objects.create(
            title="Review onboarding",
            status=Task.Status.IN_PROGRESS,
            assigned_to=self.member,
            due_date=timezone.localdate() - timedelta(days=1),
        )

        self.assertEqual(task.assigned_to, self.member)
        self.assertTrue(task.is_overdue)
        self.assertIsNotNone(task.created_at)
        self.assertIsNotNone(task.updated_at)

    def test_completed_task_is_not_overdue(self):
        task = Task.objects.create(
            title="Completed review",
            status=Task.Status.COMPLETED,
            due_date=timezone.localdate() - timedelta(days=1),
        )

        self.assertFalse(task.is_overdue)

    def test_task_form_normalizes_title(self):
        form = TaskForm(
            data={
                "title": "  Review   onboarding  ",
                "description": "",
                "status": Task.Status.TODO,
                "priority": Task.Priority.NORMAL,
                "category": "product",
                "assigned_to": self.member.pk,
                "due_date": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["title"], "Review onboarding")

    def test_inactive_member_cannot_be_assigned_to_new_task(self):
        self.member.is_active = False
        self.member.save()
        form = TaskForm(
            data={
                "title": "Assign inactive member",
                "description": "",
                "status": Task.Status.TODO,
                "priority": Task.Priority.NORMAL,
                "category": "product",
                "assigned_to": self.member.pk,
                "due_date": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("assigned_to", form.errors)

    def test_member_email_is_normalized_and_duplicates_are_rejected(self):
        form = TeamMemberForm(
            data={
                "name": "  Maya   Chen ",
                "email": "MAYA@example.test",
                "role": "Designer",
                "department": "Product",
                "is_active": "on",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class TaskCrudTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="manager",
            password="secure-demo-pass",
        )
        self.client.force_login(self.user)
        self.member = TeamMember.objects.create(
            name="Theo Martin",
            email="theo@example.test",
            role="Engineer",
            department="Engineering",
        )
        self.task = Task.objects.create(
            title="Prepare release notes",
            description="Summarize the changes for review.",
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.HIGH,
            category="engineering",
            assigned_to=self.member,
            due_date=timezone.localdate() + timedelta(days=2),
        )

    def task_data(self, **overrides):
        data = {
            "title": "Prepare release notes",
            "description": "Summarize the changes for review.",
            "status": Task.Status.IN_PROGRESS,
            "priority": Task.Priority.HIGH,
            "category": "engineering",
            "assigned_to": self.member.pk,
            "due_date": (timezone.localdate() + timedelta(days=2)).isoformat(),
        }
        data.update(overrides)
        return data

    def test_list_and_detail_render(self):
        response = self.client.get(reverse("tasks:task_list"))
        detail = self.client.get(
            reverse("tasks:task_detail", kwargs={"pk": self.task.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prepare release notes")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Summarize the changes for review.")

    def test_empty_state_is_actionable(self):
        self.task.delete()
        response = self.client.get(reverse("tasks:task_list"))

        self.assertContains(response, "Your run sheet is clear")
        self.assertContains(response, "Create a task")

    def test_search_and_filters_narrow_the_run_sheet(self):
        Task.objects.create(title="Another task", category="design")
        response = self.client.get(
            reverse("tasks:task_list"),
            {"q": "Theo", "status": Task.Status.IN_PROGRESS, "priority": Task.Priority.HIGH},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["tasks"]), [self.task])

    def test_create_requires_valid_data_and_redirects_to_detail(self):
        invalid = self.client.post(
            reverse("tasks:task_create"),
            self.task_data(title="   "),
        )
        response = self.client.post(
            reverse("tasks:task_create"),
            self.task_data(title="Plan the review"),
            follow=True,
        )

        self.assertEqual(invalid.status_code, 200)
        self.assertContains(invalid, "Enter a short, action-oriented task title.")
        created = Task.objects.get(title="Plan the review")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], created.get_absolute_url())
        self.assertContains(response, "Plan the review")
        self.assertContains(response, "Task created and added to the run sheet.")

    def test_update_saves_changes(self):
        response = self.client.post(
            reverse("tasks:task_update", kwargs={"pk": self.task.pk}),
            self.task_data(title="Updated release notes", status=Task.Status.COMPLETED),
        )

        self.task.refresh_from_db()
        self.assertRedirects(response, self.task.get_absolute_url())
        self.assertEqual(self.task.title, "Updated release notes")
        self.assertEqual(self.task.status, Task.Status.COMPLETED)

    def test_delete_uses_confirmation_page_and_post(self):
        url = reverse("tasks:task_delete", kwargs={"pk": self.task.pk})
        confirmation = self.client.get(url)

        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "cannot be undone")
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        response = self.client.post(url)

        self.assertRedirects(response, reverse("tasks:task_list"))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_list_paginates_and_preserves_filters(self):
        Task.objects.bulk_create(
            [
                Task(title=f"Task {index:02}", assigned_to=self.member)
                for index in range(11)
            ]
        )
        response = self.client.get(reverse("tasks:task_list"), {"q": "Task", "page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertContains(response, "page=1")

    def test_csrf_is_required_for_state_changes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(
            reverse("tasks:task_delete", kwargs={"pk": self.task.pk})
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())


class TeamMemberCrudTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="manager",
            password="secure-demo-pass",
        )
        self.client.force_login(self.user)
        self.member = TeamMember.objects.create(
            name="Ari Patel",
            email="ari@example.test",
            role="Operations lead",
            department="Operations",
        )

    def member_data(self, **overrides):
        data = {
            "name": "Ari Patel",
            "email": "ari@example.test",
            "role": "Operations lead",
            "department": "Operations",
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def test_member_list_and_detail_render(self):
        response = self.client.get(reverse("tasks:member_list"))
        detail = self.client.get(
            reverse("tasks:member_detail", kwargs={"pk": self.member.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ari Patel")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "ari@example.test")

    def test_empty_directory_has_a_clear_action(self):
        self.member.delete()
        response = self.client.get(reverse("tasks:member_list"))

        self.assertContains(response, "Your directory is empty")
        self.assertContains(response, "Add a person")

    def test_create_and_update_member(self):
        created_response = self.client.post(
            reverse("tasks:member_create"),
            self.member_data(name="Nina Okafor", email="NINA@example.test"),
        )
        created = TeamMember.objects.get(email="nina@example.test")
        updated_response = self.client.post(
            reverse("tasks:member_update", kwargs={"pk": created.pk}),
            self.member_data(
                name="Nina Okafor",
                email="nina@example.test",
                department="Research",
            ),
        )

        self.assertRedirects(created_response, reverse("tasks:member_detail", kwargs={"pk": created.pk}))
        self.assertRedirects(updated_response, reverse("tasks:member_list"))
        created.refresh_from_db()
        self.assertEqual(created.department, "Research")

    def test_member_with_tasks_cannot_be_deleted(self):
        Task.objects.create(title="Keep history", assigned_to=self.member)
        url = reverse("tasks:member_delete", kwargs={"pk": self.member.pk})
        confirmation = self.client.get(url)
        self.assertContains(confirmation, "deactivate them instead")
        self.assertNotContains(confirmation, "Delete permanently")
        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(TeamMember.objects.filter(pk=self.member.pk).exists())
        self.assertContains(response, "still has task history")

    def test_unassigned_member_can_be_deleted_after_confirmation(self):
        url = reverse("tasks:member_delete", kwargs={"pk": self.member.pk})
        confirmation = self.client.get(url)

        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "Delete permanently")
        response = self.client.post(url)

        self.assertRedirects(response, reverse("tasks:member_list"))
        self.assertFalse(TeamMember.objects.filter(pk=self.member.pk).exists())


class AuthenticationTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_data_creates_local_demo_account_and_login_page_shows_it(self):
        call_command("seed_data", verbosity=0)
        user = get_user_model().objects.get(username="demo")

        self.assertTrue(user.check_password("GentrobyteDemo!2026"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        login_page = self.client.get(reverse("accounts:login"))
        self.assertContains(login_page, "Local demo access")
        self.assertContains(login_page, "GentrobyteDemo!2026")

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "demo", "password": "GentrobyteDemo!2026"},
        )
        self.assertRedirects(response, reverse("tasks:task_list"))

    @override_settings(DEBUG=False)
    def test_seed_data_does_not_create_demo_account_outside_debug_mode(self):
        call_command("seed_data", verbosity=0)
        self.assertFalse(
            get_user_model().objects.filter(username="demo").exists()
        )

    def test_workspace_pages_require_sign_in(self):
        response = self.client.get(reverse("tasks:task_list"))
        member_response = self.client.get(reverse("tasks:member_list"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('tasks:task_list')}",
        )
        self.assertRedirects(
            member_response,
            f"{reverse('accounts:login')}?next={reverse('tasks:member_list')}",
        )

    def test_login_and_logout(self):
        get_user_model().objects.create_user(
            username="manager",
            password="secure-demo-pass",
        )
        login_page = self.client.get(reverse("accounts:login"))
        login_response = self.client.post(
            reverse("accounts:login"),
            {"username": "manager", "password": "secure-demo-pass"},
        )

        self.assertEqual(login_page.status_code, 200)
        self.assertContains(login_page, "Sign in to your workspace")
        self.assertRedirects(login_response, reverse("tasks:task_list"))

        logout_response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(logout_response, reverse("accounts:login"))
        self.assertRedirects(
            self.client.get(reverse("tasks:task_list")),
            f"{reverse('accounts:login')}?next={reverse('tasks:task_list')}",
        )
