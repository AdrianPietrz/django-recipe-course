import os
import tempfile

from PIL import Image

import recipe
from core.models import Recipe, Tag, Ingredient
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer
from rest_framework import status
from rest_framework.test import APIClient

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return recipe image URL"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    """Helper function to create new recipe"""''
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00,
        'link': 'https://www.google.com',
        'description': 'Sample description',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self):
        self.client: APIClient = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API access"""

    def setUp(self):
        self.client: APIClient = APIClient()
        self.user = create_user(email='test@email.com', password='Test123*')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = create_user(email='other@email.com', password='Test123*')
        create_recipe(user=user2)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test retrieving a recipe detail"""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)

        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Test recipe',
            'time_minutes': 30,
            'price': 5.00,
            'link': 'https://www.google.com',
            'description': 'Sample description',
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Recipe.objects.count(), 1)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(self.user, recipe.user)

    def test_partial_update_recipe(self):
        """Test updating a recipe with patch"""
        link = 'https://www.google.com'
        recipe = create_recipe(user=self.user, title='Old title', link=link)
        payload = {'title': 'New title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, link)

    def test_full_update_recipe(self):
        """Test updating a recipe with put"""
        recipe = create_recipe(user=self.user, title='Old title', link='https://www.google.com', time_minutes=10,
                               price=5.00, description='Sample description')
        payload = {
            'title': 'New title',
            'time_minutes': 20,
            'price': 10.00,
            'link': 'https://www.youtube.com',
            'description': 'New description',
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(self.user, recipe.user)

    def test_update_user_returns_error(self):
        """Test that updating a recipe with another user returns an error"""
        user2 = create_user(email='other@email.com', password='Test123*')
        recipe = create_recipe(user=self.user)
        payload = {'user': user2.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe"""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_user_delete_other_user_recipe_returns_error(self):
        """Test that deleting a recipe with another user returns an error"""
        user2 = create_user(email='other@email.com', password='Test123*')
        recipe = create_recipe(user=user2)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with tags"""
        payload = {
            'title': 'Test recipe with two tags',
            'tags': [
                {
                    'name': 'Vegan',
                },
                {
                    'name': 'Dessert',
                }
            ],
            'time_minutes': 30,
            'price': 5.00,
            'link': 'https://www.google.com',
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        for tag in payload['tags']:
            self.assertTrue(recipe.tags.filter(name=tag['name']).exists())

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tags"""
        tag = Tag.objects.create(user=self.user, name='Vegan')
        payload = {
            'price': 5.00,
            'link': 'https://www.google.com',
            'title': 'Test recipe with two tags',
            'time_minutes': 30,
            'tags': [
                {
                    'name': 'Vegan',
                },
                {
                    'name': 'Dessert',
                }
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag, recipe.tags.all())
        for tag in payload['tags']:
            self.assertTrue(recipe.tags.filter(name=tag['name']).exists())

    def test_update_recipe_with_new_tags(self):
        """Test updating a recipe with new tags"""
        recipe = create_recipe(user=self.user)
        payload = {
            'tags': [
                {
                    'name': 'Vegan',
                },
                {
                    'name': 'Dessert',
                }
            ]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 2)

    def test_update_recipe_with_existing_tags(self):
        """Test updating a recipe with existing tags"""
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag1)
        payload = {
            'tags': [
                {
                    'name': 'Dessert',
                }
            ]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 1)
        self.assertNotIn(tag1, recipe.tags.all())
        self.assertIn(tag2, recipe.tags.all())

    def test_update_recipe_clear_tags(self):
        """Test updating a recipe with clear tags"""
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag1)
        recipe.tags.add(tag2)
        payload = {
            'tags': []
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
        self.assertNotIn(tag1, recipe.tags.all())
        self.assertNotIn(tag2, recipe.tags.all())

    def test_create_recipe_with_new_ingredients(self):
        """Test creating a recipe with ingredients"""
        payload = {
            'title': 'Test recipe with two ingredients',
            'price': 5.00,
            'link': 'https://www.google.com',
            'time_minutes': 30,
            'ingredients': [
                {
                    'name': 'Cucumber',
                },
                {
                    'name': 'Salt',
                }
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload['ingredients']:
            self.assertTrue(recipe.ingredients.filter(name=ingredient['name'], user=self.user).exists())

    def test_create_recipe_with_existing_ingredients(self):
        """Test creating a recipe with existing ingredients"""
        ingredient = Ingredient.objects.create(user=self.user, name='Cucumber')
        payload = {
            'title': 'Test recipe with two ingredients',
            'price': 5.00,
            'link': 'https://www.google.com',
            'time_minutes': 30,
            'ingredients': [
                {
                    'name': 'Cucumber',
                },
                {
                    'name': 'Salt',
                }
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())

        for ingredient in payload['ingredients']:
            self.assertTrue(recipe.ingredients.filter(name=ingredient['name'], user=self.user).exists())

    def test_update_recipe_with_new_ingredients(self):
        """Test updating a recipe with new ingredients"""
        recipe = create_recipe(user=self.user)
        payload = {
            'ingredients': [
                {
                    'name': 'Cucumber',
                },
            ]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 1)
        ingredient = Ingredient.objects.get(name='Cucumber', user=self.user)
        self.assertIn(ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test updating a recipe with new ingredients"""
        ingredient = Ingredient.objects.create(user=self.user, name='Cucumber')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Salt')
        payload = {
            'ingredients': [
                {
                    'name': 'Salt',
                }
            ]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_update_recipe_clear_ingredient(self):
        """Test updating a recipe with empty ingredient list clear ingredient list"""
        ingredient = Ingredient.objects.create(user=self.user, name='Cucumber')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {
            'ingredients': []
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_filter_by_tags(self):
        """Filter recipes by tags"""
        recipe1 = create_recipe(user=self.user, title='Vegetable curry')
        recipe2 = create_recipe(user=self.user, title='Fish and fries')
        tag1 = Tag.objects.create(user=self.user, name='Vegetarian')
        tag2 = Tag.objects.create(user=self.user, name='Meat')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe3 = create_recipe(user=self.user, title='Spaghetti')

        params = {
            'tags': f'{tag1.id},{tag2.id}',
        }

        res = self.client.get(RECIPES_URL, params)

        serialized_recipe1 = RecipeSerializer(recipe1)
        serialized_recipe2 = RecipeSerializer(recipe2)
        serialized_recipe3 = RecipeSerializer(recipe3)

        self.assertIn(serialized_recipe1.data, res.data)
        self.assertIn(serialized_recipe2.data, res.data)
        self.assertNotIn(serialized_recipe3.data, res.data)

    def test_filter_by_ingredients(self):
        """Filter recipes by ingredients"""
        recipe1 = create_recipe(user=self.user, title='Vegetable curry')
        recipe2 = create_recipe(user=self.user, title='Fish and fries')
        ingredient1 = Ingredient.objects.create(user=self.user, name='Cucumber')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Fish')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        recipe3 = create_recipe(user=self.user, title='Spaghetti')

        params = {
            'ingredients': f'{ingredient1.id},{ingredient2.id}',
        }

        res = self.client.get(RECIPES_URL, params)

        serialized_recipe1 = RecipeSerializer(recipe1)
        serialized_recipe2 = RecipeSerializer(recipe2)
        serialized_recipe3 = RecipeSerializer(recipe3)

        self.assertIn(serialized_recipe1.data, res.data)
        self.assertIn(serialized_recipe2.data, res.data)
        self.assertNotIn(serialized_recipe3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API"""

    def setUp(self):
        self.client: APIClient = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@user.com',
            'Qwerty123*'
        )
        self.client.force_authenticate(user=self.user)
        self.recipe: Recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading image to recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}

            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading image with bad request"""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'i am not an image'}

        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
