from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, CreateView, DetailView, View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Report
from accounts.models import UserActivity
from .forms import ReportForm, CommentForm
import sys
import os

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from livestock_disease_prediction.utils import generate_ai_report, call_chat_api

# ... (existing imports) ...

# Add the project directory to sys.path to import KNN
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Logistic Regression classifier'))
try:
    import Logistic_Regression
except ImportError:
    Logistic_Regression = None

# Trigger reload for KNN updates

class DashboardView(TemplateView):
    template_name = 'predictions/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        search_query = self.request.GET.get('search', '').strip()
        report_type = self.request.GET.get('report_type', 'all')  # all, symptom, image
        
        if not user.is_authenticated:
            # Public view: maybe show some general stats or nothing specific
            context['reports'] = Report.objects.none()
            context['image_reports'] = []
            context['is_public'] = True
            context['search_query'] = search_query
            context['report_type'] = report_type
            return context

        context['is_public'] = False
        context['search_query'] = search_query
        context['report_type'] = report_type
        
        # Import ImageReport
        from .models import ImageReport
        from django.db.models import Q
        
        # Admin and superusers can see all reports
        if user.is_superuser or user.is_staff:
            reports = Report.objects.all()
            image_reports = ImageReport.objects.all()
        elif user.role == 'farm_owner':
            reports = Report.objects.filter(created_by=user)
            image_reports = ImageReport.objects.filter(created_by=user)
        elif user.role == 'doctor':
            reports = Report.objects.all()
            image_reports = ImageReport.objects.all()
        elif user.role == 'student':
            reports = Report.objects.all()
            image_reports = ImageReport.objects.all()
        else:
            reports = Report.objects.none()
            image_reports = ImageReport.objects.none()
        
        # Apply search filter if search query exists
        if search_query:
            # Build Q filter that matches ALL words from the query in any order
            # e.g. "skin lumpy" -> matches "Lumpy Skin Disease"
            words = search_query.split()

            def build_multi_word_q(words, field_list):
                """Return Q that matches records containing ALL words (any order) across fields."""
                combined = None
                for word in words:
                    word_q = None
                    for field in field_list:
                        q = Q(**{f"{field}__icontains": word})
                        word_q = q if word_q is None else word_q | q
                    combined = word_q if combined is None else combined & word_q
                return combined or Q()

            symptom_fields = ['predicted_disease', 'animal', 'symptom1', 'symptom2', 'symptom3', 'id', 'created_by__username']
            image_fields = ['predicted_disease', 'animal', 'id', 'created_by__username']

            reports = reports.filter(build_multi_word_q(words, symptom_fields))
            image_reports = image_reports.filter(build_multi_word_q(words, image_fields))
        
        # Apply report type filter
        if report_type == 'symptom':
            image_reports = ImageReport.objects.none()
        elif report_type == 'image':
            reports = Report.objects.none()
        elif report_type == 'mine':
            # Filter both by current user
            reports = reports.filter(created_by=user)
            image_reports = image_reports.filter(created_by=user)
        # else: report_type == 'all', show both
        
        # Pagination for symptom-based reports
        symptom_page = self.request.GET.get('page', 1)
        paginator = Paginator(reports.order_by('-created_at'), 6)
        try:
            reports_paginated = paginator.page(symptom_page)
        except PageNotAnInteger:
            reports_paginated = paginator.page(1)
        except EmptyPage:
            reports_paginated = paginator.page(paginator.num_pages)

        # Pagination for image-based reports
        image_page = self.request.GET.get('img_page', 1)
        img_paginator = Paginator(image_reports.order_by('-created_at'), 6)
        try:
            image_reports_paginated = img_paginator.page(image_page)
        except PageNotAnInteger:
            image_reports_paginated = img_paginator.page(1)
        except EmptyPage:
            image_reports_paginated = img_paginator.page(img_paginator.num_pages)

        context['reports'] = reports_paginated
        context['image_reports'] = image_reports_paginated
            
        return context


