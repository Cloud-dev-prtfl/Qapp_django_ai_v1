from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("profile/", views.profile, name="profile"),
    path("profile/reset-password/", views.trigger_password_reset, name="trigger_password_reset"),
    path("settings/", views.settings_view, name="settings"), # New Settings URL
    
    # Admin User Management
    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.user_add, name="user_add"),
    path("users/delete/<int:pk>/", views.user_delete, name="user_delete"),
]