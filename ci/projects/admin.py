from django.contrib import admin

from .models import Project, Configuration, Value, Build


class ConfigurationInline(admin.TabularInline):
    model = Configuration
    extra = 0


class ValueInline(admin.TabularInline):
    model = Value


class ProjectAdmin(admin.ModelAdmin):
    inlines = [ConfigurationInline]


class ConfigurationAdmin(admin.ModelAdmin):
    inlines = [ValueInline]


class BuildAdmin(admin.ModelAdmin):
    pass


admin.site.register(Project, ProjectAdmin)
admin.site.register(Configuration, ConfigurationAdmin)
admin.site.register(Build, BuildAdmin)
