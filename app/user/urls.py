from django.urls import path
from user import views

"""URL mapping for user API"""

app_name = 'user'

urlpatterns = [
    path('create/', views.CreateUserView.as_view(), name='create'),
]