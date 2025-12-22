from django import forms
from django.contrib.auth.models import User

class UserUpdateForm(forms.ModelForm):
    # Explicitly adding widgets to ensure they pick up our CSS classes
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-input'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
        }
        help_texts = {
            'username': None,  # Remove the default help text for a cleaner look
        }

    # Custom validation to ensure username is not blank (though Django handles this, it's good to be explicit)
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError("Username cannot be blank.")
        return username