from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from .forms import UserUpdateForm
from .zoho_service import send_zoho_email

# 1. Home View
@login_required
def home(request):
    return render(request, "home.html")

# 2. Profile View
@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, 'profile.html', {'form': form})

# 3. Trigger Password Reset View
@login_required
def trigger_password_reset(request):
    """
    Generates a password reset link and sends it via Zoho Mail API.
    """
    user = request.user
    
    # Generate the standard Django reset tokens
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Build the Reset URL
    domain = get_current_site(request).domain
    protocol = 'https' if request.is_secure() else 'http'
    link = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    reset_url = f"{protocol}://{domain}{link}"
    
    # Prepare Email Content
    subject = "Reset your password"
    html_content = f"""
    <p>Hello {user.username},</p>
    <p>You requested to update your password. Please click the link below to reset it:</p>
    <p><a href="{reset_url}">Change My Password</a></p>
    <p>If you didn't ask for this, please ignore this email.</p>
    """
    
    # Send via Zoho (This now calls the updated service based on your JS code)
    success, message = send_zoho_email(user.email, subject, html_content)
    
    if success:
        messages.success(request, f"A password reset link has been sent to {user.email}")
    else:
        messages.error(request, f"Failed to send email. Check server logs for details.")
        
    return redirect('profile')