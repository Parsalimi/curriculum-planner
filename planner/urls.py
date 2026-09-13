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
    path("status/toggle/", views.toggle_course_status, name="toggle_course_status"),
    path("curriculum/", views.curriculum_detail, name="curriculum"),
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
