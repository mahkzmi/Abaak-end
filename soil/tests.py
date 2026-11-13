from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.exceptions import PermissionDenied
from unittest.mock import Mock

from accounts.models import UserProfile
from .views import FarmViewSet, SoilAnalysisViewSet, SoilSampleViewSet


class FarmCreationSecurityTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.create_farm_view = SoilAnalysisViewSet.as_view({'post': 'create_farm'})

    def _post_as(self, user):
        request = self.factory.post(
            '/api/analyses/create-farm/',
            {'name': 'Test farm', 'coordinates': [[51.0, 35.0], [51.1, 35.0],
                                                   [51.1, 35.1], [51.0, 35.0]]},
            format='json',
        )
        force_authenticate(request, user=user)
        return self.create_farm_view(request)

    def test_non_farmer_cannot_create_farm(self):
        user = User.objects.create_user(username='viewer', password='test-password')
        UserProfile.objects.create(user=user, role='VIEWER', phone='09120000011')

        response = self._post_as(user)

        self.assertEqual(response.status_code, 403)

    def test_farmer_without_farmer_profile_cannot_create_farm(self):
        user = User.objects.create_user(username='farmer-without-record', password='test-password')
        UserProfile.objects.create(user=user, role='FARMER', phone='09120000012')

        response = self._post_as(user)

        self.assertEqual(response.status_code, 403)


class DirectAnalysisWriteSecurityTests(TestCase):
    def test_direct_analysis_mutations_require_admin_or_expert(self):
        view = SoilAnalysisViewSet()
        for action_name in ('create', 'update', 'partial_update', 'destroy'):
            view.action = action_name
            permissions = view.get_permissions()
            self.assertEqual(len(permissions), 1)
            self.assertEqual(permissions[0].__class__.__name__, 'IsAdminOrExpert')



class SoilSampleMutationSecurityTests(TestCase):
    def test_sample_edits_and_deletes_require_admin_or_expert(self):
        view = SoilSampleViewSet()
        for action_name in ('update', 'partial_update', 'destroy'):
            view.action = action_name
            permissions = view.get_permissions()
            self.assertEqual(len(permissions), 1)
            self.assertEqual(permissions[0].__class__.__name__, 'IsAdminOrExpert')


class GenericFarmCreationSecurityTests(TestCase):
    def test_non_farmer_role_cannot_create_farm_even_with_request(self):
        user = User.objects.create_user(username='non-farmer-farm-api', password='test-password')
        UserProfile.objects.create(user=user, role='VIEWER', phone='09120000013')
        request = APIRequestFactory().post('/api/farms/', {}, format='json')
        force_authenticate(request, user=user)

        view = FarmViewSet()
        view.request = request

        with self.assertRaises(PermissionDenied):
            view.perform_create(Mock())
