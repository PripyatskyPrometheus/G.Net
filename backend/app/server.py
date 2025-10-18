from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List


# Создаем приложение FastAPI
app = FastAPI(title="WiFi Finder API", version="1.0.0")

# CORS для мобильного приложения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы откуда угодно
    allow_credentials=True,
    allow_methods=["*"],   # Разрешаем все методы (GET, POST, etc.)
    allow_headers=["*"],   # Разрешаем все заголовки
)

# Модель данных для точки WiFi
class WiFiPoint(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    address: str = None
    type: str = None

# Заглушка с тестовыми данными
test_points = [
    WiFiPoint(
        id=1,
        name="Кафе 'Кофеин'",
        latitude=59.934280, 
        longitude=30.335098,
        address="Невский пр., 123",
        type="cafe"
    ),
    WiFiPoint(
        id=2,
        name="Библиотека им. Маяковского",
        latitude=59.931100,
        longitude=30.342150,
        address="наб. реки Фонтанки, 46", 
        type="library"
    ),
    WiFiPoint(
        id=3, 
        name="Макдональдс", 
        latitude=59.932500, 
        longitude=30.341000, 
        address="Лиговский пр., 274", 
        type="fast_food"),
    WiFiPoint(
        id=4, 
        name="Парк им. Бабушкина", 
        latitude=59.940000, 
        longitude=30.330000, 
        address="ул. Бабушкина, 125", 
        type="park"),
    WiFiPoint(
        id=5, 
        name="Станция метро Площадь Восстания", 
        latitude=59.931800, 
        longitude=30.360500, 
        address="пл. Восстания", 
        type="metro"),
]


@app.get("/")
async def root():
    return {"message": "G.NET API работает!", "status": "OK"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ОСНОВНОЙ ЭНДПОИНТ ДЛЯ ПРИЛОЖЕНИЯ
@app.get("/wifi-points", response_model=List[WiFiPoint])
async def get_wifi_points(city: str = "spb"):
    """
    Возвращает список точек WiFi для указанного города
    """
    # Пока возвращаем тестовые данные
    return test_points

@app.get("/wifi-points/{point_id}")
async def get_wifi_point(point_id: int):
    """
    Возвращает конкретную точку по ID
    """
    for point in test_points:
        if point.id == point_id:
            return point
    return {"Ошибка": "Точка не найдена"}

# Запускаем сервер
if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",  # Доступ с любого IP
        port=8000,       # Порт
        reload=True      # Автоперезагрузка при изменениях
    )