from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from core import models


def create_user(email='test@email.com', password='test123*'):
    """Helper function to create new user"""
    return get_user_model().objects.create_user(email, password)

class ModelTests(TestCase):

    def test_create_user_with_email_successful(self):
        """Test creating a new user with an email is successful"""
        email = 'test@email.com'
        password = '<PASSWORD>'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test the email for a new user is normalized"""
        email = 'Test@email.com'
        user = get_user_model().objects.create_user(email, 'test123')

        self.assertEqual(user.email, "test@email.com")

    def test_new_user_without_email_raises_error(self):


        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):

        user = get_user_model().objects.create_superuser(
            email='test@email.com',
            password='Qwerty123*'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        """Test creating a recipe"""
        user = get_user_model().objects.create_user(
            email='test@email.com',
            password='Test123*'
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title='Test recipe',
            time_minutes=5,
            price=Decimal('5.00'),
            description='Test recipe description',
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        """Test creating a tag is successful"""
        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Test tag')

        self.assertEqual(str(tag), tag.name)