class SearchSuggestionsView(LoginRequiredMixin, View):
    """Return JSON autocomplete suggestions for the search bar."""
    def get(self, request):
        from .models import ImageReport
        from django.db.models import Q

        q = request.GET.get('q', '').strip()
        if not q or len(q) < 2:
            return JsonResponse({'suggestions': []})

        user = request.user
        words = q.split()

        def build_multi_word_q(words, field_list):
            combined = None
            for word in words:
                word_q = None
                for field in field_list:
                    qobj = Q(**{f"{field}__icontains": word})
                    word_q = qobj if word_q is None else word_q | qobj
                combined = word_q if combined is None else combined & word_q
            return combined or Q()

        # Determine which reports user can see
        if user.is_superuser or user.is_staff or user.role in ('doctor', 'student'):
            reports = Report.objects.all()
            image_reports = ImageReport.objects.all()
        elif user.role == 'farm_owner':
            reports = Report.objects.filter(created_by=user)
            image_reports = ImageReport.objects.filter(created_by=user)
        else:
            return JsonResponse({'suggestions': []})

        symptom_q = build_multi_word_q(words, ['predicted_disease', 'animal', 'symptom1', 'symptom2', 'symptom3'])
        image_q = build_multi_word_q(words, ['predicted_disease', 'animal'])

        diseases = list(
            reports.filter(symptom_q).values_list('predicted_disease', flat=True).distinct()[:5]
        )
        image_diseases = list(
            image_reports.filter(image_q).values_list('predicted_disease', flat=True).distinct()[:5]
        )
        animals = list(
            reports.filter(Q(animal__icontains=q)).values_list('animal', flat=True).distinct()[:3]
        )

        # Combine and deduplicate
        seen = set()
        suggestions = []
        for item in diseases + image_diseases + animals:
            if item and item not in seen:
                seen.add(item)
                suggestions.append(item)

        return JsonResponse({'suggestions': suggestions[:8]})


class CreateReportView(LoginRequiredMixin, CreateView):
    model = Report
    form_class = ReportForm
    template_name = 'predictions/create_report.html'
    
    def get_success_url(self):
        return reverse_lazy('report_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Get data for prediction
        animal = form.cleaned_data['animal']
        symptom1 = form.cleaned_data['symptom1']
        symptom2 = form.cleaned_data['symptom2']
        symptom3 = form.cleaned_data['symptom3']
        
        # Call Logistic regression venvmodel for symptom-based prediction
        if Logistic_Regression:
            try:
                prediction_result = Logistic_Regression.Logistic_Regression_classifier(animal, symptom1, symptom2, symptom3)
                predicted_disease = prediction_result['Predicted Disease']
                form.instance.predicted_disease = predicted_disease
                
                # Generate detailed AI report
                symptoms_str = f"{symptom1}, {symptom2}, {symptom3}"
                ai_report = generate_ai_report(predicted_disease, symptoms_str)
                
                form.instance.description = (
                    f"**Predicted Disease:** {predicted_disease}\n"
                    f"**Confidence:** {prediction_result['Confidence']}%\n"
                    f"**Model Accuracy:** {prediction_result['Model Accuracy']}%\n\n"
                    f"{ai_report}"
                )
            except Exception as e:
                form.instance.predicted_disease = "Error"
                form.instance.description = f"Prediction failed: {str(e)}"
        else:
            form.instance.predicted_disease = "Model Not Found"
            form.instance.description = "KNN model could not be loaded."
            
        response = super().form_valid(form)
        
        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            action="Generated Symptom-Based Report",
            details=f"Report ID: {self.object.id}, Disease: {self.object.predicted_disease}, Animal: {self.object.animal}"
        )
        
        return response

class ReportDetailView(LoginRequiredMixin, DetailView):
    model = Report
    template_name = 'predictions/report_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.all().order_by('created_at')
        if self.request.user.role == 'doctor':
            context['comment_form'] = CommentForm()
        return context

class AddCommentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        if request.user.role == 'doctor':
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.report = report
                comment.doctor = request.user
                comment.save()
                messages.success(request, 'Comment added successfully.')
            else:
                messages.error(request, 'Error adding comment.')
        else:
            messages.error(request, 'Only doctors can add comments.')
        return redirect('report_detail', pk=pk)

class DeleteCommentView(LoginRequiredMixin, View):
    def post(self, request, pk, comment_id):
        from .models import Comment
        comment = get_object_or_404(Comment, pk=comment_id, report__pk=pk)
        
        # Only the comment author can delete their own comment
        if request.user == comment.doctor:
            comment.delete()
            messages.success(request, 'Comment deleted successfully.')
        else:
            messages.error(request, 'You can only delete your own comments.')
        
        return redirect('report_detail', pk=pk)

class AuthenticateReportView(LoginRequiredMixin, View):
    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        if request.user.role == 'doctor':
            if request.user not in report.authenticated_by.all():
                report.authenticated_by.add(request.user)
                messages.success(request, 'Report authenticated successfully.')
            else:
                messages.info(request, 'You have already authenticated this report.')
        else:
            messages.error(request, 'You are not authorized to authenticate reports.')
        return redirect('report_detail', pk=pk)

@method_decorator(csrf_exempt, name='dispatch')
class ChatView(LoginRequiredMixin, View):
    template_name = 'predictions/chat.html'

    def get(self, request):
        # Initialize chat history if not present
        if 'chat_history' not in request.session:
            request.session['chat_history'] = []
        
        # Preparing history for display
        display_history = []
        for msg in request.session.get('chat_history', []):
            sender = 'user' if msg['role'] == 'user' else 'bot'
            display_history.append({'sender': sender, 'text': msg['content']})
            
        return render(request, self.template_name, {"chat_history": display_history})

    def post(self, request):
        if 'chat_history' not in request.session:
            request.session['chat_history'] = []

        user_input = request.POST.get("user_input", "").strip()
        if user_input:
            chat_history = request.session['chat_history']

            # Append user query
            chat_history.append({"role": "user", "content": user_input})

            prompt = (
                "You are 'CliniPaws', a professional veterinary assistant. "
                "Analyze the query and provide a clear, concise, and informative response suitable for doctors and students. "
                "Ensure the response is of normal length, avoiding unnecessary verbosity.\n"
                f"Query: {user_input}\n"
                "Constraints: Do not use special characters, symbols, or HTML tags. Stay strictly within the veterinary context.\n"
                "Closing: Always end your response with: 'Is there anything else about veterinary medicine you would like to ask?'"
            )

            # Call to AI model
            # We pass the history + system prompt to the API
            # Note: call_chat_api handles the last 6 messages logic
            bot_response = call_chat_api(chat_history + [{"role": "system", "content": prompt}])

            # Append assistant's answer
            chat_history.append({"role": "assistant", "content": bot_response})

            request.session['chat_history'] = chat_history
            request.session.modified = True
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action="Interacted with AI Chat",
                details="Used AI chat for assistance"
            )
            
        return redirect('chat')

class DeleteReportView(LoginRequiredMixin, View):
    """Admin-only view to delete reports"""
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to delete reports.')
            return redirect('dashboard')
        
        report = get_object_or_404(Report, pk=pk)
        report.delete()
        messages.success(request, f'Report #{pk} has been deleted successfully.')
        return redirect('dashboard')

class DeleteImageReportView(LoginRequiredMixin, View):
    """Admin-only view to delete image reports"""
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to delete image reports.')
            return redirect('dashboard')
        
        from .models import ImageReport
        image_report = get_object_or_404(ImageReport, pk=pk)
        image_report.delete()
        messages.success(request, f'Image Report #{pk} has been deleted successfully.')
        return redirect('dashboard')

