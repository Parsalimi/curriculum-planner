from django.core.management.base import BaseCommand
from planner.models import (
    Course,
    Curriculum,
    CurriculumCourse,
    RequirementCourse,
    RequirementGroup,
)


COURSES = [
    ("101", "Calculus I", 3, "First calculus course."),
    ("102", "Calculus II", 3, "Second calculus course."),
    ("103", "Differential Equations", 3, "Ordinary differential equations."),
    ("201", "Programming Fundamentals", 3, "Fundamentals of programming."),
    ("202", "Advanced Programming", 4, "Advanced programming concepts."),
    ("301", "Data Structures and Algorithms", 4, "Core data structures and algorithms."),
    ("302", "Database Systems", 4, "Relational databases and SQL."),
    ("303", "Computer Networks", 3, "Computer networking fundamentals."),
    ("304", "Operating Systems", 4, "Operating system concepts."),
    ("305", "Artificial Intelligence", 4, "Introduction to AI."),
    ("401", "Compiler Design", 3, "Principles of compiler construction."),
    ("501", "General English", 3, "General English."),
]

class Command(BaseCommand):
    help = "Create a small demo curriculum for local development."

    def handle(self, *args, **options):
        curriculum, _ = Curriculum.objects.get_or_create(
            name="Computer Science",
            degree="Bachelor's",
            version="MVP-2026",
            defaults={"minimum_credits": 139},
        )

        created = {}
        for code, name, credits, description in COURSES:
            course, _ = Course.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "credits": credits,
                    "description": description,
                    "is_active": True,
                },
            )
            created[code] = course

        mandatory_codes = {"101", "102", "103", "201", "202", "301", "304"}
        specialized_codes = {"202", "301", "302", "303", "304", "305"}
        general_codes = {"501"}
        elective_codes = {"401", "302", "303"}

        for code, course in created.items():
            if code in general_codes:
                category = CurriculumCourse.Category.GENERAL
            elif code in specialized_codes:
                category = CurriculumCourse.Category.SPECIALIZED
            elif code in elective_codes:
                category = CurriculumCourse.Category.ELECTIVE
            else:
                category = CurriculumCourse.Category.BASE

            CurriculumCourse.objects.update_or_create(
                curriculum=curriculum,
                course=course,
                defaults={
                    "category": category,
                    "recommended_semester": 1 if code in {"101", "201"} else 2,
                    "is_mandatory": code in mandatory_codes,
                },
            )

        # Example prerequisite: Data Structures -> Programming Fundamentals.
        cc = {
            cc.course.code: cc
            for cc in CurriculumCourse.objects.filter(curriculum=curriculum).select_related("course")
        }

        # Create requirement groups.
        base_group, _ = RequirementGroup.objects.get_or_create(
            curriculum=curriculum,
            name="Base mandatory courses",
            defaults={
                "type": RequirementGroup.Type.MANDATORY,
                "required_count": None,
                "required_credits": None,
            },
        )

        elective_group, _ = RequirementGroup.objects.get_or_create(
            curriculum=curriculum,
            name="Specialized / elective choices",
            defaults={
                "type": RequirementGroup.Type.CHOOSE_COUNT,
                "required_count": 2,
                "required_credits": None,
            },
        )

        for code in mandatory_codes:
            if code in cc:
                RequirementCourse.objects.get_or_create(
                    curriculum_course=cc[code],
                    requirement_group=base_group,
                )

        for code in {"302", "303", "305"}:
            if code in cc:
                RequirementCourse.objects.get_or_create(
                    curriculum_course=cc[code],
                    requirement_group=elective_group,
                )

        self.stdout.write(self.style.SUCCESS(
            f"Demo curriculum ready: {curriculum} ({curriculum.id})"
        ))
