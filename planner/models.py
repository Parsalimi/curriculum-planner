from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    credits = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Curriculum(models.Model):
    name = models.CharField(max_length=200)
    degree = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    minimum_credits = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.name} - {self.version}"


class CurriculumCourse(models.Model):
    class Category(models.TextChoices):
        BASE = "BASE", "Base"
        SPECIALIZED = "SPECIALIZED", "Specialized"
        ELECTIVE = "ELECTIVE", "Elective"
        GENERAL = "GENERAL", "General"

    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name="curriculum_courses",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="curriculum_courses",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    recommended_semester = models.PositiveSmallIntegerField()
    is_mandatory = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["curriculum", "course"],
                name="unique_course_per_curriculum",
            )
        ]

    def __str__(self):
        return f"{self.curriculum} - {self.course}"


class Prerequisite(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="prerequisites",
    )
    prerequisite = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="required_for",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "prerequisite"],
                name="unique_prerequisite",
            ),
            models.CheckConstraint(
                condition=~Q(course=models.F("prerequisite")),
                name="course_cannot_require_itself",
            ),
        ]

    def __str__(self):
        return f"{self.prerequisite} → {self.course}"


class RequirementGroup(models.Model):
    class Type(models.TextChoices):
        MANDATORY = "MANDATORY", "Mandatory"
        CHOOSE_COUNT = "CHOOSE_COUNT", "Choose Count"
        CHOOSE_CREDITS = "CHOOSE_CREDITS", "Choose Credits"

    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name="requirement_groups",
    )
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=Type.choices)
    required_count = models.PositiveSmallIntegerField(null=True, blank=True)
    required_credits = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.curriculum} - {self.name}"


class RequirementCourse(models.Model):
    curriculum_course = models.ForeignKey(
        CurriculumCourse,
        on_delete=models.CASCADE,
        related_name="requirement_courses",
    )
    requirement_group = models.ForeignKey(
        RequirementGroup,
        on_delete=models.CASCADE,
        related_name="requirement_courses",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["curriculum_course", "requirement_group"],
                name="unique_course_per_requirement",
            )
        ]

    def __str__(self):
        return f"{self.requirement_group} - {self.curriculum_course.course}"


class StudentCourse(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        PASSED = "PASSED", "Passed"
        FAILED = "FAILED", "Failed"

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="student_courses",
    )
    curriculum_course = models.ForeignKey(
        CurriculumCourse,
        on_delete=models.CASCADE,
        related_name="student_courses",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    grade = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "curriculum_course"],
                name="unique_student_course",
            )
        ]

    def __str__(self):
        return f"{self.student.username} - {self.curriculum_course.course}"
