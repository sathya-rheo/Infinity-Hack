from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()  

mongo_client = None
db = None

def create_app():
    app = Flask(__name__)

    CORS(app, origins=["https://frontend-jt19.onrender.com"])

    MONGO_URI = os.getenv("MONGO_CLIENT")

    global mongo_client, db
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client.movies 

    from .routes import register_blueprints
    register_blueprints(app)

    return app
