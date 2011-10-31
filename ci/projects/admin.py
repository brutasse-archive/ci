from django.contrib import admin

from .models import Project, Configuration, Value, Build, Job


class ConfigurationInline(admin.TabularInline):
    model = Configuration
    extra = 0


class ValueInline(admin.TabularInline):
    model = Value


class JobInline(admin.TabularInline):
    model = Job
    extra = 0


class ProjectAdmin(admin.ModelAdmin):
    inlines = [ConfigurationInline]
    list_display = ('name', 'repo_type', 'sequential', 'latest_revision')


class ConfigurationAdmin(admin.ModelAdmin):
    inlines = [ValueInline]


class JobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'status')
    list_filter = ('status',)


class BuildAdmin(admin.ModelAdmin):
    inlines = [JobInline]
    list_display = ('__unicode__', 'revision', 'creation_date')


admin.site.register(Project, ProjectAdmin)
admin.site.register(Configuration, ConfigurationAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(Build, BuildAdmin)
