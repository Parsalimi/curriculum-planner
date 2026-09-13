import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CourseStatusForm, CurriculumSelectForm, RegisterForm
from .models import (
    Course,
    Curriculum,
    CurriculumCourse,
    RequirementCourse,
    RequirementGroup,
    StudentCourse,
)


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "planner/home.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "حساب کاربری شما با موفقیت ایجاد شد.")
            return redirect("select_curriculum")
    else:
        form = RegisterForm()

    return render(request, "planner/register.html", {"form": form})


@login_required
def select_curriculum(request):
    if request.method == "POST":
        form = CurriculumSelectForm(request.POST)
        if form.is_valid():
            request.session["curriculum_id"] = form.cleaned_data["curriculum"].id
            return redirect("dashboard")
    else:
        form = CurriculumSelectForm()

    return render(request, "planner/select_curriculum.html", {"form": form})


def _current_curriculum(request):
    curriculum_id = request.session.get("curriculum_id")
    if curriculum_id:
        return Curriculum.objects.filter(id=curriculum_id).first()
    return Curriculum.objects.first()


def _get_curriculum_stats(request, curriculum):
    curriculum_courses = list(
        CurriculumCourse.objects.filter(
            curriculum=curriculum,
            course__is_active=True,
        ).select_related("course")
    )

    tracked = {
        item.curriculum_course_id: item
        for item in StudentCourse.objects.filter(
            student=request.user,
            curriculum_course__curriculum=curriculum,
        )
    }

    passed_items = [
        item for item in tracked.values()
        if item.status == StudentCourse.Status.PASSED
    ]

    # total_required_units = sum(item.course.credits for item in curriculum_courses)
    total_required_units = curriculum.minimum_credits
    completed_units = sum(
        item.curriculum_course.course.credits for item in passed_items
    )

    overall_progress = (
        round((completed_units / total_required_units) * 100, 1)
        if total_required_units
        else 0
    )

    groups = RequirementGroup.objects.filter(curriculum=curriculum).prefetch_related(
        "requirement_courses__curriculum_course__course"
    )

    groups_payload = []
    completed_groups = 0

    for group in groups:
        requirement_courses = list(group.requirement_courses.all())
        passed_courses = []
        for requirement_course in requirement_courses:
            tracking = tracked.get(requirement_course.curriculum_course_id)
            if tracking and tracking.status == StudentCourse.Status.PASSED:
                passed_courses.append(requirement_course)

        required_units = (
            group.required_credits
            if group.required_credits is not None
            else sum(
                requirement_course.curriculum_course.course.credits
                for requirement_course in requirement_courses
            )
        )
        completed_group_units = sum(
            requirement_course.curriculum_course.course.credits
            for requirement_course in passed_courses
        )
        progress = (
            round((completed_group_units / required_units) * 100, 1)
            if required_units
            else 0
        )
        is_complete = completed_group_units >= required_units
        if is_complete:
            completed_groups += 1

        groups_payload.append(
            {
                "group": group,
                "courses": [
                    {
                        "curriculum_course_id": requirement_course.curriculum_course_id,
                        "name": requirement_course.curriculum_course.course.name,
                        "code": requirement_course.curriculum_course.course.code,
                        "credits": requirement_course.curriculum_course.course.credits,
                        "passed": bool(
                            tracked.get(requirement_course.curriculum_course_id)
                            and tracked[requirement_course.curriculum_course_id].status
                            == StudentCourse.Status.PASSED
                        ),
                    }
                    for requirement_course in requirement_courses
                ],
                "required_units": required_units,
                "completed_units": completed_group_units,
                "progress": progress,
                "passed_courses_count": len(passed_courses),
                "is_complete": is_complete,
                "course_count": len(requirement_courses),
            }
        )

    return {
        "curriculum": curriculum,
        "total_required_units": total_required_units,
        "completed_units": completed_units,
        "remaining_units": max(total_required_units - completed_units, 0),
        "overall_progress": overall_progress,
        "passed_courses_count": len(passed_items),
        "completed_groups": completed_groups,
        "groups": groups_payload,
    }


@login_required
def dashboard(request):
    curriculum = _current_curriculum(request)
    if not curriculum:
        return redirect("select_curriculum")

    stats = _get_curriculum_stats(request, curriculum)
    return render(request, "planner/dashboard.html", stats)


@login_required
def curriculum_detail(request):
    curriculum = _current_curriculum(request)
    if not curriculum:
        return redirect("select_curriculum")

    courses = CurriculumCourse.objects.filter(
        curriculum=curriculum,
        course__is_active=True,
    ).select_related("course")

    tracked = {
        item.curriculum_course_id: item
        for item in StudentCourse.objects.filter(
            student=request.user,
            curriculum_course__curriculum=curriculum,
        )
    }

    categories = []
    for key, label in CurriculumCourse.Category.choices:
        items = [cc for cc in courses if cc.category == key]
        if items:
            categories.append(
                {
                    "key": key,
                    "label": label,
                    "courses": [
                        {"item": cc, "progress": tracked.get(cc.id)}
                        for cc in items
                    ],
                }
            )

    return render(
        request,
        "planner/curriculum.html",
        {"curriculum": curriculum, "categories": categories},
    )


@login_required
def course_list(request):
    curriculum = _current_curriculum(request)
    if not curriculum:
        return redirect("select_curriculum")

    courses = CurriculumCourse.objects.filter(
        curriculum=curriculum,
        course__is_active=True,
    ).select_related("course")

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        courses = courses.filter(
            Q(course__name__icontains=query)
            | Q(course__code__icontains=query)
        )
    if category:
        courses = courses.filter(category=category)

    tracked = {
        item.curriculum_course_id: item
        for item in StudentCourse.objects.filter(
            student=request.user,
            curriculum_course__curriculum=curriculum,
        )
    }

    rows = []
    for cc in courses:
        progress = tracked.get(cc.id)
        if status and (not progress or progress.status != status):
            continue
        rows.append({"item": cc, "progress": progress})

    return render(
        request,
        "planner/courses.html",
        {
            "curriculum": curriculum,
            "rows": rows,
            "query": query,
            "selected_category": category,
            "selected_status": status,
            "categories": CurriculumCourse.Category.choices,
            "statuses": StudentCourse.Status.choices,
        },
    )


