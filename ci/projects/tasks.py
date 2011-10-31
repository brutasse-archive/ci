from celery.decorators import task

from .exceptions import BuildException
from .models import Job, Build, Project


@task(ignore_result=True)
def execute_job(build_id):
    try:
        Job.objects.get(pk=build_id).execute()
    except BuildException:
        pass  # It's being reported, task is complete.


@task(ignore_result=True)
def execute_build(build_id):
    """
    Sequential build.
    """
    build = Build.objects.get(pk=build_id)
    for job in build.jobs.all():
        try:
            job.execute()
        except BuildException:
            pass


@task(ignore_result=True)
def clone_on_creation(project_id):
    Project.objects.get(pk=project_id).update_source()
