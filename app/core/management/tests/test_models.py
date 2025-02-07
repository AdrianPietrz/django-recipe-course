from django.test import TestCase
from django.contrib.auth import get_user_model

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