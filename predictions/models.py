from django.db import models
from django.conf import settings

class Report(models.Model):
    ANIMAL_CHOICES = (
        ('sheep', 'Sheep'),
        ('goat', 'Goat'),
        ('buffalo', 'Buffalo'),
        ('cow', 'Cow'),
    )

    animal = models.CharField(max_length=20, choices=ANIMAL_CHOICES)
    symptom1 = models.CharField(max_length=100)
    symptom2 = models.CharField(max_length=100)
    symptom3 = models.CharField(max_length=100)
    predicted_disease = models.CharField(max_length=100, default="Unknown")
    description = models.TextField()
    
    # Image detection fields (deprecated - use ImageReport instead)
    animal_image = models.ImageField(upload_to='animal_images/', blank=True, null=True)
    roboflow_detected = models.BooleanField(default=False, help_text="Skin disease detected")
    roboflow_confidence = models.FloatField(default=0.0, help_text="Detection confidence score")
    roboflow_details = models.JSONField(blank=True, null=True, help_text="Raw detection details")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    authenticated_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='authenticated_reports')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_authenticated(self):
        return self.authenticated_by.exists()

    def __str__(self):
        return f"Report {self.id} - {self.animal} ({self.created_by.username})"

class ImageReport(models.Model):
    """Model for image-based disease detection"""
    ANIMAL_CHOICES = (
        ('sheep', 'Sheep'),
        ('goat', 'Goat'),
        ('buffalo', 'Buffalo'),
        ('cow', 'Cow'),
    )
    
    animal = models.CharField(max_length=20, choices=ANIMAL_CHOICES)
    original_image = models.ImageField(upload_to='disease_images/original/')
    annotated_image = models.ImageField(upload_to='disease_images/annotated/', blank=True, null=True)
    
    detected = models.BooleanField(default=False, help_text="Skin disease detected")
    confidence = models.FloatField(default=0.0, help_text="Detection confidence score")
    predicted_disease = models.CharField(max_length=100, default="No Disease Detected")
    detection_details = models.JSONField(blank=True, null=True, help_text="Detection details")
    description = models.TextField(blank=True, help_text="AI-generated disease report")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='image_reports')
    authenticated_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='authenticated_image_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def is_authenticated(self):
        return self.authenticated_by.exists()
    
    def __str__(self):
        return f"Image Report {self.id} - {self.animal} ({self.created_by.username})"


class ImageComment(models.Model):
    """Comments on image reports by doctors"""
    image_report = models.ForeignKey(ImageReport, on_delete=models.CASCADE, related_name='comments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.doctor.username} on Image Report {self.image_report.id}"


class Comment(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='comments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.doctor.username} on Report {self.report.id}"
