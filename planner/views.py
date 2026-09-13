import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    CourseStatusForm,
    CurriculumAdminForm,
    CurriculumCourseForm,
    CurriculumSelectForm,
    RegisterForm,
    RequirementGroupAdminForm,
)
from .models import (
    Course,
    Curriculum,
    CurriculumCourse,
    Prerequisite,
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

    total_required_units = curriculum.minimum_credits
    completed_units = sum(
        item.curriculum_course.course.credits for item in passed_items
    )

    overall_progress = (
        round((completed_units / total_required_units) * 100, 1)
        if total_required_units
        else 0
    )

    groups = list(
        RequirementGroup.objects.filter(curriculum=curriculum).prefetch_related(
            "requirement_courses__curriculum_course__course",
            "overflow_to",
        )
    )

    requirement_courses_by_group = {}
    passed_courses_by_group = {}
    own_completed_by_group = {}
    required_units_by_group = {}
    mandatory_passed_by_group = {}
    groups_payload = []
    completed_groups = 0

    for group in groups:
        requirement_courses = list(group.requirement_courses.all())
        requirement_courses_by_group[group.id] = requirement_courses

        passed_courses = []
        for requirement_course in requirement_courses:
            tracking = tracked.get(requirement_course.curriculum_course_id)
            if tracking and tracking.status == StudentCourse.Status.PASSED:
                passed_courses.append(requirement_course)

        passed_courses_by_group[group.id] = passed_courses

        required_units = (
            group.required_credits
            if group.required_credits is not None
            else sum(
                requirement_course.curriculum_course.course.credits
                for requirement_course in requirement_courses
            )
        )
        required_units_by_group[group.id] = required_units

        own_completed_by_group[group.id] = sum(
            requirement_course.curriculum_course.course.credits
            for requirement_course in passed_courses
        )

        mandatory_passed_by_group[group.id] = all(
            (
                not requirement_course.curriculum_course.is_mandatory
                or (
                    tracked.get(requirement_course.curriculum_course_id)
                    and tracked[requirement_course.curriculum_course_id].status
                    == StudentCourse.Status.PASSED
                )
            )
            for requirement_course in requirement_courses
        )

    overflow_sources_by_destination = {group.id: [] for group in groups}
    for group in groups:
        if group.overflow_to_id:
            overflow_sources_by_destination[group.overflow_to_id].append(group)

    completed_units_by_group = {}

    def resolve_group_completed(group_id):
        if group_id in completed_units_by_group:
            return completed_units_by_group[group_id]

        own_completed = own_completed_by_group.get(group_id, 0)
        extra_from_sources = 0

        for source_group in overflow_sources_by_destination.get(group_id, []):
            source_total = resolve_group_completed(source_group.id)
            source_required = required_units_by_group.get(source_group.id, 0)
            extra_from_sources += max(source_total - source_required, 0)

        completed_units_by_group[group_id] = own_completed + extra_from_sources
        return completed_units_by_group[group_id]

    for group in groups:
        requirement_courses = requirement_courses_by_group.get(group.id, [])
        passed_courses = passed_courses_by_group.get(group.id, [])
        required_units = required_units_by_group.get(group.id, 0)
        completed_group_units = resolve_group_completed(group.id)
        progress = (
            round((completed_group_units / required_units) * 100, 1)
            if required_units
            else 0
        )
        progress = min(progress, 100)
        is_complete = (
            bool(required_units)
            and completed_group_units >= required_units
            and mandatory_passed_by_group.get(group.id, True)
        )

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
                        "is_mandatory": requirement_course.curriculum_course.is_mandatory,
                    }
                    for requirement_course in requirement_courses
                ],
                "required_units": required_units,
                "completed_units": completed_group_units,
                "own_completed_units": own_completed_by_group.get(group.id, 0),
                "overflow_received": max(
                    completed_group_units - own_completed_by_group.get(group.id, 0),
                    0,
                ),
                "progress": progress,
                "passed_courses_count": len(passed_courses),
                "is_complete": is_complete,
                "course_count": len(requirement_courses),
                "overflow_destination": group.overflow_to,
                "overflow_destination_name": group.overflow_to.name if group.overflow_to else None,
            }
        )

    return {
        "curriculum": curriculum,
        "total_required_units": total_required_units,
        "completed_units": completed_units,
        "remaining_units": max(total_required_units - completed_units, 0),
        "overall_progress": min(
            round((completed_units / total_required_units) * 100, 1)
            if total_required_units
            else 0,
            100,
        ),
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
def chart_page(request):
    curriculum = _current_curriculum(request)
    if not curriculum:
        return redirect("select_curriculum")

    courses = list(
        CurriculumCourse.objects.filter(
            curriculum=curriculum,
            course__is_active=True,
        )
        .select_related("course")
        .order_by("recommended_semester", "course__code")
    )

    tracked = {
        item.curriculum_course_id: item
        for item in StudentCourse.objects.filter(
            student=request.user,
            curriculum_course__curriculum=curriculum,
        )
    }

    semester_counts = {}
    nodes = []
    course_lookup_by_course_id = {cc.course_id: cc for cc in courses}

    for cc in courses:
        semester_counts[cc.recommended_semester] = semester_counts.get(cc.recommended_semester, 0) + 1

    position_counts = {}
    for cc in courses:
        semester = cc.recommended_semester
        position_counts[semester] = position_counts.get(semester, 0) + 1
        node_index = position_counts[semester] - 1
        nodes.append(
            {
                "curriculum_course": cc,
                "x": semester * 240 + 120,
                "y": node_index * 150 + 70,
                "passed": bool(
                    tracked.get(cc.id)
                    and tracked[cc.id].status == StudentCourse.Status.PASSED
                ),
            }
        )

    nodes_by_id = {node["curriculum_course"].id: node for node in nodes}
    edges = []
    prerequisite_relations = Prerequisite.objects.filter(
        course__curriculum_courses__curriculum=curriculum,
        prerequisite__curriculum_courses__curriculum=curriculum,
    ).select_related("course", "prerequisite")

    for relation in prerequisite_relations:
        source_cc = course_lookup_by_course_id.get(relation.prerequisite_id)
        target_cc = course_lookup_by_course_id.get(relation.course_id)
        if source_cc and target_cc:
            edges.append(
                {
                    "from": source_cc.id,
                    "to": target_cc.id,
                    "from_course": source_cc,
                    "to_course": target_cc,
                }
            )

    return render(
        request,
        "planner/chart.html",
        {
            "curriculum": curriculum,
            "nodes": nodes,
            "edges": edges,
            "nodes_by_id": nodes_by_id,
            "course_lookup_by_course_id": course_lookup_by_course_id,
        },
    )


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


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_panel(request):
    curricula = Curriculum.objects.all().prefetch_related(
        "curriculum_courses__course",
        "requirement_groups__requirement_courses__curriculum_course__course",
    )

    curriculum_payload = []
    for curriculum in curricula:
        groups = list(curriculum.requirement_groups.all())
        curriculum_payload.append(
            {
                "curriculum": curriculum,
                "course_count": curriculum.curriculum_courses.count(),
                "group_count": len(groups),
                "groups": groups,
            }
        )

    return render(
        request,
        "planner/admin_panel.html",
        {"curricula": curriculum_payload},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_curriculum_list(request):
    curricula = Curriculum.objects.all().order_by("name")
    return render(
        request,
        "planner/admin_curricula.html",
        {"curricula": curricula},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_curriculum_create(request):
    if request.method == "POST":
        form = CurriculumAdminForm(request.POST)
        if form.is_valid():
            curriculum = form.save()
            messages.success(request, "برنامه درسی با موفقیت ایجاد شد.")
            return redirect("admin_curriculum_detail", curriculum_id=curriculum.pk)
    else:
        form = CurriculumAdminForm()

    return render(
        request,
        "planner/admin_curriculum_form.html",
        {"form": form, "title": "ایجاد برنامه درسی"},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_curriculum_detail(request, curriculum_id):
    curriculum = get_object_or_404(
        Curriculum.objects.prefetch_related(
            "requirement_groups__requirement_courses__curriculum_course__course"
        ),
        pk=curriculum_id,
    )
    groups = list(curriculum.requirement_groups.all())
    courses = list(
        CurriculumCourse.objects.filter(curriculum=curriculum)
        .select_related("course")
        .order_by("recommended_semester", "course__code")
    )

    assigned_course_ids = set()
    for group in groups:
        for requirement_course in group.requirement_courses.all():
            assigned_course_ids.add(requirement_course.curriculum_course_id)

    unassigned_courses = [course for course in courses if course.id not in assigned_course_ids]

    return render(
        request,
        "planner/admin_curriculum_detail.html",
        {
            "curriculum": curriculum,
            "groups": groups,
            "courses": courses,
            "unassigned_courses": unassigned_courses,
        },
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_curriculum_edit(request, curriculum_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    if request.method == "POST":
        form = CurriculumAdminForm(request.POST, instance=curriculum)
        if form.is_valid():
            form.save()
            messages.success(request, "برنامه درسی با موفقیت به‌روزرسانی شد.")
            return redirect("admin_curriculum_detail", curriculum_id=curriculum.pk)
    else:
        form = CurriculumAdminForm(instance=curriculum)

    return render(
        request,
        "planner/admin_curriculum_form.html",
        {"form": form, "title": "ویرایش برنامه درسی", "curriculum": curriculum},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_curriculum_delete(request, curriculum_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    if request.method == "POST":
        curriculum.delete()
        messages.success(request, "برنامه درسی حذف شد.")
        return redirect("admin_curriculum_list")

    return render(
        request,
        "planner/admin_curriculum_delete.html",
        {"curriculum": curriculum},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_group_create(request, curriculum_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    if request.method == "POST":
        form = RequirementGroupAdminForm(request.POST, curriculum=curriculum)
        if form.is_valid():
            group = form.save(commit=False)
            group.curriculum = curriculum
            group.save()
            messages.success(request, "گروه درسی ایجاد شد.")
            return redirect("admin_curriculum_detail", curriculum_id=curriculum.pk)
    else:
        form = RequirementGroupAdminForm(curriculum=curriculum)

    return render(
        request,
        "planner/admin_group_form.html",
        {"form": form, "curriculum": curriculum, "title": "ایجاد گروه درسی"},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_group_edit(request, curriculum_id, group_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    group = get_object_or_404(RequirementGroup, pk=group_id, curriculum=curriculum)
    if request.method == "POST":
        form = RequirementGroupAdminForm(request.POST, instance=group, curriculum=curriculum)
        if form.is_valid():
            form.save()
            messages.success(request, "گروه درسی به‌روزرسانی شد.")
            return redirect("admin_curriculum_detail", curriculum_id=curriculum.pk)
    else:
        form = RequirementGroupAdminForm(instance=group, curriculum=curriculum)

    return render(
        request,
        "planner/admin_group_form.html",
        {"form": form, "curriculum": curriculum, "title": "ویرایش گروه درسی"},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_group_delete(request, curriculum_id, group_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    group = get_object_or_404(RequirementGroup, pk=group_id, curriculum=curriculum)
    if request.method == "POST":
        group.delete()
        messages.success(request, "گروه درسی حذف شد.")
        return redirect("admin_curriculum_detail", curriculum_id=curriculum.pk)

    return render(
        request,
        "planner/admin_group_delete.html",
        {"curriculum": curriculum, "group": group},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_course_create(request, curriculum_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    if request.method == "POST":
        form = CurriculumCourseForm(request.POST, curriculum=curriculum)
        if form.is_valid():
            form.save(curriculum)
            messages.success(request, "درس جدید با موفقیت ایجاد شد.")
            return redirect("admin_curriculum_detail", curriculum_id=curriculum.pk)
    else:
        form = CurriculumCourseForm(curriculum=curriculum)

    return render(
        request,
        "planner/admin_course_form.html",
        {"form": form, "curriculum": curriculum, "title": "ایجاد درس"},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_course_edit(request, curriculum_id, course_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    curriculum_course = get_object_or_404(
        CurriculumCourse.objects.select_related("course"),
        pk=course_id,
        curriculum=curriculum,
    )

    if request.method == "POST":
        form = CurriculumCourseForm(request.POST, curriculum=curriculum, curriculum_course=curriculum_course)
        if form.is_valid():
            form.save(curriculum, curriculum_course=curriculum_course)
            messages.success(request, "درس با موفقیت به‌روزرسانی شد.")
            return redirect("admin_curriculum_detail", curriculum_id=curriculum.pk)
    else:
        form = CurriculumCourseForm(curriculum=curriculum, curriculum_course=curriculum_course)

    return render(
        request,
        "planner/admin_course_form.html",
        {"form": form, "curriculum": curriculum, "title": "ویرایش درس"},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_course_delete(request, curriculum_id, course_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    curriculum_course = get_object_or_404(CurriculumCourse, pk=course_id, curriculum=curriculum)
    if request.method == "POST":
        curriculum_course.delete()
        messages.success(request, "درس حذف شد.")
        return redirect("admin_curriculum_detail", curriculum_id=curriculum.pk)

    return render(
        request,
        "planner/admin_course_delete.html",
        {"curriculum": curriculum, "curriculum_course": curriculum_course},
    )


@user_passes_test(lambda user: user.is_staff)
@login_required
def admin_assign_course_to_group(request, curriculum_id, course_id):
    curriculum = get_object_or_404(Curriculum, pk=curriculum_id)
    curriculum_course = get_object_or_404(CurriculumCourse, pk=course_id, curriculum=curriculum)

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "درخواست نامعتبر است."}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    group_id = payload.get("group_id")

    if group_id is None:
        RequirementCourse.objects.filter(curriculum_course=curriculum_course).delete()
        return JsonResponse({"success": True, "group_id": None})

    group = get_object_or_404(RequirementGroup, pk=group_id, curriculum=curriculum)
    RequirementCourse.objects.update_or_create(
        curriculum_course=curriculum_course,
        requirement_group=group,
    )

    RequirementCourse.objects.filter(curriculum_course=curriculum_course).exclude(
        requirement_group=group
    ).delete()

    return JsonResponse({"success": True, "group_id": group.pk})


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
