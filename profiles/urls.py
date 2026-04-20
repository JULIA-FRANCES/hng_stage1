from django.urls import path
from profiles import views

urlpatterns = [
    path('api/profiles/search', views.profile_search),
    path('api/profiles/search/', views.profile_search),
    path('api/profiles', views.profiles_router),
    path('api/profiles/', views.profiles_router),
    path('api/profiles/<str:pk>', views.profile_detail),
    path('api/profiles/<str:pk>/', views.profile_detail),
]