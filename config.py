import os

class Config:
    # Database configuration
    MYSQL_HOST = 'localhost'  # If your MySQL server is on the same machine
    MYSQL_USER = 'PRAJNA N RAO'  # Your MySQL username
    MYSQL_PASSWORD = ''  # Replace with your password
    MYSQL_DB = 'Foodhub'  # Your database name
    MYSQL_CURSORCLASS = 'DictCursor'  # Optional, to return results as dictionaries

