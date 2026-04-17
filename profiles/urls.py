from django.urls import path
from profiles import views

urlpatterns = [
    path('api/profiles', views.profiles_router, name='profiles'),
    path('api/profiles/<str:pk>', views.profile_detail, name='profile-detail'),
]