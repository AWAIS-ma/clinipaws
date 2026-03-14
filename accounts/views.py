from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm, ForgotPasswordForm, OTPVerificationForm, PasswordResetForm, ContactAdminForm
from .models import User, ContactMessage
from .otp_models import PasswordResetOTP

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('dashboard')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        # Save the user
        response = super().form_valid(form)
        # Log the user in
        login(self.request, self.object)
        messages.success(self.request, f'Welcome, {self.request.user.username}! Your account has been created.')
        return response


class ForgotPasswordView(View):
    """View for initiating password reset - sends OTP to email"""
    template_name = 'registration/forgot_password.html'
    
    def get(self, request):
        form = ForgotPasswordForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                
                # Generate OTP
                otp_code = PasswordResetOTP.generate_otp()
                
                # Create OTP record
                otp_record = PasswordResetOTP.objects.create(
                    user=user,
                    otp_code=otp_code
                )
                
                # Send OTP via email
                subject = 'Password Reset OTP - Livestock Disease Prediction'
                message = f'''
Hello {user.username},

You have requested to reset your password. Your OTP code is:

{otp_code}

This code will expire in 10 minutes.

If you did not request this, please ignore this email.

Best regards,
Livestock Disease Prediction System
                '''
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    
                    # Store email in session for next step
                    request.session['reset_email'] = email
                    messages.success(request, f'OTP has been sent to {email}. Please check your email.')
                    return redirect('verify_otp')
                    
                except Exception as e:
                    messages.error(request, f'Failed to send email: {str(e)}')
                    otp_record.delete()
                    
            except User.DoesNotExist:
                # Don't reveal if email exists or not for security
                messages.success(request, 'If this email exists, an OTP has been sent.')
                
        return render(request, self.template_name, {'form': form})


class VerifyOTPView(View):
    """View for verifying OTP code"""
    template_name = 'registration/verify_otp.html'
    
    def get(self, request):
        if 'reset_email' not in request.session:
            messages.error(request, 'Please start the password reset process first.')
            return redirect('forgot_password')
        
        form = OTPVerificationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        if 'reset_email' not in request.session:
            messages.error(request, 'Session expired. Please start again.')
            return redirect('forgot_password')
        
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            email = request.session.get('reset_email')
            
            try:
                user = User.objects.get(email=email)
                otp_record = PasswordResetOTP.objects.filter(
                    user=user,
                    otp_code=otp_code,
                    is_used=False
                ).order_by('-created_at').first()
                
                if otp_record and otp_record.is_valid():
                    # Mark OTP as used
                    otp_record.is_used = True
                    otp_record.save()
                    
                    # Store verification in session
                    request.session['otp_verified'] = True
                    messages.success(request, 'OTP verified successfully. Please set your new password.')
                    return redirect('reset_password')
                else:
                    messages.error(request, 'Invalid or expired OTP. Please try again.')
                    
            except User.DoesNotExist:
                messages.error(request, 'Invalid request.')
                return redirect('forgot_password')
                
        return render(request, self.template_name, {'form': form})


class ResetPasswordView(View):
    """View for setting new password after OTP verification"""
    template_name = 'registration/reset_password.html'
    
    def get(self, request):
        if not request.session.get('otp_verified'):
            messages.error(request, 'Please verify OTP first.')
            return redirect('verify_otp')
        
        form = PasswordResetForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        if not request.session.get('otp_verified'):
            messages.error(request, 'Session expired. Please start again.')
            return redirect('forgot_password')
        
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = request.session.get('reset_email')
            new_password = form.cleaned_data['new_password1']
            
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()
                
                # Clear session data
                request.session.pop('reset_email', None)
                request.session.pop('otp_verified', None)
                
                messages.success(request, 'Password reset successfully! You can now login with your new password.')
                return redirect('login')
                
            except User.DoesNotExist:
                messages.error(request, 'Invalid request.')
                return redirect('forgot_password')
                
        return render(request, self.template_name, {'form': form})


class CustomLoginView(LoginView):
    """Custom login view to handle blocked users"""
    
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
                if getattr(user, 'is_blocked', False):
                    # User is blocked, redirect to blocked page
                    return redirect('blocked')
            except User.DoesNotExist:
                pass
        
        return super().post(request, *args, **kwargs)


class BlockedView(TemplateView):
    """Landing page for blocked users"""
    template_name = 'registration/blocked.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ContactAdminForm()
        return context


class ContactAdminView(View):
    """Handle contact admin submissions from blocked users"""
    
    def post(self, request):
        form = ContactAdminForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            # Try to associate with existing user if email/username matches
            try:
                user = User.objects.get(username=form.cleaned_data['sender_username'])
                message.sender = user
            except User.DoesNotExist:
                pass
            
            message.save()
            messages.success(request, 'Your message has been sent to the administrator. They will review it shortly.')
            return redirect('login')
            
        # If form is invalid, re-render the blocked page with errors
        return render(request, 'registration/blocked.html', {'form': form})
