from django.urls import path
from profiles import views

urlpatterns = [
    path('profiles', views.profiles_router, name='profiles'),
    path('profiles/<uuid:pk>', views.profile_detail, name='profile-detail'),
]