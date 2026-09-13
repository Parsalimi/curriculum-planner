import json
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Course, Curriculum, CurriculumCourse, RequirementCourse, RequirementGroup, StudentCourse
from .views import _get_curriculum_stats


class StatusPageToggleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="secret123")
        self.curriculum = Curriculum.objects.create(
            name="Computer Science",
            degree="BSc",
            version="1403",
            minimum_credits=140,
        )
        self.course = Course.objects.create(
            code="CS-101",
            name="Programming",
            credits=3,
            description="",
            is_active=True,
        )
        self.curriculum_course = CurriculumCourse.objects.create(
            curriculum=self.curriculum,
            course=self.course,
            category=CurriculumCourse.Category.BASE,
            recommended_semester=1,
            is_mandatory=True,
        )
        self.requirement_group = RequirementGroup.objects.create(
            curriculum=self.curriculum,
            name="دروس پایه",
            type=RequirementGroup.Type.MANDATORY,
            required_count=None,
            required_credits=None,
        )
        RequirementCourse.objects.create(
            curriculum_course=self.curriculum_course,
            requirement_group=self.requirement_group,
        )

    def test_toggle_course_status_updates_student_course_and_returns_group_stats(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/status/toggle/",
            data=json.dumps({"curriculum_course_id": self.curriculum_course.id, "passed": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        tracking = StudentCourse.objects.get(
            student=self.user,
            curriculum_course=self.curriculum_course,
        )
        self.assertEqual(tracking.status, StudentCourse.Status.PASSED)
        self.assertEqual(response.json()["overall"]["completed_units"], 3)
        self.assertEqual(response.json()["group"]["completed_units"], 3)

    def test_group_progress_is_capped_and_mandatory_courses_block_completion(self):
        mandatory_course = Course.objects.create(
            code="CS-102",
            name="Algorithms",
            credits=5,
            description="",
            is_active=True,
        )
        mandatory_cc = CurriculumCourse.objects.create(
            curriculum=self.curriculum,
            course=mandatory_course,
            category=CurriculumCourse.Category.BASE,
            recommended_semester=1,
            is_mandatory=True,
        )
        optional_course_1 = Course.objects.create(
            code="CS-103",
            name="Data Structures",
            credits=10,
            description="",
            is_active=True,
        )
        optional_cc_1 = CurriculumCourse.objects.create(
            curriculum=self.curriculum,
            course=optional_course_1,
            category=CurriculumCourse.Category.BASE,
            recommended_semester=2,
            is_mandatory=False,
        )
        optional_course_2 = Course.objects.create(
            code="CS-104",
            name="Databases",
            credits=10,
            description="",
            is_active=True,
        )
        optional_cc_2 = CurriculumCourse.objects.create(
            curriculum=self.curriculum,
            course=optional_course_2,
            category=CurriculumCourse.Category.BASE,
            recommended_semester=2,
            is_mandatory=False,
        )
        optional_course_3 = Course.objects.create(
            code="CS-105",
            name="Operating Systems",
            credits=5,
            description="",
            is_active=True,
        )
        optional_cc_3 = CurriculumCourse.objects.create(
            curriculum=self.curriculum,
            course=optional_course_3,
            category=CurriculumCourse.Category.BASE,
            recommended_semester=2,
            is_mandatory=False,
        )
        self.requirement_group.required_credits = 20
        self.requirement_group.save()

        for item in [mandatory_cc, optional_cc_1, optional_cc_2, optional_cc_3]:
            RequirementCourse.objects.get_or_create(
                curriculum_course=item,
                requirement_group=self.requirement_group,
            )

        StudentCourse.objects.create(
            student=self.user,
            curriculum_course=optional_cc_1,
            status=StudentCourse.Status.PASSED,
        )
        StudentCourse.objects.create(
            student=self.user,
            curriculum_course=optional_cc_2,
            status=StudentCourse.Status.PASSED,
        )
        StudentCourse.objects.create(
            student=self.user,
            curriculum_course=optional_cc_3,
            status=StudentCourse.Status.PASSED,
        )

        request = SimpleNamespace(user=self.user, session={})
        stats = _get_curriculum_stats(request, self.curriculum)
        group = next(item for item in stats["groups"] if item["group"].id == self.requirement_group.id)

        self.assertEqual(group["completed_units"], 25)
        self.assertEqual(group["progress"], 100)
        self.assertFalse(group["is_complete"])

    def test_overflow_destination_tracks_transferred_credit_units(self):
        source_group = RequirementGroup.objects.create(
            curriculum=self.curriculum,
            name="Group A",
            type=RequirementGroup.Type.CHOOSE_CREDITS,
            required_credits=20,
        )
        destination_group = RequirementGroup.objects.create(
            curriculum=self.curriculum,
            name="Group B",
            type=RequirementGroup.Type.CHOOSE_CREDITS,
            required_credits=20,
        )
        source_group.overflow_to = destination_group
        source_group.save()

        for code, credits in (("CS-201", 10), ("CS-202", 10), ("CS-203", 4)):
            course = Course.objects.create(
                code=code,
                name=code,
                credits=credits,
                description="",
                is_active=True,
            )
            curriculum_course = CurriculumCourse.objects.create(
                curriculum=self.curriculum,
                course=course,
                category=CurriculumCourse.Category.ELECTIVE,
                recommended_semester=1,
                is_mandatory=False,
            )
            RequirementCourse.objects.create(
                curriculum_course=curriculum_course,
                requirement_group=source_group,
            )
            StudentCourse.objects.create(
                student=self.user,
                curriculum_course=curriculum_course,
                status=StudentCourse.Status.PASSED,
            )

        request = SimpleNamespace(user=self.user, session={})
        stats = _get_curriculum_stats(request, self.curriculum)
        source = next(item for item in stats["groups"] if item["group"].id == source_group.id)
        destination = next(item for item in stats["groups"] if item["group"].id == destination_group.id)

        self.assertEqual(source["completed_units"], 24)
        self.assertEqual(source["progress"], 100)
        self.assertEqual(destination["completed_units"], 4)
        self.assertEqual(destination["progress"], 20)
