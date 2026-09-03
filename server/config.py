# backend/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/gaming_house')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 86400  # 24 hours
    
    # Bcrypt
    BCRYPT_LOG_ROUNDS = 12
    
    # Server
    SERVER_PORT = int(os.getenv('SERVER_PORT', 8003))
    DISCOVERY_PORT = int(os.getenv('DISCOVERY_PORT', 9000))s