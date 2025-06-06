from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import ssl

load_dotenv()  

mongo_client = None
db = None

def create_app():
    app = Flask(__name__)

    MONGO_URI = os.getenv("MONGO_CLIENT")

    global mongo_client, db
    mongo_client = MongoClient(
        MONGO_URI,
        tls=True,  
        tlsAllowInvalidCertificates=True, 
        tlsCAFile=None  
    )
    db = mongo_client.movies 

    from .routes import register_blueprints
    register_blueprints(app)

    return app
