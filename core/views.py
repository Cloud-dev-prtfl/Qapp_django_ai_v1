import threading # Required for background task
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.views import LoginView
from django.http import JsonResponse # Required for AJAX

from .forms import UserUpdateForm, EmailOrUsernameAuthenticationForm, AdminUserCreationForm
from .zoho_service import send_zoho_email
from .models import ExamSession
# Import the new orchestrated flow
from .ai_agents import orchestrated_exam_flow

# --- CUSTOM LOGIN VIEW ---
class CustomLoginView(LoginView):
    authentication_form = EmailOrUsernameAuthenticationForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

# --- EXISTING VIEWS ---

@login_required
def home(request):
    if request.user.groups.filter(name='User').exists():
        return render(request, "users/user_dashboard.html")
    return render(request, "home.html")

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect(f"{reverse('profile')}#update-profile")
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'profile.html', {'form': form})

@login_required
def settings_view(request):
    if request.method == 'POST':
        try:
            difficulty = request.POST.get('level')
            experience = request.POST.get('experience')
            num_questions = request.POST.get('num_questions')
            languages = request.POST.get('languages')
            instructions = request.POST.get('instructions')
            
            repeated_allowed = request.POST.get('repeated_allowed') == 'on'
            mcq = request.POST.get('mcq') == 'on'
            mcq_coding = request.POST.get('mcq_coding') == 'on'
            general_topic = request.POST.get('general_topic') == 'on'

            ExamSession.objects.create(
                user=request.user,
                difficulty_level=difficulty,
                experience_level=experience,
                num_questions=num_questions,
                repeated_questions_allowed=repeated_allowed,
                mcq_format=mcq,
                mcq_coding_format=mcq_coding,
                general_topic=general_topic,
                coding_languages=languages,
                specific_instructions=instructions
            )
            messages.success(request, "Configuration Saved Successfully!")
            return redirect('settings')
        except Exception as e:
            messages.error(request, f"Error saving configuration: {str(e)}")
            return redirect('settings')

    last_exam = ExamSession.objects.filter(user=request.user).last()
    return render(request, 'settings.html', {'last_exam': last_exam})

# --- ASYNC EXAM GENERATION VIEWS ---

@login_required
def generate_exam(request):
    """
    Renders the Generate Exam page. 
    The actual generation is now handled via AJAX calls to start_exam_generation.
    """
    if request.user.groups.filter(name='User').exists():
        messages.error(request, "You are not authorized to access this page.")
        return redirect('home')
    
    # Just render the template; the frontend handles the rest
    return render(request, 'generate_exam.html')

@login_required
def start_exam_generation(request):
    """
    AJAX Endpoint: Starts the background thread for exam generation.
    """
    if request.method == 'POST':
        # 1. Retrieve the last valid settings (exclude any currently processing ones)
        last_config = ExamSession.objects.filter(user=request.user).exclude(status='PROCESSING').last()
        
        if not last_config:
            return JsonResponse({'status': 'error', 'message': 'Please save Settings first.'})

        # 2. Create a NEW session for this specific run
        new_session = ExamSession.objects.create(
            user=request.user,
            difficulty_level=last_config.difficulty_level,
            experience_level=last_config.experience_level,
            num_questions=last_config.num_questions,
            coding_languages=last_config.coding_languages,
            specific_instructions=last_config.specific_instructions,
            mcq_format=last_config.mcq_format,
            mcq_coding_format=last_config.mcq_coding_format,
            general_topic=last_config.general_topic,
            repeated_questions_allowed=last_config.repeated_questions_allowed, # ADDED THIS LINE
            status='PENDING' 
        )

        # 3. Start the Background Thread
        thread = threading.Thread(target=orchestrated_exam_flow, args=(new_session.id,))
        thread.daemon = True 
        thread.start()

        return JsonResponse({'status': 'started', 'session_id': new_session.id})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def cancel_exam_generation(request):
    """
    AJAX Endpoint: Marks a session as CANCELLED.
    """
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        if session_id:
            try:
                session = ExamSession.objects.get(id=session_id, user=request.user)
                session.status = 'CANCELLED'
                session.save()
                return JsonResponse({'status': 'cancelled'})
            except ExamSession.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Session not found'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def check_exam_status(request):
    """
    AJAX Endpoint: Polling to check current status.
    """
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            session = ExamSession.objects.get(id=session_id, user=request.user)
            return JsonResponse({
                'status': session.status,
                'html': session.result_html if session.status == 'COMPLETED' else None
            })
        except ExamSession.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Not found'})
    return JsonResponse({'status': 'error'}, status=400)

# --- PASSWORD RESET & ADMIN VIEWS (UNCHANGED) ---

@login_required
def trigger_password_reset(request):
    user = request.user
    if not user.email:
        messages.error(request, "Please add an email address to your profile first.")
        return redirect(f"{reverse('profile')}#update-profile")
    
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    domain = get_current_site(request).domain
    protocol = 'https' if request.is_secure() else 'http'
    link = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    reset_url = f"{protocol}://{domain}{link}"
    
    subject = "Reset your password"
    html_content = f"""
    <p>Hello {user.username},</p>
    <p>You requested to update your password. Please click the link below to reset it:</p>
    <p><a href="{reset_url}">Change My Password</a></p>
    """
    
    success, message = send_zoho_email(user.email, subject, html_content)
    
    if success:
        messages.success(request, f"A password reset link has been sent to {user.email}")
    else:
        messages.error(request, f"Failed to send email: {message}")
        
    return redirect(f"{reverse('profile')}#reset-password")

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'users/user_list.html', {'users': users})

@user_passes_test(is_admin)
def user_add(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New user created successfully.")
            return redirect('user_list')
    else:
        form = AdminUserCreationForm()
    
    return render(request, 'users/user_form.html', {'form': form})

@user_passes_test(is_admin)
def user_delete(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)
    if user_to_delete == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_list')
        
    if request.method == 'POST':
        user_to_delete.delete()
        messages.success(request, f"User {user_to_delete.username} has been deleted.")
        return redirect('user_list')
    
    return render(request, 'users/user_confirm_delete.html', {'object': user_to_delete})