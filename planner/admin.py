from django.contrib import admin
from .models import (
    Course,
    Curriculum,
    CurriculumCourse,
    Prerequisite,
    RequirementGroup,
    RequirementCourse,
    StudentCourse,
)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "credits", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ("name", "degree", "version", "minimum_credits")
    search_fields = ("name", "degree", "version")


@admin.register(CurriculumCourse)
class CurriculumCourseAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "curriculum",
        "category",
        "credits",
        "recommended_semester",
        "is_mandatory",
    )
    list_filter = ("curriculum", "category", "is_mandatory")
    search_fields = ("course__code", "course__name")

    @admin.display(description="Credits")
    def credits(self, obj):
        return obj.course.credits


@admin.register(Prerequisite)
class PrerequisiteAdmin(admin.ModelAdmin):
    list_display = ("course", "prerequisite")
    search_fields = ("course__name", "course__code", "prerequisite__name")


@admin.register(RequirementGroup)
class RequirementGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "curriculum",
        "type",
        "required_count",
        "required_credits",
    )
    list_filter = ("curriculum", "type")
    search_fields = ("name",)


@admin.register(RequirementCourse)
class RequirementCourseAdmin(admin.ModelAdmin):
    list_display = ("requirement_group", "curriculum_course")
    list_filter = ("requirement_group__curriculum",)
    search_fields = ("curriculum_course__course__name", "curriculum_course__course__code")


@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ("student", "curriculum_course", "status", "grade")
    list_filter = ("status",)
    search_fields = ("student__username", "curriculum_course__course__name")
