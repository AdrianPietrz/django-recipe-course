from django.contrib.auth import get_user, get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer
from django.urls import reverse

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def create_user(email='example@email.com', password='Test123*'):
    """Helper function to create new user"""
    return get_user_model().objects.create_user(email=email, password=password)


def detail_url(ingredient_id):
    """Return ingredient detail URL"""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


class PublicIngredientsApiTests(TestCase):
    """Test the publicly available ingredients API"""

    def setUp(self):
        self.client: APIClient = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEquals(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test the private ingredients API"""

    def setUp(self):
        self.client: APIClient = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients_list(self):
        """Test retrieving a list of ingredients"""
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data, IngredientSerializer(Ingredient.objects.all().order_by('-name'), many=True).data)

    def test_ingredients_limited_to_user(self):
        """Test that ingredients returned are for the authenticated user"""
        user2 = create_user(email='other@email.com', password='Test123*')
        Ingredient.objects.create(user=user2, name='Vinegar')
        ingredient = Ingredient.objects.create(user=self.user, name='Tumeric')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """Test updating an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Cabbage')
        payload = {'name': 'Coriander'}
        url = detail_url(ingredient.id)

        res = self.client.patch(url, payload)
        ingredient.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(ingredient.name, payload['name'])

    def test_update_user_error(self):
        """Test that updating an ingredient with another user returns an error"""
        user2 = create_user(email='other@email.com', password='Test123*')
        ingredient = Ingredient.objects.create(user=user2, name='Vinegar')
        payload = {'user_id': self.user.id}
        url = detail_url(ingredient.id)

        self.client.patch(url, payload)
        ingredient.refresh_from_db()

        self.assertNotEquals(ingredient.user, self.user)

    def test_delete_ingredient(self):
        """Test deleting an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Cabbage')
        url = detail_url(ingredient.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())

    def test_user_delete_other_user_ingredient_returns_error(self):
        """Test that deleting an ingredient with another user returns an error"""
        user2 = create_user(email='other@email.com', password='Test123*')
        ingredient = Ingredient.objects.create(user=user2, name='Vinegar')
        url = detail_url(ingredient.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Ingredient.objects.filter(id=ingredient.id).exists())

    def filter_ingredients_assigned_to_recipes(self):
        """Test filtering ingredients assigned to recipes"""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Apples')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Chicken')
        recipe = Recipe.objects.create(user=self.user, title='Chocole Chicken', time_minutes=10, price=5.00)
        recipe.ingredients.add(ingredient1)

        params = {
            'assigned_only': True
        }

        res = self.client.get(INGREDIENTS_URL, params)

        serialized_ingredient1 = IngredientSerializer(ingredient1)
        serialized_ingredient2 = IngredientSerializer(ingredient2)

        self.assertIn(serialized_ingredient1.data, res.data)
        self.assertNotIn(serialized_ingredient2.data, res.data)

    def filtered_ingredients_unique(self):
        """Test filtering ingredients unique"""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Chicken')
        Ingredient.objects.create(user=self.user, name='Apples')

        recipe1 = Recipe.objects.create(user=self.user, title='Chocole Chicken', time_minutes=10, price=5.00)
        recipe2 = Recipe.objects.create(user=self.user, title='Chocole Chicken 2', time_minutes=12, price=6.00)
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient1)

        params = {
            'assigned_only': True
        }

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': params})

        self.assertEqual(len(res.data), 1)
