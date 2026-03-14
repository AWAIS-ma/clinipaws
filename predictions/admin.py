from django.contrib import admin
from .models import Report, Comment, ImageReport, ImageComment

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'animal', 'predicted_disease', 'created_by', 'created_at', 'get_authentication_status']
    list_filter = ['animal', 'created_at', 'predicted_disease']
    search_fields = ['symptom1', 'symptom2', 'symptom3', 'predicted_disease', 'created_by__username']
    readonly_fields = ['created_at', 'created_by']
    filter_horizontal = ['authenticated_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Animal Information', {
            'fields': ('animal',)
        }),
        ('Symptoms', {
            'fields': ('symptom1', 'symptom2', 'symptom3')
        }),
        ('Prediction Results', {
            'fields': ('predicted_disease', 'description')
        }),
        ('Report Metadata', {
            'fields': ('created_by', 'created_at', 'authenticated_by')
        }),
    )
    
    def get_authentication_status(self, obj):
        if obj.is_authenticated:
            return f"✓ Authenticated by {obj.authenticated_by.count()} doctor(s)"
        return "⏳ Pending"
    get_authentication_status.short_description = 'Authentication Status'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'doctor', 'report', 'created_at']
    list_filter = ['created_at', 'doctor']
    search_fields = ['text', 'doctor__username', 'report__id']
    readonly_fields = ['created_at']

@admin.register(ImageReport)
class ImageReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'animal', 'predicted_disease', 'confidence', 'detected', 'created_by', 'created_at', 'get_authentication_status']
    list_filter = ['animal', 'detected', 'created_at', 'predicted_disease']
    search_fields = ['predicted_disease', 'created_by__username']
    readonly_fields = ['created_at', 'created_by', 'confidence', 'detected', 'predicted_disease', 'detection_details']
    filter_horizontal = ['authenticated_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Animal Information', {
            'fields': ('animal',)
        }),
        ('Images', {
            'fields': ('original_image', 'annotated_image')
        }),
        ('Detection Results', {
            'fields': ('detected', 'predicted_disease', 'confidence', 'detection_details', 'description')
        }),
        ('Report Metadata', {
            'fields': ('created_by', 'created_at', 'authenticated_by')
        }),
    )
    
    def get_authentication_status(self, obj):
        if obj.is_authenticated:
            return f"✓ Authenticated by {obj.authenticated_by.count()} doctor(s)"
        return "⏳ Pending"
    get_authentication_status.short_description = 'Authentication Status'

@admin.register(ImageComment)
class ImageCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'doctor', 'image_report', 'created_at']
    list_filter = ['created_at', 'doctor']
    search_fields = ['text', 'doctor__username', 'image_report__id']
    readonly_fields = ['created_at']
