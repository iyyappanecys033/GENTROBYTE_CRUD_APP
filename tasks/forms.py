from django import forms
from django.db.models import Q

from .models import Task, TeamMember

FIELD_CLASS = (
    "block w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 "
    "text-sm text-slate-900 shadow-sm transition placeholder:text-slate-400 "
    "focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-100"
)
TEXTAREA_CLASS = FIELD_CLASS + " min-h-32 resize-y"


class AccessibleModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["aria-describedby"] = (
                f"id_{name}_help id_{name}_error"
            )


class TeamMemberForm(AccessibleModelForm):
    class Meta:
        model = TeamMember
        fields = ("name", "email", "role", "department", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "e.g. Maya Chen"}),
            "email": forms.EmailInput(attrs={"class": FIELD_CLASS, "placeholder": "maya@company.com"}),
            "role": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "e.g. Product designer"}),
            "department": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "e.g. Product"}),
            "is_active": forms.CheckboxInput(
                attrs={"class": "size-4 rounded border-slate-300 text-blue-700 focus:ring-blue-600"}
            ),
        }

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not name:
            raise forms.ValidationError("Enter a name so teammates can identify this person.")
        return name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        duplicates = TeamMember.objects.filter(email__iexact=email)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A team member with this email already exists.")
        return email


class TaskForm(AccessibleModelForm):
    class Meta:
        model = Task
        fields = (
            "title",
            "description",
            "status",
            "priority",
            "category",
            "assigned_to",
            "due_date",
        )
        widgets = {
            "title": forms.TextInput(
                attrs={"class": FIELD_CLASS, "placeholder": "e.g. Prepare the launch review"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "placeholder": "Add the context, outcome, or handoff details.",
                    "rows": 4,
                }
            ),
            "status": forms.Select(attrs={"class": FIELD_CLASS}),
            "priority": forms.Select(attrs={"class": FIELD_CLASS}),
            "category": forms.Select(attrs={"class": FIELD_CLASS}),
            "assigned_to": forms.Select(attrs={"class": FIELD_CLASS}),
            "due_date": forms.DateInput(attrs={"class": FIELD_CLASS, "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].error_messages["required"] = (
            "Enter a short, action-oriented task title."
        )
        eligible_members = TeamMember.objects.filter(is_active=True)
        if self.instance.pk and self.instance.assigned_to_id:
            eligible_members = TeamMember.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.assigned_to_id)
            )
        self.fields["assigned_to"].queryset = eligible_members.order_by("name")
        self.fields["assigned_to"].empty_label = "Unassigned"
        self.fields["assigned_to"].required = False

    def clean_title(self):
        title = " ".join(self.cleaned_data["title"].split())
        if not title:
            raise forms.ValidationError("Enter a short, action-oriented task title.")
        return title