class AdminUsersView(LoginRequiredMixin, TemplateView):
    """Admin-only view to see all users"""
    template_name = 'predictions/admin_users.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import User
        context['users'] = User.objects.all().order_by('-date_joined')
        return context

class CheckByImageView(LoginRequiredMixin, View):
    """View for image-based disease detection"""
    template_name = 'predictions/check_by_image.html'
    
    def get(self, request):
        from .forms import ImageReportForm
        form = ImageReportForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        from .forms import ImageReportForm
        from .models import ImageReport
        
        form = ImageReportForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Save the form to get the image path
            image_report = form.save(commit=False)
            image_report.created_by = request.user
            image_report.save()
            
            # Get the uploaded image path
            image_path = image_report.original_image.path
            
            try:
                # Import detector
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from Roboflow.detector import SkinDiseaseDetector
                
                # Run detection and get annotated image
                detector = SkinDiseaseDetector()
                annotated_path, detection_result = detector.draw_detections(image_path)
                
                # Save annotated image to model
                from django.core.files import File
                with open(annotated_path, 'rb') as f:
                    image_report.annotated_image.save(
                        os.path.basename(annotated_path),
                        File(f),
                        save=False
                    )
                
                # Process detection results
                detected = detection_result.get('detected', False)
                confidence_raw = detection_result.get('confidence', 0.0)
                disease = detection_result.get('disease', 'No Disease Detected')
                
                # Convert confidence to percentage (0.711 -> 71.1)
                confidence_percentage = confidence_raw * 100
                
                # Treat "Normal", "Healthy", or similar as no disease
                disease_lower = disease.lower()
                healthy_keywords = ['normal', 'healthy', 'no disease', 'fine', 'ok']
                if any(keyword in disease_lower for keyword in healthy_keywords):
                    detected = False
                    disease = "No Disease Detected"
                
                # Update report with detection results
                image_report.detected = detected
                image_report.confidence = confidence_percentage
                image_report.predicted_disease = disease
                image_report.detection_details = detection_result.get('details')
                
                # Generate AI report if disease detected
                print(f"DEBUG: Detected={detected}, Disease={disease}")
                if detected and disease != "No Disease Detected":
                    try:
                        from livestock_disease_prediction.utils import generate_ai_report
                        # Provide context that this was an image-based detection
                        context_str = "Visual signs and skin lesions observed in the uploaded image analysis"
                        print("DEBUG: Calling generate_ai_report...")
                        ai_report = generate_ai_report(disease, context_str)
                        print(f"DEBUG: AI Report generated (len={len(ai_report)})")
                        
                        # Format the full description with header
                        image_report.description = (
                            f"**Predicted Disease:** {disease}\n"
                            f"**Confidence:** {confidence_percentage:.1f}%\n"
                            f"**Model Accuracy:** {confidence_percentage:.1f}%\n\n"
                            f"{ai_report}"
                        )
                    except Exception as e:
                        print(f"DEBUG: Error generating AI report: {e}")
                        image_report.description = f"Error generating AI report: {str(e)}"
                
                image_report.save()
                
                # Clean up temporary annotated file
                if os.path.exists(annotated_path):
                    os.remove(annotated_path)
                
                messages.success(request, 'Image analyzed successfully!')
                
                # Log activity
                UserActivity.objects.create(
                    user=request.user,
                    action="Generated Image-Based Report",
                    details=f"Report ID: {image_report.id}, Disease: {image_report.predicted_disease}, Animal: {image_report.animal}"
                )
                
                return redirect('image_report_detail', pk=image_report.pk)
                
            except Exception as e:
                messages.error(request, f'Detection failed: {str(e)}')
                return redirect('check_by_image')
        
        return render(request, self.template_name, {'form': form})



