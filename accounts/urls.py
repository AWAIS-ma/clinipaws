from django.urls import path
from .views import (SignUpView, ForgotPasswordView, VerifyOTPView, 
                    ResetPasswordView, CustomLoginView, BlockedView, ContactAdminView)
from . import views

urlpatterns = [
    # Override default login to use CustomLoginView
    path('login/', CustomLoginView.as_view(template_name='registration/login.html'), name='login'),
    
    path('signup/', SignUpView.as_view(), name='signup'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    
    # Blocked user pages
    path('blocked/', BlockedView.as_view(), name='blocked'),
    path('contact-admin/', ContactAdminView.as_view(), name='contact_admin'),
]
