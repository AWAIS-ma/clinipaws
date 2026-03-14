from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class BlockedUserMiddleware:
    """
    Middleware to ensure that any user marked as 'is_blocked' is immediately 
    logged out and redirected to the blocked notification page on their next request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if the user is blocked in the database
            if getattr(request.user, 'is_blocked', False):
                # Only logout if we are not already on the blocked page or trying to contact admin
                # (prevents potential issues or redirect loops, although logout should handle it)
                blocked_url = reverse('blocked')
                contact_admin_url = reverse('contact_admin')
                
                if request.path != blocked_url and request.path != contact_admin_url:
                    logout(request)
                    messages.error(request, 'Your account has been blocked by the administrator.')
                    return redirect('blocked')
        
        response = self.get_response(request)
        return response
