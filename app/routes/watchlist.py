
from app import db
from flask import Blueprint, request, jsonify, send_file
from app.utils.helper import paginate
from app.services.watchlist import paginate_list
from app.services.movie import get_signed_url
import math


watchlist_collection = db.watchlist


watchlist_bp = Blueprint("watchlist", __name__)

@watchlist_bp.route("/create", methods=["POST"])
def create_or_update_watchlist():
    data = request.json
    user_id = request.args.get("user_id")
    
    movie_id = data.get("movie_id")
    movie_id = str(movie_id)
    if not user_id or not movie_id:
        return jsonify({"error": "user_id and movie_id are required"}), 400

    watchlist = db.watchlists.find_one({"user_id": user_id})
    if watchlist:
        if movie_id not in watchlist["movie_ids"]:
            watchlist["movie_ids"].append(movie_id)
            new_movie_ids = watchlist["movie_ids"]
            db.watchlists.update_one(
                {"user_id": user_id},
                {"$set": {"movie_ids": new_movie_ids}}
            )
        else:
            return jsonify({"message": "Movie already in Watchlist"}), 400
    else:
        # Create new watchlist doc
        db.watchlists.insert_one({
            "user_id": user_id,
            "movie_ids": [movie_id]
        })

    return jsonify({"message": "Watchlist updated"}), 200


@watchlist_bp.route("/get", methods=["GET"])
def get_watchlist():
    user_id = request.args.get("user_id")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    watchlist = db.watchlists.find_one({"user_id": user_id})
    
    if not watchlist or not watchlist.get("movie_ids"):
        return jsonify({"message": "No movies in your watchlist"}), 404

    movie_ids = watchlist["movie_ids"]
    total_count = len(movie_ids)

    # Slice the movie_ids for pagination
    paginated_ids = paginate_list(movie_ids, page, limit)
    # Fetch movie metadata for paginated IDs
    movies_cursor = db.movies_metadata.find({"id": {"$in": paginated_ids}})
    movies = []
    for movie in movies_cursor:
        movie["_id"] = str(movie["_id"])
        movie_id = movie.get("id")
        poster = get_signed_url(f"posters/{movie_id}.jpg")
        movie["poster_url"] = poster["signed_url"]
        movies.append(movie)

    
    return jsonify({
        "page": page,
        "total_pages": math.ceil(total_count / limit),
        "total_movies": total_count,
        "movies": movies
    }), 200
