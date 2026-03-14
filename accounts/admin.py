from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ContactMessage
from .otp_models import PasswordResetOTP

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'get_role_display', 'is_staff', 'is_active', 'is_blocked', 'date_joined']
    list_filter = ['role', 'is_staff', 'is_active', 'is_blocked', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Status Information', {'fields': ('role', 'is_blocked')}),
    )
    
    def get_role_display(self, obj):
        role_colors = {
            'farm_owner': '🌾 Farm Owner',
            'doctor': '👨‍⚕️ Doctor',
            'student': '🎓 Student',
        }
        return role_colors.get(obj.role, obj.get_role_display())
    get_role_display.short_description = 'Role'


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp_code', 'created_at', 'expires_at', 'is_used', 'is_valid']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'user__email', 'otp_code']
    readonly_fields = ['created_at', 'expires_at']
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['sender_username', 'sender_email', 'reaction', 'is_read', 'created_at']
    list_filter = ['is_read', 'reaction', 'created_at']
    search_fields = ['sender_username', 'sender_email', 'message']
    readonly_fields = ['sender', 'sender_username', 'sender_email', 'message', 'created_at', 'reaction']
    list_display_links = ['sender_username']
