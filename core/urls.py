from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("profile/", views.profile, name="profile"),
    path("profile/reset-password/", views.trigger_password_reset, name="trigger_password_reset"),
]