@login_required
def course_detail(request, pk):
    curriculum = _current_curriculum(request)
    cc = get_object_or_404(
        CurriculumCourse.objects.select_related("course", "curriculum"),
        pk=pk,
        curriculum=curriculum,
    )
    tracking = StudentCourse.objects.filter(
        student=request.user,
        curriculum_course=cc,
    ).first()

    prerequisites = cc.course.prerequisites.select_related("prerequisite")
    required_for = cc.course.required_for.select_related("course")

    form = CourseStatusForm(instance=tracking)

    return render(
        request,
        "planner/course_detail.html",
        {
            "curriculum_course": cc,
            "tracking": tracking,
            "form": form,
            "prerequisites": prerequisites,
            "required_for": required_for,
        },
    )


@login_required
def update_course_status(request, pk):
    curriculum = _current_curriculum(request)
    cc = get_object_or_404(CurriculumCourse, pk=pk, curriculum=curriculum)

    tracking, _ = StudentCourse.objects.get_or_create(
        student=request.user,
        curriculum_course=cc,
    )

    if request.method == "POST":
        form = CourseStatusForm(request.POST, instance=tracking)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            messages.success(request, f"{cc.course.name} به‌روزرسانی شد.")
            return redirect("course_detail", pk=cc.pk)

    return redirect("course_detail", pk=cc.pk)


@login_required
def requirements(request):
    curriculum = _current_curriculum(request)
    if not curriculum:
        return redirect("select_curriculum")

    groups = RequirementGroup.objects.filter(
        curriculum=curriculum
    ).prefetch_related(
        "requirement_courses__curriculum_course__course"
    )

    tracked = {
        item.curriculum_course_id: item
        for item in StudentCourse.objects.filter(
            student=request.user,
            curriculum_course__curriculum=curriculum,
        )
    }

    data = []
    for group in groups:
        items = []
        for rc in group.requirement_courses.all():
            items.append(
                {
                    "rc": rc,
                    "tracking": tracked.get(rc.curriculum_course_id),
                }
            )
        passed = [
            item for item in items
            if item["tracking"]
            and item["tracking"].status == StudentCourse.Status.PASSED
        ]
        credits = sum(
            item["rc"].curriculum_course.course.credits for item in passed
        )
        data.append(
            {
                "group": group,
                "items": items,
                "passed_count": len(passed),
                "passed_credits": credits,
            }
        )

    return render(
        request,
        "planner/requirements.html",
        {"curriculum": curriculum, "groups": data},
    )


@login_required
def status_page(request):
    curriculum = _current_curriculum(request)
    if not curriculum:
        return redirect("select_curriculum")

    stats = _get_curriculum_stats(request, curriculum)
    return render(request, "planner/status.html", stats)


@login_required
def toggle_course_status(request):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "درخواست نامعتبر است."},
            status=405,
        )

    curriculum = _current_curriculum(request)
    if not curriculum:
        return JsonResponse(
            {"success": False, "message": "هیچ برنامه درسی انتخاب نشده است."},
            status=400,
        )

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "message": "درخواست نامعتبر است."},
            status=400,
        )

    curriculum_course_id = payload.get("curriculum_course_id")
    passed = payload.get("passed", False)

    if curriculum_course_id is None:
        return JsonResponse(
            {"success": False, "message": "شناسه درس نامعتبر است."},
            status=400,
        )

    try:
        curriculum_course = get_object_or_404(
            CurriculumCourse.objects.select_related("course", "curriculum"),
            pk=curriculum_course_id,
            curriculum=curriculum,
        )
    except Exception:
        return JsonResponse(
            {"success": False, "message": "درس مورد نظر پیدا نشد."},
            status=404,
        )

    try:
        tracking, _ = StudentCourse.objects.get_or_create(
            student=request.user,
            curriculum_course=curriculum_course,
        )
        tracking.status = (
            StudentCourse.Status.PASSED if passed else StudentCourse.Status.NOT_STARTED
        )
        tracking.save(update_fields=["status"])
    except Exception:
        return JsonResponse(
            {"success": False, "message": "ذخیره تغییرات انجام نشد. دوباره تلاش کنید."},
            status=500,
        )

    stats = _get_curriculum_stats(request, curriculum)

    matching_group = next(
        (
            group
            for group in stats["groups"]
            if any(
                course["curriculum_course_id"] == curriculum_course_id
                for course in group["courses"]
            )
        ),
        None,
    )

    if matching_group is None:
        matching_group = {"group": None, "required_units": 0, "completed_units": 0, "progress": 0, "passed_courses_count": 0, "is_complete": False}

    return JsonResponse(
        {
            "success": True,
            "passed": passed,
            "overall": {
                "completed_units": stats["completed_units"],
                "required_units": stats["total_required_units"],
                "progress": stats["overall_progress"],
                "passed_courses_count": stats["passed_courses_count"],
                "completed_groups": stats["completed_groups"],
            },
            "group": {
                "group_id": matching_group["group"].id if matching_group["group"] else None,
                "required_units": matching_group["required_units"],
                "completed_units": matching_group["completed_units"],
                "progress": matching_group["progress"],
                "passed_courses_count": matching_group["passed_courses_count"],
                "is_complete": matching_group["is_complete"],
            },
        }
    )
