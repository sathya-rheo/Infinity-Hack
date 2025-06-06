from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()  # loads variables from .env into os.environ

mongo_client = None
db = None

def create_app():
    app = Flask(__name__)

    MONGO_URI = os.getenv("MONGO_CLIENT")

    global mongo_client, db
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client.movies  # your MongoDB database

    from .routes import register_blueprints
    register_blueprints(app)

    return app
