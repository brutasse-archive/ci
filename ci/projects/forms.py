from django.forms.formsets import formset_factory, BaseFormSet
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

import floppyforms as forms

from dulwich.client import get_transport_and_path, SubprocessGitClient
from mercurial import hg, ui
from mercurial.error import RepoError

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'repo', 'repo_type', 'build_instructions']
        widgets = {
            'name': forms.TextInput,
            'repo': forms.TextInput,
            'repo_type': forms.Select,
            'build_instructions': forms.Textarea,
        }

    def clean_name(self):
        slug_candidate = slugify(self.cleaned_data['name'])
        existing = Project.objects.filter(slug=slug_candidate)
        if existing:
            raise forms.ValidationError(
                _('This name conflicts with an existing "%s" '
                  'project.') % existing[0].name
            )
        return self.cleaned_data['name']

    def clean(self):
        repo_type = self.cleaned_data.get('repo_type', None)
        repo = self.cleaned_data['repo']
        if repo_type is None:  # required field
            return self.cleaned_data

        getattr(self, 'validate_%s_url' % repo_type)(repo)
        return self.cleaned_data

    def validate_git_url(self, url):
        error = _("Invalid Git URL: '%s'") % url
        try:
            client, path = get_transport_and_path(url)
        except ValueError:
            raise forms.ValidationError(error)

        if isinstance(client, SubprocessGitClient):
            raise forms.ValidationError(error)

    def validate_hg_url(self, url):
        error = _("Invalid Hg URL: '%s'") % url
        source, branches = hg.parseurl(url)
        try:
            hg.repository(ui.ui(), source)
        except RepoError:
            raise forms.ValidationError(error)


class ProjectBuildForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['build_instructions', 'sequential', 'keep_build_data',
                  'xunit_xml_report']
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
