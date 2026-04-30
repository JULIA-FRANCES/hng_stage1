from django.urls import path, include
from django.http import JsonResponse


def handler404(request, exception):
    return JsonResponse(
        {"status": "error", "message": "Profile not found."},
        status=404
    )


urlpatterns = [
    path('', include('profiles.urls')),
    path('', include('authentication.urls')),
]