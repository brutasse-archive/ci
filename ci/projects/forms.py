import floppyforms as forms

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ['slug', 'keep_build_data', 'sequential']
        widgets = {
            'name': forms.TextInput,
            'repo': forms.TextInput,
            'repo_type': forms.Select,
            'build_instructions': forms.Textarea,
        }
