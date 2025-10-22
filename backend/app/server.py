from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from typing import Optional
from contextlib import contextmanager 

app = FastAPI(title="WiFi Finder API", version="1.0.0")

# CORS для мобильного приложения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель данных для точки WiFi
class WiFiPoint(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    type: Optional[str] = None

class CreateWiFiPoint(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    type: Optional[str] = None

# Контекстный менеджер для БД (автоматическое закрытие соединения)
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="wifinder",
            user="postgres", 
            password="password",
            port="5432"
        )
        yield conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
    finally:
        if conn:
            conn.close()

def init_db():
    """Инициализация БД и заполнение тестовыми данными"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'wifi_points'
                );
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                # Создаем таблицу если не существует
                cur.execute("""
                    CREATE TABLE wifi_points (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        latitude DECIMAL(10, 8) NOT NULL,
                        longitude DECIMAL(11, 8) NOT NULL,
                        address TEXT,
                        type VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Создаем индекс для быстрого поиска
                cur.execute("""
                    CREATE INDEX idx_wifi_points_location 
                    ON wifi_points(latitude, longitude);
                """)
            
            test_points = [
                ("Кафе 'Кофеин'", 59.934280, 30.335098, "Невский пр., 123", "cafe"),
                ("Библиотека им. Маяковского", 59.931100, 30.342150, "наб. реки Фонтанки, 46", "library"),
                ("Макдональдс", 59.932500, 30.341000, "Лиговский пр., 274", "fast_food"),
                ("Парк им. Бабушкина", 59.940000, 30.330000, "ул. Бабушкина, 125", "park"),
                ("Станция метро Площадь Восстания", 59.931800, 30.360500, "пл. Восстания", "metro"),
            ]
            
            for point in test_points:
                cur.execute("""
                    INSERT INTO wifi_points (name, latitude, longitude, address, type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, point)
            
            conn.commit()
            cur.close()
            print("База данных успешно создана")
            
    except Exception as e:
        print(f"Не удалось создать базу данных: {e}")

@app.get("/")
async def root():
    return {"message": "G.NET API работает!", "status": "OK"}

@app.get("/health")
async def health_check():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    return {
        "status": "healthy", 
        "database": db_status,
        "version": "1.0.0"
    }

# ОСНОВНОЙ ЭНДПОИНТ ДЛЯ ПРИЛОЖЕНИЯ
@app.get("/wifi-points", response_model=List[WiFiPoint])
async def get_wifi_points(
    lat: float = 59.93, 
    lon: float = 30.34, 
    radius: float = 0.02  # ~2km radius
):
    """Возвращает точки WiFi из БД в радиусе..."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, name, latitude, longitude, address, type
                FROM wifi_points 
                WHERE ABS(latitude - %s) < %s AND ABS(longitude - %s) < %s
                ORDER BY id
            """, (lat, radius, lon, radius))
            
            points = []
            for row in cur.fetchall():
                points.append(WiFiPoint(
                    id=row[0], 
                    name=row[1], 
                    latitude=float(row[2]), 
                    longitude=float(row[3]), 
                    address=row[4], 
                    type=row[5]
                ))
            
            cur.close()
            return points

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")

@app.get("/wifi-points/{point_id}", response_model=WiFiPoint)
async def get_wifi_point(point_id: int):
    """Возвращает конкретную точку по ID"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, name, latitude, longitude, address, type
                FROM wifi_points 
                WHERE id = %s
            """, (point_id,))
            
            row = cur.fetchone()
            cur.close()
            
            if not row:
                raise HTTPException(status_code=404, detail="Точка не найдена")
            
            return WiFiPoint(
                id=row[0], 
                name=row[1], 
                latitude=float(row[2]), 
                longitude=float(row[3]), 
                address=row[4], 
                type=row[5]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")

@app.post("/wifi-points", response_model=WiFiPoint)
async def create_wifi_point(point: CreateWiFiPoint):
    """Создает новую точку WiFi"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
            INSERT INTO wifi_points (name, latitude, longitude, address, type)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, latitude, longitude, address, type
            """, (point.name, point.latitude, point.longitude, point.address, point.type))
            
            row = cur.fetchone()
            conn.commit()
            
            new_point = WiFiPoint(
                id=row[0], 
                name=row[1], 
                latitude=float(row[2]), 
                longitude=float(row[3]), 
                address=row[4], 
                type=row[5]
            )
            
            cur.close()
            return new_point
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось добавить точку: {str(e)}")

@app.delete("/wifi-points/{point_id}")
async def delete_wifi_point(point_id: int):
    """Удаляет точку WiFi по ID"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("DELETE FROM wifi_points WHERE id = %s", (point_id,))
            conn.commit()
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Точка не найдена")
            
            cur.close()
            return {"message": f"Точка {point_id} удалена"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось удалить точку: {str(e)}")

# Инициализируем БД при старте
@app.on_event("startup")
async def startup_event():
    print("Запуск API приложения")
    init_db()

# Запускаем сервер
if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

# # Создаем приложение FastAPI
# app = FastAPI(title="WiFi Finder API", version="1.0.0")

# # CORS для мобильного приложения
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Разрешаем запросы откуда угодно
#     allow_credentials=True,
#     allow_methods=["*"],   # Разрешаем все методы (GET, POST, etc.)
#     allow_headers=["*"],   # Разрешаем все заголовки
# )

# # Модель данных для точки WiFi
# class WiFiPoint(BaseModel):
#     id: int
#     name: str
#     latitude: float
#     longitude: float
#     address: str = None
#     type: str = None

# test_points = [
#     WiFiPoint(
#         id=1,
#         name="Кафе 'Кофеин'",
#         latitude=59.934280, 
#         longitude=30.335098,
#         address="Невский пр., 123",
#         type="cafe"
#     ),
#     WiFiPoint(
#         id=2,
#         name="Библиотека им. Маяковского",
#         latitude=59.931100,
#         longitude=30.342150,
#         address="наб. реки Фонтанки, 46", 
#         type="library"
#     ),
#     WiFiPoint(
#         id=3, 
#         name="Макдональдс", 
#         latitude=59.932500, 
#         longitude=30.341000, 
#         address="Лиговский пр., 274", 
#         type="fast_food"),
#     WiFiPoint(
#         id=4, 
#         name="Парк им. Бабушкина", 
#         latitude=59.940000, 
#         longitude=30.330000, 
#         address="ул. Бабушкина, 125", 
#         type="park"),
#     WiFiPoint(
#         id=5, 
#         name="Станция метро Площадь Восстания", 
#         latitude=59.931800, 
#         longitude=30.360500, 
#         address="пл. Восстания", 
#         type="metro"),
# ]

# def get_db_connection():
#     return psycopg2.connect(
#         host="localhost",
#         database="wifinder",
#         user="postgres", 
#         password="password",
#         port="5432"
#     )


# @app.get("/")
# async def root():
#     return {"message": "G.NET API работает!", "status": "OK"}

# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}

# # ОСНОВНОЙ ЭНДПОИНТ ДЛЯ ПРИЛОЖЕНИЯ
# @app.get("/wifi-points", response_model=List[WiFiPoint])
# async def get_wifi_points(lat: float = 59.93, lon: float = 30.34, radius: float = 2.0):
#     """Возвращает точки WiFi из БД в радиусе"""
#     conn = get_db_connection()
#     cur = conn.cursor()
    
#     cur.execute("""
#         SELECT id, name, latitude, longitude, address, type
#         FROM wifi_points 
#         WHERE ABS(latitude - %s) < %s AND ABS(longitude - %s) < %s
#     """, (lat, radius/100, lon, radius/100))
    
#     points = []
#     for row in cur.fetchall():
#         points.append(WiFiPoint(
#             id=row[0], name=row[1], latitude=float(row[2]), 
#             longitude=float(row[3]), address=row[4], type=row[5]
#         ))
    
#     cur.close()
#     conn.close()
#     return points

# @app.get("/wifi-points/{point_id}")
# async def get_wifi_point(point_id: int):
#     """
#     Возвращает конкретную точку по ID
#     """
#     for point in test_points:
#         if point.id == point_id:
#             return point
#     return {"Ошибка": "Точка не найдена"}

# def init_db():
#     conn = get_db_connection()
#     cur = conn.cursor()
    
#     # Вставляем тестовые данные
#     test_points = [
#         ("Кафе 'Кофеин'", 59.934280, 30.335098, "Невский пр., 123", "cafe"),
#         ("Библиотека им. Маяковского", 59.931100, 30.342150, "наб. реки Фонтанки, 46", "library"),
#         ("Макдональдс", 59.932500, 30.341000, "Лиговский пр., 274", "fast_food"),
#     ]
    
#     for point in test_points:
#         cur.execute("""
#             INSERT INTO wifi_points (name, latitude, longitude, address, type)
#             VALUES (%s, %s, %s, %s, %s)
#             ON CONFLICT DO NOTHING
#         """, point)
    
#     conn.commit()
#     cur.close()
#     conn.close()


# @app.on_event("startup")
# async def startup_event():
#     init_db()

# # Запускаем сервер
# if __name__ == "__main__":
#     uvicorn.run(
#         "server:app",
#         host="0.0.0.0",  # Доступ с любого IP
#         port=8000,       # Порт
#         reload=True      # Автоперезагрузка при изменениях
#     )