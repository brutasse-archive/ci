from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns('',
    url(r'^$', views.projects, name='projects'),
    url(r'^add/$', views.add_project, name='add_project'),
    url(r'^project/(?P<slug>[\w_-]+)/$', views.project, name='project'),
    url(r'^build/(?P<pk>\d+)/$', views.build, name='build'),
)
