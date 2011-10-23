from django.forms.formsets import formset_factory, BaseFormSet
from django.utils.translation import ugettext_lazy as _

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


class ProjectBuildForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['build_instructions', 'sequential', 'keep_build_data']
        widgets = {
            'build_instructions': forms.Textarea,
            'sequential': forms.CheckboxInput,
            'keep_build_data': forms.CheckboxInput,
        }


class ConfigurationForm(forms.Form):
    name = forms.CharField(label=_('Name'))
    values = forms.CharField(label=_('Values'),
                             help_text=_('Comma-separated list of values'))

    def clean_values(self):
        values = self.cleaned_data['values']
        values = [v.strip() for v in values.split(',')]
        # unique values -- not strictly necessary but avoids queries for later
        return list(set(values))


class DeletionFormSet(BaseFormSet):
    def add_fields(self, form, index):
        super(DeletionFormSet, self).add_fields(form, index)
        if form.initial:
            form.fields['delete'] = forms.BooleanField(
                label=_('Delete this axis?'),
                required=False,
            )
        else:
            form.fields['name'].required = False
            form.fields['name'].widget.is_required = False
            form.fields['values'].required = False
            form.fields['values'].widget.is_required = False


ConfigurationFormSet = formset_factory(ConfigurationForm, extra=1,
                                       formset=DeletionFormSet)
