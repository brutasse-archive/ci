from django.contrib import messages
from django.shortcuts import redirect
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _
from django.views import generic

from .forms import ProjectForm
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
    form_class = ProjectForm
project_admin = ProjectAdmin.as_view()
