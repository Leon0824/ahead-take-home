from http import HTTPStatus

from httpx import AsyncClient
import pytest



class TestSystem:
    @pytest.mark.asyncio
    async def test_get_openapi_json(self, async_client: AsyncClient):
        response = await async_client.get('/openapi.json')
        assert response.status_code == HTTPStatus.OK


    @pytest.mark.asyncio
    async def test_get_system_health(self, async_client: AsyncClient):
        response = await async_client.get('/system/health')
        assert response.status_code == HTTPStatus.OK