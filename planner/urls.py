from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="planner/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("status/", views.status_page, name="status"),
    path("chart/", views.chart_page, name="chart"),
    path("status/toggle/", views.toggle_course_status, name="toggle_course_status"),
    path("curriculum/", views.curriculum_detail, name="curriculum"),
    path("admin-panel/", views.admin_panel, name="admin_panel"),
    path("admin-panel/curricula/", views.admin_curriculum_list, name="admin_curriculum_list"),
    path("admin-panel/curricula/create/", views.admin_curriculum_create, name="admin_curriculum_create"),
    path("admin-panel/curricula/<int:curriculum_id>/", views.admin_curriculum_detail, name="admin_curriculum_detail"),
    path("admin-panel/curricula/<int:curriculum_id>/edit/", views.admin_curriculum_edit, name="admin_curriculum_edit"),
    path("admin-panel/curricula/<int:curriculum_id>/delete/", views.admin_curriculum_delete, name="admin_curriculum_delete"),
    path("admin-panel/curricula/<int:curriculum_id>/groups/create/", views.admin_group_create, name="admin_group_create"),
    path("admin-panel/curricula/<int:curriculum_id>/groups/<int:group_id>/edit/", views.admin_group_edit, name="admin_group_edit"),
    path("admin-panel/curricula/<int:curriculum_id>/groups/<int:group_id>/delete/", views.admin_group_delete, name="admin_group_delete"),
    path("admin-panel/curricula/<int:curriculum_id>/courses/create/", views.admin_course_create, name="admin_course_create"),
    path("admin-panel/curricula/<int:curriculum_id>/courses/<int:course_id>/edit/", views.admin_course_edit, name="admin_course_edit"),
    path("admin-panel/curricula/<int:curriculum_id>/courses/<int:course_id>/delete/", views.admin_course_delete, name="admin_course_delete"),
    path("admin-panel/curricula/<int:curriculum_id>/courses/<int:course_id>/assign/", views.admin_assign_course_to_group, name="admin_assign_course_to_group"),
    path("courses/", views.course_list, name="courses"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    path(
        "courses/<int:pk>/track/",
        views.update_course_status,
        name="update_course_status",
    ),
    path("requirements/", views.requirements, name="requirements"),
    path("curriculum/select/", views.select_curriculum, name="select_curriculum"),
]
