
# from .auth_routes import auth_bp
from .movie_details import movie_bp
from .watchlist import watchlist_bp

def register_blueprints(app):
    app.register_blueprint(movie_bp, url_prefix='/movies')
    app.register_blueprint(watchlist_bp, url_prefix='/watchlist')
