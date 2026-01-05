from django.db import models
from django.contrib.auth.models import User

class ExamSession(models.Model):
    """
    Stores the configuration for a specific exam generation session.
    """
    # --- EXISTING CHOICES ---
    DIFFICULTY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Medium', 'Medium'),
        ('Advanced', 'Advanced'),
    ]

    EXPERIENCE_CHOICES = [
        ('Fresher', 'Fresher / < 1 Year'),
        ('1-3 Years', '1 - 3 Years'),
        ('4-5 Years', '4 - 5 Years'),
        ('5+ Years', 'Above 5 Years'),
    ]

    # --- NEW STATUS CHOICES FOR ASYNC ---
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed'),
    ]

    # Link to the user who requested the exam
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_sessions')
    
    # Candidate Profile
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES)
    
    # Exam Structure
    num_questions = models.IntegerField()
    repeated_questions_allowed = models.BooleanField(default=False)
    mcq_format = models.BooleanField(default=False)
    mcq_coding_format = models.BooleanField(default=False)
    
    # Content Scope
    general_topic = models.BooleanField(default=False)
    # Storing languages as a simple text string (e.g., "Python,Java,C++")
    coding_languages = models.CharField(max_length=255, blank=True, null=True)
    specific_instructions = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    # --- NEW FIELDS FOR ASYNC PROCESS ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    result_html = models.TextField(blank=True, null=True)

    def __str__(self):
        # Merged your string format with the new status
        return f"Exam ({self.difficulty_level}) by {self.user.username} on {self.created_at.strftime('%Y-%m-%d %H:%M')} [{self.status}]"