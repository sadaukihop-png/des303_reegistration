from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('guest-register/', views.guest_register, name='guest_register'),
    path('registered-view/', views.registered_view, name='registered_view'),
]