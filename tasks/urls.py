from django.urls import path

from .views import (
    TaskCreateView,
    TaskDeleteView,
    TaskDetailView,
    TaskListView,
    TaskUpdateView,
    TeamMemberCreateView,
    TeamMemberDeleteView,
    TeamMemberDetailView,
    TeamMemberListView,
    TeamMemberUpdateView,
)

app_name = "tasks"

urlpatterns = [
    path("", TaskListView.as_view(), name="task_list"),
    path("tasks/new/", TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task_detail"),
    path("tasks/<int:pk>/edit/", TaskUpdateView.as_view(), name="task_update"),
    path("tasks/<int:pk>/delete/", TaskDeleteView.as_view(), name="task_delete"),
    path("people/", TeamMemberListView.as_view(), name="member_list"),
    path("people/new/", TeamMemberCreateView.as_view(), name="member_create"),
    path("people/<int:pk>/", TeamMemberDetailView.as_view(), name="member_detail"),
    path(
        "people/<int:pk>/edit/",
        TeamMemberUpdateView.as_view(),
        name="member_update",
    ),
    path(
        "people/<int:pk>/delete/",
        TeamMemberDeleteView.as_view(),
        name="member_delete",
    ),
]
