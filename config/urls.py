from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from core import views  # Correctly import views from the core app

urlpatterns = [
    # --- Admin Panel ---
    path("admin/", admin.site.urls),

    # --- Dashboard & Core ---
    path("", views.home, name="home"),
    path("profile/", views.profile, name="profile"),
    path("profile/reset-password/", views.trigger_password_reset, name="trigger_password_reset"),
    path("settings/", views.settings_view, name="settings"),
    path("generate-exam/", views.generate_exam, name="generate_exam"),
    
    # --- Authentication ---
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    
    # --- Admin User Management ---
    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.user_add, name="user_add"),
    path("users/delete/<int:pk>/", views.user_delete, name="user_delete"),

    # --- Password Reset Paths (Required for the link in trigger_password_reset) ---
    path("accounts/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path("accounts/reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]