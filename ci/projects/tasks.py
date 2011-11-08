from celery.decorators import task

from ..exceptions import CommandError
from .models import Job, Project


@task(ignore_result=True)
def execute_job(job_id):
    try:
        Job.objects.get(pk=job_id).execute()
    except CommandError:
        pass  # It's being reported, task is complete.


@task(ignore_result=True)
def execute_jobs(job_ids):
    """
    Sequential build.
    """
    for job in Job.objects.filter(pk__in=job_ids):
        try:
            job.execute()
        except CommandError:
            pass


@task(ignore_result=True)
def clone_on_creation(project_id):
    Project.objects.get(pk=project_id).update_source()
