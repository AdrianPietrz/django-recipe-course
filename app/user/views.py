from rest_framework import generics
from user.serializers import UserSerializer

"""Views for the user API"""

class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system"""
    serializer_class = UserSerializer