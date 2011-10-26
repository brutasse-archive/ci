from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns('',
    url(r'^$', views.projects, name='projects'),

    url(r'^add/$', views.add_project, name='add_project'),

    url(r'^project/(?P<slug>[\w_-]+)/admin/$',
        views.project_admin, name='project_admin'),

    url(r'^project/(?P<slug>[\w_-]+)/axis/$',
        views.project_axis, name='project_axis'),

    url(r'^project/(?P<slug>[\w_-]+)/build/$',
        views.project_trigger_build, name='project_trigger_build'),

    url(r'^project/(?P<slug>[\w_-]+)/builds/(?P<pk>\d+)/delete/$',
        views.delete_build, name='delete_build'),

    url(r'^project/(?P<slug>[\w_-]+)/builds/(?P<pk>\d+)/$',
        views.project_build, name='project_build'),

    url(r'^project/(?P<slug>[\w_-]+)/builds/$',
        views.project_builds, name='project_builds'),

    url(r'^project/(?P<slug>[\w_-]+)/$', views.project, name='project'),

    url(r'^build/(?P<pk>\d+)/$', views.build, name='build'),
)
