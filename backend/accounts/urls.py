from django.urls import path

from .views import (
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    PasswordChangeAPIView,
    ProfileAPIView,
    RegisterAPIView,
)

urlpatterns = [
    path('auth/register/', RegisterAPIView.as_view(), name='register'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'),
    path('auth/me/', MeAPIView.as_view(), name='me'),
    path('auth/password/', PasswordChangeAPIView.as_view(), name='password-change'),
    path('profile/', ProfileAPIView.as_view(), name='profile'),
]
