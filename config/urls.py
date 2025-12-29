from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import CustomLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # Custom Login
    path("accounts/login/", CustomLoginView.as_view(), name='login'),
    
    # Password Reset
    path("accounts/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path("accounts/reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    
    # Default Auth URLs
    path("accounts/", include("django.contrib.auth.urls")),
    
    # Core App URLs (This points to the file below)
    path("", include("core.urls")),
]