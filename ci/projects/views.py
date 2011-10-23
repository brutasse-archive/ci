from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _
from django.views import generic

from .forms import ProjectForm, ProjectBuildForm, ConfigurationFormSet
from .models import Project, MetaBuild


class Projects(generic.ListView):
    model = Project
projects = Projects.as_view()


class ProjectDetails(generic.DetailView):
    model = Project
project = ProjectDetails.as_view()


class BuildDetails(generic.DetailView):
    model = MetaBuild
build = BuildDetails.as_view()


class AddProject(generic.CreateView):
    model = Project
    form_class = ProjectForm

    def get_success_url(self):
        return reverse('project_admin', args=[self.object.slug])

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.slug = slugify(self.object.name)
        self.object.save()
        messages.success(self.request, _('%s has been successfully created. '
                                         'You may review the build '
                                         'configuration now.'))
        return redirect(self.get_success_url())
add_project = AddProject.as_view()


class ProjectAdmin(generic.UpdateView):
    model = Project
    form_class = ProjectBuildForm
    template_name = 'projects/project_admin_form.html'

    def get_context_data(self, **kwargs):
        ctx = super(ProjectAdmin, self).get_context_data(**kwargs)
        ctx.update({
            'formset': ConfigurationFormSet(initial=self.object.axis_initial())
        })
        return ctx

    def form_valid(self, form):
        response = super(ProjectAdmin, self).form_valid(form)
        messages.success(
            self.request,
            _('%s has been successfully updated') % self.object.name,
        )
        return response
project_admin = ProjectAdmin.as_view()


class ProjectAxis(generic.FormView):
    form_class = ConfigurationFormSet
    template_name = 'projects/project_admin_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, slug=kwargs['slug'])
        return super(ProjectAxis, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        return self.project.axis_initial()

    def get_context_data(self, **kwargs):
        ctx = super(ProjectAxis, self).get_context_data(**kwargs)
        # Make the context behave like ProjectAdmin's context, we use
        # the same template
        ctx['formset'] = ctx['form']
        ctx['form'] = ProjectBuildForm(instance=self.project)
        ctx['object'] = self.project
        return ctx

    def form_valid(self, form):
        # Remove empty forms
        data = [f for f in form.cleaned_data if f]

        # clean existing axis
        axis_list = [f['name'] for f in data]
        self.project.configurations.exclude(key__in=axis_list).delete()
        for axis in data:
            if axis.get('delete', False):
                self.project.configurations.get(key=axis['name']).delete()
                continue
            config, created = self.project.configurations.get_or_create(
                key=axis['name'],
            )

            # clean existing values
            config.values.exclude(value__in=axis['values']).delete()
            for value in axis['values']:
                val, created = config.values.get_or_create(
                    value=value,
                )
        messages.success(self.request,
                         _('Build axis have been successfully updated.'))
        return super(ProjectAxis, self).form_valid(form)

    def get_success_url(self):
        return reverse('project', args=[self.project.slug])
project_axis = ProjectAxis.as_view()
