from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    ROLE_CHOICES = (
        ('farm_owner', 'Farm Owner'),
        ('doctor', 'Doctor'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='farm_owner')
    email = models.EmailField(unique=True, blank=True, null=True)  # Made optional for existing users
    is_blocked = models.BooleanField(default=False, help_text='Blocked users cannot log in')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class ContactMessage(models.Model):
    """Message sent by a blocked user to the admin."""
    REACTION_CHOICES = (
        ('none', 'No Reaction'),
        ('up', 'Thumbs Up'),
        ('down', 'Thumbs Down'),
    )
    # sender may be null if the user account is fully inactive
    sender = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contact_messages'
    )
    sender_username = models.CharField(max_length=150)
    sender_email = models.EmailField(blank=True)
    message = models.TextField()
    admin_reply = models.TextField(blank=True)
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES, default='none')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.sender_username} ({self.created_at.strftime('%Y-%m-%d')})"

    @property
    def has_reply(self):
        return bool(self.admin_reply)

class UserActivity(models.Model):
    """Model to track user activities like login, logout, report generation, etc."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "User Activities"

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
