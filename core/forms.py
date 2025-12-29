from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.models import Q

class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """
    Custom form that changes the label to 'Username or Email'.
    Used by CustomLoginView.
    """
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={'class': 'form-input', 'autofocus': True})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input'})
    )

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
        }
        help_texts = {
            'username': None,
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError("Username cannot be blank.")
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email cannot be blank.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already associated with another account.")
        return email

class AdminUserCreationForm(UserCreationForm):
    """
    Form for Admins to add a new user.
    Extends UserCreationForm which handles the Password 1 & 2 validation automatically.
    """
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input'}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        # We generally do not need manual widgets in Meta if we use the __init__ override,
        # but defining the username widget here is safe.
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super(AdminUserCreationForm, self).__init__(*args, **kwargs)
        # Apply the CSS class to ALL fields, including the auto-generated password fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-input'