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


class ConfigurationAdmin(admin.ModelAdmin):
    inlines = [ValueInline]


class BuildAdmin(admin.ModelAdmin):
    pass

class MetaBuildAdmin(admin.ModelAdmin):
    inlines = [BuildInline]


admin.site.register(Project, ProjectAdmin)
admin.site.register(Configuration, ConfigurationAdmin)
admin.site.register(Build, BuildAdmin)
admin.site.register(MetaBuild, MetaBuildAdmin)
