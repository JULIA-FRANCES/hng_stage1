from django.urls import path
from . import views

urlpatterns = [
    path('auth/github', views.github_login),
    path('auth/github/', views.github_login),
    path('auth/github/callback', views.github_callback),
    path('auth/github/callback/', views.github_callback),
    path('auth/refresh', views.refresh_token_view),
    path('auth/refresh/', views.refresh_token_view),
    path('auth/logout', views.logout_view),
    path('auth/logout/', views.logout_view),
    path('auth/whoami', views.whoami_view),
    path('auth/whoami/', views.whoami_view),
    path('api/users/me', views.users_me_view),
    path('api/users/me/', views.users_me_view),
]