
from app import db
from flask import Blueprint, request, jsonify, send_file, g
from app.utils.helper import paginate, get_genre_list
from app.services.watchlist import paginate_list
from app.services.movie import get_signed_url
import math
from app.services.auth import require_auth


watchlist_collection = db.watchlist


watchlist_bp = Blueprint("watchlist", __name__)

@watchlist_bp.route("/create", methods=["POST"])
@require_auth
def create_or_update_watchlist():
    data = request.json
    user_id = g.user_id
    
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
@require_auth
def get_watchlist():
    user_id = g.user_id
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    search = request.args.get("search")
    year = request.args.get("year")  
    genre = request.args.get("genre")  

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    watchlist = db.watchlists.find_one({"user_id": user_id})
    if not watchlist or not watchlist.get("movie_ids"):
        return jsonify({"message": "No movies in your watchlist"}), 404

    movie_ids = watchlist["movie_ids"]

    # Base query
    query = {"id": {"$in": movie_ids}}

    if search:
        query["title"] = {"$regex": search, "$options": "i"}

    if genre:
        query["genres.name"] = {"$regex": genre, "$options": "i"} 

    if year:
        query["$expr"] = {
            "$eq": [
                {"$substr": ["$release_date", 0, 4]},
                str(year)
            ]
        }

    total_count = db.movies_metadata.count_documents(query)
    
    raw_cursor = db.movies_metadata.find(query).sort("title", 1)

    movies_cursor, _ = paginate(raw_cursor, page, limit)

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

@watchlist_bp.route("/remove", methods=["DELETE"])
@require_auth
def remove_from_watchlist():
    user_id = g.user_id
    movie_id = request.args.get("movie_id")

    if not movie_id:
        return jsonify({"error": "movie_id is required"}), 400

    result = db.watchlists.update_one(
        {"user_id": user_id},
        {"$pull": {"movie_ids": movie_id}}
    )

    if result.modified_count == 0:
        return jsonify({"message": "Movie was not in the watchlist or already removed"}), 200

    return jsonify({"message": "Movie removed from watchlist"}), 200



@watchlist_bp.route("/get_genre_list")
def get_list():
    return {"genre_list":get_genre_list()}
    