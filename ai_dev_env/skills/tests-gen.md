## MANDATORY RULES (STRICT ENFORCEMENT)
1. **Absolute Imports**: Use `from <app>.models import ...`.
2. **Fixture Control**: ONLY use `api_client` and `django_db`.
3. **Mandatory Fixture Injection**: Every test file MUST define its own `api_client` fixture locally.
4. **Core API Coverage (3 TESTS REQUIRED)**:
   - `test_list_success`
   - `test_create_success`
   - `test_detail_success`
5. **Database Setup**: Mark class with `@pytest.mark.django_db`.
6. **Conciseness**: Keep tests simple. No mocks.

## TEST TEMPLATE (CORE)
```python
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from <app>.models import <Entity>

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class Test<Entity>Views:
    def test_list_success(self, api_client):
        <Entity>.objects.create(name="Sample")
        url = reverse('<entity>-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_success(self, api_client):
        url = reverse('<entity>-list')
        payload = {"name": "New Entity"}
        response = api_client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_detail_success(self, api_client):
        obj = <Entity>.objects.create(name="Detail")
        url = reverse('<entity>-detail', kwargs={'pk': obj.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
```