class ImageReportDetailView(LoginRequiredMixin, DetailView):
    """View for displaying image detection results"""
    model = None  # Will be set dynamically
    template_name = 'predictions/image_report_detail.html'
    
    def get_object(self):
        from .models import ImageReport
        return get_object_or_404(ImageReport, pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.all().order_by('created_at')
        if self.request.user.role == 'doctor':
            from .forms import ImageCommentForm
            context['comment_form'] = ImageCommentForm()
        return context


class AuthenticateImageReportView(LoginRequiredMixin, View):
    """View for doctors to authenticate image reports"""
    def post(self, request, pk):
        from .models import ImageReport
        image_report = get_object_or_404(ImageReport, pk=pk)
        if request.user.role == 'doctor':
            if request.user not in image_report.authenticated_by.all():
                image_report.authenticated_by.add(request.user)
                messages.success(request, 'Image report authenticated successfully.')
            else:
                messages.info(request, 'You have already authenticated this report.')
        else:
            messages.error(request, 'You are not authorized to authenticate reports.')
        return redirect('image_report_detail', pk=pk)


class AddImageCommentView(LoginRequiredMixin, View):
    """View for doctors to add comments to image reports"""
    def post(self, request, pk):
        from .models import ImageReport
        from .forms import ImageCommentForm
        
        image_report = get_object_or_404(ImageReport, pk=pk)
        if request.user.role == 'doctor':
            form = ImageCommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.image_report = image_report
                comment.doctor = request.user
                comment.save()
                messages.success(request, 'Comment added successfully.')
            else:
                messages.error(request, 'Error adding comment.')
        else:
            messages.error(request, 'Only doctors can add comments.')
        return redirect('image_report_detail', pk=pk)


class DeleteImageCommentView(LoginRequiredMixin, View):
    """View for doctors to delete their own comments on image reports"""
    def post(self, request, pk, comment_id):
        from .models import ImageComment
        comment = get_object_or_404(ImageComment, pk=comment_id, image_report__pk=pk)
        
        # Only the comment author can delete their own comment
        if request.user == comment.doctor:
            comment.delete()
            messages.success(request, 'Comment deleted successfully.')
        else:
            messages.error(request, 'You can only delete your own comments.')
        
        return redirect('image_report_detail', pk=pk)


class DownloadSymptomReportPDFView(LoginRequiredMixin, View):
    """View to download symptom-based report as PDF"""
    def get(self, request, pk):
        from django.http import HttpResponse
        from livestock_disease_prediction.pdf_utils import generate_symptom_report_pdf
        
        report = get_object_or_404(Report, pk=pk)
        
        # Generate PDF
        pdf_buffer = generate_symptom_report_pdf(report)
        
        # Create response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f'symptom_report_{report.id}_{report.predicted_disease.replace(" ", "_")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            action="Downloaded PDF Report",
            details=f"Symptom-based Report ID: {report.id}, Disease: {report.predicted_disease}"
        )
        
        return response


class DownloadImageReportPDFView(LoginRequiredMixin, View):
    """View to download image-based report as PDF"""
    def get(self, request, pk):
        from django.http import HttpResponse
        from livestock_disease_prediction.pdf_utils import generate_image_report_pdf
        from .models import ImageReport
        
        image_report = get_object_or_404(ImageReport, pk=pk)
        
        # Generate PDF
        pdf_buffer = generate_image_report_pdf(image_report)
        
        # Create response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f'image_report_{image_report.id}_{image_report.predicted_disease.replace(" ", "_")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            action="Downloaded PDF Report",
            details=f"Image-based Report ID: {image_report.id}, Disease: {image_report.predicted_disease}"
        )
        
        return response


def about(request):
    return render(request, 'about/about.html')


class BlockUserView(LoginRequiredMixin, View):
    """Admin-only view to block users"""
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to block users.')
            return redirect('admin_users')
        
        from accounts.models import User
        user_to_block = get_object_or_404(User, pk=pk)
        
        if user_to_block.is_superuser:
            messages.error(request, 'Cannot block superusers.')
        else:
            user_to_block.is_blocked = True
            user_to_block.save()
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action="Blocked User",
                details=f"Blocked user: {user_to_block.username}"
            )
            
            messages.success(request, f'User {user_to_block.username} has been blocked.')
            
        return redirect('admin_users')


