from celery.decorators import task

from .exceptions import BuildException
from .models import Build

@task(ignore_result=True)
def execute_build(build_id):
    try:
        Build.objects.get(pk=build_id).execute()
    except BuildException:
        pass  # It's being reported, task is complete.
