from django.contrib.auth.forms import AuthenticationForm


class WorkspaceLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            "block w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 "
            "text-sm text-slate-900 shadow-sm focus:border-blue-600 focus:outline-none "
            "focus:ring-4 focus:ring-blue-100"
        )
        self.fields["username"].widget.attrs.update(
            {"class": input_class, "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": input_class, "autocomplete": "current-password"}
        )
