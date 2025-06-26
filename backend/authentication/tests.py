from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse


class UserCreationTests(TestCase):
    def test_user_creation(self):

        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)


class AuthMiddlewareTests(TestCase):
    def test_authentication_required(self):

        response = self.client.get('/protected-view/', follow=True)

        self.assertRedirects(response, '/accounts/login/?next=/protected-view/')


        User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get('/protected-view/')
        self.assertEqual(response.status_code, 200)