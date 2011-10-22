from django.contrib import admin

from .models import Project, Configuration, Value, MetaBuild, Build


class ConfigurationInline(admin.TabularInline):
    model = Configuration
    extra = 0


class ValueInline(admin.TabularInline):
    model = Value


class BuildInline(admin.TabularInline):
    model = Build
    extra = 0


class ProjectAdmin(admin.ModelAdmin):
    inlines = [ConfigurationInline]
    list_display = ('name', 'repo_type', 'sequential', 'latest_revision')


class ConfigurationAdmin(admin.ModelAdmin):
    inlines = [ValueInline]


class BuildAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'status')
    list_filter = ('status',)


class MetaBuildAdmin(admin.ModelAdmin):
    inlines = [BuildInline]
    list_display = ('__unicode__', 'revision', 'creation_date')


admin.site.register(Project, ProjectAdmin)
admin.site.register(Configuration, ConfigurationAdmin)
admin.site.register(Build, BuildAdmin)
admin.site.register(MetaBuild, MetaBuildAdmin)