class UnblockUserView(LoginRequiredMixin, View):
    """Admin-only view to unblock users"""
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to unblock users.')
            return redirect('admin_users')
        
        from accounts.models import User
        user_to_unblock = get_object_or_404(User, pk=pk)
        
        user_to_unblock.is_blocked = False
        user_to_unblock.save()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            action="Unblocked User",
            details=f"Unblocked user: {user_to_unblock.username}"
        )
        
        messages.success(request, f'User {user_to_unblock.username} has been unblocked.')
            
        return redirect('admin_users')


class DeleteUserView(LoginRequiredMixin, View):
    """Admin-only view to permanently delete a user account"""
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to delete users.')
            return redirect('admin_users')
            
        from accounts.models import User, UserActivity
        user_to_delete = get_object_or_404(User, pk=pk)
        
        if user_to_delete.is_superuser:
            messages.error(request, 'Cannot delete superusers.')
        else:
            username = user_to_delete.username
            user_to_delete.delete()
            
            # Log this administrative action (logged against the admin user)
            UserActivity.objects.create(
                user=request.user,
                action="Deleted User Account",
                details=f"Permanently deleted user account: {username}"
            )
            
            messages.success(request, f'User {username} has been permanently deleted.')
            
        return redirect('admin_users')


class AdminMessagesView(LoginRequiredMixin, TemplateView):
    """Admin inbox for contact messages from blocked users"""
    template_name = 'predictions/admin_messages.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import ContactMessage
        # Mark all as read when admin visits the inbox
        unread_messages = ContactMessage.objects.filter(is_read=False)
        unread_messages.update(is_read=True)
        
        context['messages_list'] = ContactMessage.objects.all()
        return context


class DeleteAdminMessageView(LoginRequiredMixin, View):
    """Admin-only view to delete contact messages"""
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to delete messages.')
            return redirect('dashboard')
            
        from accounts.models import ContactMessage
        message = get_object_or_404(ContactMessage, pk=pk)
        message.delete()
        messages.success(request, 'Message deleted successfully.')
            
        return redirect('admin_messages')


class UserActivityView(LoginRequiredMixin, TemplateView):
    """Admin-only view to see activity logs for a specific user"""
    template_name = 'predictions/user_activity.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import User
        target_user = get_object_or_404(User, pk=self.kwargs['pk'])
        context['target_user'] = target_user
        context['activities'] = target_user.activities.all().order_by('-timestamp')
        return context


class ClearUserActivityView(LoginRequiredMixin, View):
    """Admin-only view to clear activity logs for a specific user"""
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to perform this action.')
            return redirect('dashboard')
            
        from accounts.models import User, UserActivity
        target_user = get_object_or_404(User, pk=pk)
        
        # Delete all activities for this user
        count = target_user.activities.count()
        target_user.activities.all().delete()
        
        # Log this administrative action
        UserActivity.objects.create(
            user=request.user,
            action="Cleared User History",
            details=f"Cleared {count} activity logs for user: {target_user.username}"
        )
        
        messages.success(request, f'Activity history for {target_user.username} has been cleared.')
        return redirect('user_activity', pk=pk)


class ReactAdminMessageView(LoginRequiredMixin, View):
    """Admin-only view to react to contact messages"""
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, 'You are not authorized to react to messages.')
            return redirect('dashboard')
            
        from accounts.models import ContactMessage
        message = get_object_or_404(ContactMessage, pk=pk)
        reaction = request.POST.get('reaction')
        
        if reaction in ['up', 'down', 'none']:
            message.reaction = reaction
            message.save()
            # We don't need a success message for a simple reaction to keep it "quiet"
        else:
            messages.error(request, 'Invalid reaction.')
            
        return redirect('admin_messages')