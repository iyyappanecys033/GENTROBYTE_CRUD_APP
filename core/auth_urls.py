from django.contrib.auth import views as auth_views
from django.conf import settings
from django.urls import path

from .forms import WorkspaceLoginForm

app_name = "accounts"


class WorkspaceLoginView(auth_views.LoginView):
    authentication_form = WorkspaceLoginForm
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "show_demo_credentials": settings.DEBUG,
                "demo_username": settings.DEMO_ACCOUNT_USERNAME,
                "demo_password": settings.DEMO_ACCOUNT_PASSWORD,
            }
        )
        return context


urlpatterns = [
    path(
        "login/",
        WorkspaceLoginView.as_view(),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
