from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import TaskForm, TeamMemberForm
from .models import Task, TeamMember
from .services import get_due_windows, get_task_metrics


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"
    paginate_by = 10

    def get_queryset(self):
        queryset = Task.objects.select_related("assigned_to")
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        priority = self.request.GET.get("priority", "")
        sort = self.request.GET.get("sort", "due_date")

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(category__icontains=query)
                | Q(assigned_to__name__icontains=query)
            )
        if status in Task.Status.values:
            queryset = queryset.filter(status=status)
        if priority in Task.Priority.values:
            queryset = queryset.filter(priority=priority)
        due_window = self.request.GET.get("due", "")
        today = timezone.localdate()
        if due_window == "overdue":
            queryset = queryset.filter(
                due_date__lt=today
            ).exclude(status=Task.Status.COMPLETED)
        elif due_window == "today":
            queryset = queryset.filter(
                due_date=today
            ).exclude(status=Task.Status.COMPLETED)
        elif due_window == "week":
            queryset = queryset.filter(
                due_date__gt=today,
                due_date__lte=today + timedelta(days=7),
            ).exclude(status=Task.Status.COMPLETED)
        elif due_window == "later":
            queryset = queryset.filter(due_date__gt=today + timedelta(days=7)).exclude(
                status=Task.Status.COMPLETED
            )

        sort_fields = {
            "title": "title",
            "-title": "-title",
            "priority": "priority",
            "-priority": "-priority",
            "status": "status",
            "-status": "-status",
        }
        if sort in {"due_date", "-due_date"}:
            queryset = queryset.annotate(
                completion_order=Case(
                    When(status=Task.Status.COMPLETED, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            due_order = (
                F("due_date").desc(nulls_last=True)
                if sort == "-due_date"
                else F("due_date").asc(nulls_last=True)
            )
            return queryset.order_by("completion_order", due_order, "title")
        return queryset.order_by(sort_fields.get(sort, "title"), "title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "metrics": get_task_metrics(),
                "due_windows": get_due_windows(),
                "status_choices": Task.Status.choices,
                "priority_choices": Task.Priority.choices,
                "active_filters": any(
                    self.request.GET.get(key)
                    for key in ("q", "status", "priority", "due")
                ),
            }
        )
        return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Task created and added to the run sheet.")
        return super().form_valid(form)


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    context_object_name = "task"

    def form_valid(self, form):
        messages.success(self.request, "Task details saved.")
        return super().form_valid(form)


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = "tasks/task_confirm_delete.html"
    success_url = reverse_lazy("tasks:task_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, "Task deleted.")
        return super().form_valid(form)


class TeamMemberListView(LoginRequiredMixin, ListView):
    model = TeamMember
    template_name = "tasks/member_list.html"
    context_object_name = "members"
    paginate_by = 12

    def get_queryset(self):
        queryset = TeamMember.objects.annotate(task_count=Count("tasks"))
        query = self.request.GET.get("q", "").strip()
        activity = self.request.GET.get("activity", "")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(email__icontains=query)
                | Q(role__icontains=query)
                | Q(department__icontains=query)
            )
        if activity == "active":
            queryset = queryset.filter(is_active=True)
        elif activity == "inactive":
            queryset = queryset.filter(is_active=False)
        return queryset.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_count"] = TeamMember.objects.filter(is_active=True).count()
        return context


class TeamMemberDetailView(LoginRequiredMixin, DetailView):
    model = TeamMember
    template_name = "tasks/member_detail.html"
    context_object_name = "member"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_tasks = self.object.tasks.select_related("assigned_to").order_by(
            "due_date", "title"
        )
        context["task_count"] = member_tasks.count()
        context["tasks"] = member_tasks[:8]
        return context


class TeamMemberCreateView(LoginRequiredMixin, CreateView):
    model = TeamMember
    form_class = TeamMemberForm
    template_name = "tasks/member_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Team member added to the directory.")
        return super().form_valid(form)


class TeamMemberUpdateView(LoginRequiredMixin, UpdateView):
    model = TeamMember
    form_class = TeamMemberForm
    template_name = "tasks/member_form.html"
    context_object_name = "member"
    success_url = reverse_lazy("tasks:member_list")

    def form_valid(self, form):
        messages.success(self.request, "Team member details saved.")
        return super().form_valid(form)


class TeamMemberDeleteView(LoginRequiredMixin, DeleteView):
    model = TeamMember
    template_name = "tasks/member_confirm_delete.html"
    success_url = reverse_lazy("tasks:member_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete"] = not self.object.tasks.exists()
        context["delete_message"] = (
            "This person has no assigned tasks and can be removed from the directory."
            if context["can_delete"]
            else "This person still has task history; deactivate them instead of removing the record."
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.tasks.exists():
            messages.error(
                request,
                "This person still has task history. Deactivate them instead of deleting.",
            )
            return redirect("tasks:member_detail", pk=self.object.pk)
        messages.success(request, "Team member removed.")
        return super().post(request, *args, **kwargs)
from datetime import timedelta
