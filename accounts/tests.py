from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory

from .models import UserProfile
from .serializers import RegisterSerializer
from .permissions import IsVerifiedLabSample


class RegistrationRoleSecurityTests(TestCase):
    def test_public_registration_cannot_assign_privileged_role(self):
        serializer = RegisterSerializer()
        user = serializer.create({
            'username': 'public-user',
            'email': 'public@example.test',
            'first_name': 'Public',
            'last_name': 'User',
            'password': 'Safe-Test-Password-984!',
            'password2': 'Safe-Test-Password-984!',
            'phone': '09120000000',
            'national_id': '1234567890',
            'role': 'ADMIN',
        })

        self.assertEqual(user.profile.role, 'FARMER')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class VerifiedLabPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsVerifiedLabSample()

    def test_unverified_lab_is_denied(self):
        user = User.objects.create_user(username='lab-pending', password='test-password')
        UserProfile.objects.create(user=user, role='LAB', phone='09120000001', is_verified=False)
        request = self.factory.post('/api/analyses/lab-register/')
        request.user = user

        self.assertFalse(self.permission.has_permission(request, None))

    def test_verified_lab_is_allowed(self):
        user = User.objects.create_user(username='lab-approved', password='test-password')
        UserProfile.objects.create(user=user, role='LAB', phone='09120000002', is_verified=True)
        request = self.factory.post('/api/analyses/lab-register/')
        request.user = user

        self.assertTrue(self.permission.has_permission(request, None))
