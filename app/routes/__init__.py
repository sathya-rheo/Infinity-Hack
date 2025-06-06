
# from .auth_routes import auth_bp
from .movie_details import movie_bp

def register_blueprints(app):
    app.register_blueprint(movie_bp, url_prefix='/movies')
