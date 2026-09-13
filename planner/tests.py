import json

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Course, Curriculum, CurriculumCourse, RequirementCourse, RequirementGroup, StudentCourse


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
