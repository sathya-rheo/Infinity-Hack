from flask import Flask

def create_app():
    app = Flask(__name__)

    from .routes import example_routes
    app.register_blueprint(example_routes.bp)

    return app
