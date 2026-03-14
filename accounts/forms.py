from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required. Enter a valid email address.')
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Don't modify username - let doctors login with their plain username
        # The "Dr." prefix will be shown only in display (templates)
        if commit:
            user.save()
        return user


class ForgotPasswordForm(forms.Form):
    """Form for requesting password reset via email"""
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )


class OTPVerificationForm(forms.Form):
    """Form for verifying OTP code"""
    otp_code = forms.CharField(
        label='OTP Code',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit OTP'
        })
    )


class PasswordResetForm(forms.Form):
    """Form for setting new password after OTP verification"""
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    new_password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data


class ContactAdminForm(forms.ModelForm):
    """Form for blocked users to contact the admin"""
    class Meta:
        from .models import ContactMessage
        model = ContactMessage
        fields = ['sender_username', 'sender_email', 'message']
        widgets = {
            'sender_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Registered Username', 'required': True}),
            'sender_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Registered Email', 'required': True}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Explain why you should be unblocked or your issue here...', 'required': True}),
        }
