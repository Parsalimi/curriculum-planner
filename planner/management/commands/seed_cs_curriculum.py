from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User

from planner.models import (
    Course,
    Curriculum,
    CurriculumCourse,
    Prerequisite,
    RequirementGroup,
    RequirementCourse,
)


class Command(BaseCommand):
    help = "Seed the CS Bachelor curriculum data"

    @transaction.atomic
    def handle(self, *args, **options):
        # ------------------------------------------------------------------
        # 1) CURRICULUM
        # ------------------------------------------------------------------
        curriculum, _ = Curriculum.objects.update_or_create(
            name="کارشناسی علوم کامپیوتر",
            version="1400",
            defaults={
                "degree": "BSc",
                "minimum_credits": 139,
            },
        )

        # ------------------------------------------------------------------
        # 2) HELPER
        # ------------------------------------------------------------------
        def add_course(code, name, credits, category, semester,
                       mandatory=False, description=""):
            course, _ = Course.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "credits": credits,
                    "description": description,
                    "is_active": True,
                },
            )
            cc, _ = CurriculumCourse.objects.update_or_create(
                curriculum=curriculum,
                course=course,
                defaults={
                    "category": category,
                    "recommended_semester": semester,
                    "is_mandatory": mandatory,
                },
            )
            return course, cc

        # ------------------------------------------------------------------
        # 5) BASE COURSES (دروس پایه) — 7 mandatory + 1 elective
        # ------------------------------------------------------------------
        base_mandatory_group = RequirementGroup.objects.update_or_create(
                    curriculum=curriculum,
                    name="دروس پایه",
                    defaults={"type": "CHOOSE_COUNT", "required_count": 7,
                              "required_credits": 18},
        )[0]
        base_mandatory = [
            ("BA-MATH1", "ریاضی عمومی (1)", 3, 1),
            ("BA-MATH2", "ریاضی عمومی (2)", 3, 2),
            ("BA-DIFF", "معادلات دیفرانسیل", 3, 3),
            ("BA-COMP", "مبانی کامپیوتر و برنامه سازی", 3, 1),
            ("BA-PHYS1", "فیزیک عمومی (1)", 3, 1),
            ("BA-RESEARCH", "روش تحقیق و گزارش نویسی", 2, 5),
            ("BA-LAB", "کارگاه کامپیوتر", 1, 1),
        ]
        for code, name, cr, sem in base_mandatory:
            _, cc = add_course(code, name, cr, "BASE", sem, mandatory=True)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=base_mandatory_group
            )


        # Base elective: choose 1
        base_elective_group = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="دروس پایه انتخابی (1 درس)",
            defaults={"type": "CHOOSE_COUNT", "required_count": 1,
                      "required_credits": 3},
        )[0]
        base_electives = [
            ("BA-ECO", "مبانی اقتصاد", 3, 4),
            ("BA-PHYS2", "فیزیک عمومی (2)", 3, 3),
            ("BA-ACC", "اصول حسابداری و هزینه یابی", 3, 4),
            ("BA-MGMT", "اصول مدیریت", 3, 4),
        ]
        for code, name, cr, sem in base_electives:
            _, cc = add_course(code, name, cr, "BASE", sem)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=base_elective_group
            )


        # ------------------------------------------------------------------
        # 6) SPECIALIZED COURSES (دروس تخصصی) — 17 mandatory + 2 elective
        # ------------------------------------------------------------------
        spec_mandatory_group = RequirementGroup.objects.update_or_create(
                    curriculum=curriculum,
                    name="دروس تخصصی",
                    defaults={"type": "CHOOSE_COUNT", "required_count": 17,
                              "required_credits": 57},
        )[0]
        spec_mandatory = [
            ("SP-MATH", "مبانی علوم ریاضی", 3, 2),
            ("SP-MATRIX", "مبانی ماتریس ها و جبر خطی", 3, 2),
            ("SP-COMB", "مبانی ترکیبیات", 3, 3),
            ("SP-NUM", "مبانی آنالیز عددی", 3, 4),
            ("SP-PROB", "مبانی احتمال", 3, 4),
            ("SP-COMPTH", "مبانی نظریه محاسبه", 3, 4),
            ("SP-ADVPROG", "برنامه سازی پیشرفته", 4, 2),
            ("SP-DSA", "ساختمان داده ها و الگوریتم ها", 4, 3),
            ("SP-OS", "اصول سیستم های عامل", 4, 5),
            ("SP-NUMLIN", "جبر خطی عددی", 3, 4),
            ("SP-ARCH", "اصول سیستم های کامپیوتری", 4, 4),
            ("SP-LOGIC", "مبانی منطق و نظریه مجموعه ها", 3, 3),
            ("SP-ALGO", "طراحی و تحلیل الگوریتم ها", 3, 5),
            ("SP-LP", "بهینه سازی خطی", 3, 4),
            ("SP-COMPTH2", "نظریه محاسبه", 3, 5),
            ("SP-AI", "هوش مصنوعی", 4, 6),
            ("SP-SD", "اصول طراحی نرم افزار", 4, 6),
        ]
        spec_courses = {}
        for code, name, cr, sem in spec_mandatory:
            _, cc = add_course(code, name, cr, "SPECIALIZED", sem, mandatory=True)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=spec_mandatory_group
            )

        # Specialized elective: choose 2
        spec_elective_group = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="دروس تخصصی انتخابی (2 درس)",
            defaults={"type": "CHOOSE_COUNT", "required_count": 2,
                      "required_credits": 6},
        )[0]
        spec_electives = [
            ("SP-COMPILER", "کامپایلر", 3, 6),
            ("SP-DB", "پایگاه داده ها", 4, 5),
            ("SP-NET", "شبکه های کامپیوتری", 3, 5),
            ("SP-TOPICS", "مباحثی در علوم کامپیوتر", 3, 7),
            ("SP-NLP", "بهینه سازی غیر خطی", 3, 6),
            ("SP-GRAPH", "نظریه گراف و کاربرد ها", 3, 5),
            ("SP-NUMAN", "آنالیز عددی", 3, 6),
        ]
        for code, name, cr, sem in spec_electives:
            _, cc = add_course(code, name, cr, "SPECIALIZED", sem)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=spec_elective_group
            )


        # ------------------------------------------------------------------
        # 7) ELECTIVE COURSES (دروس اختیاری) — 30 credits
        # ------------------------------------------------------------------
        # دفاع مقدس is mandatory within electives
        elective_group = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="دروس اختیاری (30 واحد)",
            defaults={"type": "CHOOSE_CREDITS", "required_count": None,
                      "required_credits": 30},
        )[0]

        electives = [
            ("EL-CG", "طراحی هندسی کامپیوتری", 3),
            ("EL-SIM", "شبیه سازی کامپیوتری", 3),
            ("EL-DM", "مقدمه ای بر داده کاوی", 3),
            ("EL-PROJ", "پروژه", 3),
            ("EL-INT1", "کارآموزی 1", 2),
            ("EL-INT2", "کارآموزی 2", 2),
            ("EL-BIZ", "کاربرد کامپیوتر در سیستم های تجاری", 3),
            ("EL-COMBOPT", "بهینه سازی ترکیباتی و آنالیز شبکه ها", 3),
            ("EL-REAL", "مبانی آنالیز ریاضی", 3),
            ("EL-ALG", "مبانی جبر", 3),
            ("EL-CODE", "نظریه کد گذاری", 3),
            ("EL-PL", "زبان های برنامه سازی", 3),
            ("EL-GFX", "گرافیک کامپیوتری", 3),
            ("EL-LOGIC", "منطق", 3),
            ("EL-MIS", "سیستم های اطلاعاتی مدیریت", 3),
            ("EL-ENGMATH", "ریاضیات مهندسی", 3),
            ("EL-PROB1", "احتمال 1", 3),
            ("EL-BIO", "زیست شناسی سلولی و مولکولی", 2),
            ("EL-ALGTOP", "مباحثی در الگوریتم ها", 3),
            ("EL-BIOINF", "مبانی بیوانفورماتیک", 4),
            ("EL-ENTRE", "مبانی کارآفرینی", 2),
            ("EL-DEFAA", "دفاع مقدس", 2),   # mandatory
        ]
        for code, name, cr in electives:
            is_mand = (code == "EL-DEFAA")
            _, cc = add_course(code, name, cr, "ELECTIVE", 8,
                               mandatory=is_mand)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=elective_group
            )

        # ------------------------------------------------------------------
        # 3) GENERAL COURSES (دروس عمومی)  — 26 credits total
        # ------------------------------------------------------------------
        general_group = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="دروس عمومی",
            defaults={"type": "CHOOSE_CREDITS", "required_count": 6,
                      "required_credits": 8},
        )[0]
        general = [ # mandatory
                    ("GEN-FA", "زبان فارسی", 3, "GENERAL", 1),
                    # ("GEN-EN-PRE", "زبان انگلیسی پیش دانشگاهی-ترکیبی", 2, "GENERAL", 1),
                    ("GEN-EN-1", "زبان انگلیسی عمومی-ترکیبی (1)", 1, "GENERAL", 1),
                    ("GEN-EN-2", "زبان انگلیسی عمومی-ترکیبی (2)", 1, "GENERAL", 2),
                    ("GEN-EN-3", "زبان انگلیسی عمومی-ترکیبی (3)", 1, "GENERAL", 3),
                    ("GEN-PE-1", "تربیت بدنی 1", 1, "GENERAL", 1),
                    ("GEN-SPORT", "ورزش", 1, "GENERAL", 2),
        ]
        for code, name, cr, typ, sem in general:
                    _, cc = add_course(code, name, cr, typ, sem, mandatory=True)
                    RequirementCourse.objects.get_or_create(
                        curriculum_course=cc, requirement_group=general_group
                    )

        # ------------------------------------------------------------------
        # 4) GENERAL ELECTIVE BOXES (معارف)
        # ------------------------------------------------------------------
        # Box 1: choose 2
        box1 = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="معارف - باکس اول (2 درس)",
            defaults={"type": "CHOOSE_COUNT", "required_count": 2,
                      "required_credits": 4},
        )[0]
        box1_courses = [
            ("MA-AND1", "اندیشه 1", 2),
            ("MA-AND2", "اندیشه 2", 2),
            ("MA-ENSAN", "انسان در اسلام", 2),
            ("MA-HOGHOUGH", "حقوق اجتماعی و سیاسی در اسلام", 2),
        ]
        for code, name, cr in box1_courses:
            _, cc = add_course(code, name, cr, "GENERAL", 1)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=box1
            )

        # Box 2: choose 1 (اخلاق)
        box2 = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="معارف - باکس دوم (1 درس)",
            defaults={"type": "CHOOSE_COUNT", "required_count": 1,
                      "required_credits": 2},
        )[0]
        box2_courses = [
            ("MA-AKH1", "اخلاق اسلامی", 2),
            ("MA-AKH2", "اخلاق خانواده", 2),
            ("MA-AKH3", "فلسفه اخلاق", 2),
            ("MA-AKH4", "آیین زندگی", 2),
            ("MA-AKH5", "عرفان عملی در اسلام", 2),
        ]
        for code, name, cr in box2_courses:
            _, cc = add_course(code, name, cr, "GENERAL", 2)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=box2
            )

        # Box 3: choose 1 (انقلاب / قانون اساسی / اندیشه سیاسی)
        box3 = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="معارف - باکس سوم (1 درس)",
            defaults={"type": "CHOOSE_COUNT", "required_count": 1,
                      "required_credits": 2},
        )[0]
        box3_courses = [
            ("MA-ENQELAB", "انقلاب اسلامی ایران", 2),
            ("MA-GHANUN", "آشنایی با قانون اساسی جمهوری اسلامی", 2),
            ("MA-EMAM", "اندیشه سیاسی امام خمینی", 2),
        ]
        for code, name, cr in box3_courses:
            _, cc = add_course(code, name, cr, "GENERAL", 3)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=box3
            )

        # Box 4: choose 1 (تفسیر)
        box4 = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="معارف - باکس چهارم (1 درس)",
            defaults={"type": "CHOOSE_COUNT", "required_count": 1,
                      "required_credits": 2},
        )[0]
        box4_courses = [
            ("MA-TAFSIR-Q", "تفسیر موضوعی قرآن", 2),
            ("MA-TAFSIR-N", "تفسیر موضوعی نهج البلاغه", 2),
        ]
        for code, name, cr in box4_courses:
            _, cc = add_course(code, name, cr, "GENERAL", 4)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=box4
            )

        # Box 5: choose 2 (تاریخ / فرهنگ و تمدن اجباری / تاریخ امامت)
        box5 = RequirementGroup.objects.update_or_create(
            curriculum=curriculum,
            name="معارف - باکس پنجم (2 درس)",
            defaults={"type": "CHOOSE_COUNT", "required_count": 2,
                      "required_credits": 4},
        )[0]
        box5_courses = [
            ("MA-TARIKH-S", "تاریخ تحلیلی صدر اسلام", 2, False),
            ("MA-FARHANG", "فرهنگ و تمدن اسلام و ایران", 2, True),
            ("MA-TARIKH-E", "تاریخ امامت", 2, False),
        ]
        for code, name, cr, mand in box5_courses:
            _, cc = add_course(code, name, cr, "GENERAL", 5, mandatory=mand)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=box5
            )

        # Box 6:
        box6 = RequirementGroup.objects.update_or_create(
                    curriculum=curriculum,
                    name="معارف - باکس آخر (اجباری)",
                    defaults={"type": "CHOOSE_COUNT", "required_count": 3,
                              "required_credits": 4},
        )[0]
        box6_courses = [
            ("GEN-FAMILY", "دانش خانواده و جمعیت", 2, 4),
            ("GEN-QURAN-F", "انس با قرآن", 1, 1),
            ("GEN-VASIYA", "وصایا", 1, 8),
        ]
        for code, name, cr, sem in box6_courses:
            _, cc = add_course(code, name, cr, "GENERAL", sem, mandatory=True)
            RequirementCourse.objects.get_or_create(
                curriculum_course=cc, requirement_group=box6
            )
        # ------------------------------------------------------------------
        # 8) PREREQUISITES (sample — extend as needed)
        # ------------------------------------------------------------------
        prereq_pairs = [
            # (course_code, prerequisite_code)
            ("BA-MATH2", "BA-MATH1"),
            ("BA-DIFF", "BA-MATH2"),
            ("SP-ADVPROG", "BA-COMP"),
            ("SP-DSA", "SP-ADVPROG"),
            ("SP-ALGO", "SP-DSA"),
            ("SP-OS", "SP-ARCH"),
            ("SP-ARCH", "SP-DSA"),
            ("SP-AI", "SP-DSA"),
            ("SP-SD", "SP-ADVPROG"),
            ("SP-DB", "SP-DSA"),
            ("SP-NET", "SP-OS"),
            ("SP-COMPILER", "SP-DSA"),
            ("SP-MATRIX", "BA-MATH1"),
            ("SP-COMB", "SP-MATRIX"),
            ("SP-NUM", "BA-MATH2"),
            ("SP-PROB", "BA-MATH2"),
            ("SP-LP", "SP-MATRIX"),
            ("SP-NUMLIN", "SP-MATRIX"),
            ("SP-COMPTH2", "SP-COMPTH"),
            ("SP-LOGIC", "SP-MATH"),
        ]
        for course_code, prereq_code in prereq_pairs:
            course = Course.objects.get(code=course_code)
            prereq = Course.objects.get(code=prereq_code)
            Prerequisite.objects.get_or_create(
                course=course, prerequisite=prereq
            )

        self.stdout.write(self.style.SUCCESS(
            "✅ CS Bachelor curriculum seeded successfully!"
        ))