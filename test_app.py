import pytest
from fastapi.testclient import TestClient
from app import app, get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

# Mock для асинхронной сессии базы данных
@pytest.fixture
async def async_session():
    # Здесь можно создать mock-сессию или использовать реальную тестовую базу данных
    pass

# Замена зависимости get_db_session на mock-сессию
app.dependency_overrides[get_db_session] = lambda: async_session

client = TestClient(app)

# Тесты для эндпоинтов пользователей

def test_create_user():
    response = client.post("/users", json={"id": 1, "name": "John Doe", "email": "john@example.com"})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "John Doe", "email": "john@example.com"}

def test_get_user():
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "John Doe", "email": "john@example.com"}

def test_update_user():
    response = client.put("/users/1", json={"id": 1, "name": "Jane Doe", "email": "jane@example.com"})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Jane Doe", "email": "jane@example.com"}

def test_delete_user():
    response = client.delete("/users/1")
    assert response.status_code == 200
    assert response.json() == {"message": "User deleted"}

# Тесты для эндпоинтов продуктов

def test_create_product():
    response = client.post("/products", json={"id": 1, "name": "Laptop", "price": 999.99})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Laptop", "price": 999.99}

def test_get_product():
    response = client.get("/products/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Laptop", "price": 999.99}

def test_update_product():
    response = client.put("/products/1", json={"id": 1, "name": "Notebook", "price": 499.99})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Notebook", "price": 499.99}

def test_delete_product():
    response = client.delete("/products/1")
    assert response.status_code == 200
    assert response.json() == {"message": "Product deleted"}

# Тесты для эндпоинтов заказов

def test_create_order():
    response = client.post("/orders", json={"id": 1, "user_id": 1, "product_id": 1, "quantity": 2})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "user_id": 1, "product_id": 1, "quantity": 2}

def test_get_order():
    response = client.get("/orders/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "user_id": 1, "product_id": 1, "quantity": 2}

def test_update_order():
    response = client.put("/orders/1", json={"id": 1, "user_id": 1, "product_id": 1, "quantity": 3})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "user_id": 1, "product_id": 1, "quantity": 3}

def test_delete_order():
    response = client.delete("/orders/1")
    assert response.status_code == 200
    assert response.json() == {"message": "Order deleted"}

# Тесты для миграционных эндпоинтов

def test_migrate_users():
    response = client.get("/migrate/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_migrate_products():
    response = client.get("/migrate/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_migrate_orders():
    response = client.get("/migrate/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# Тест для эндпоинта health check

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}