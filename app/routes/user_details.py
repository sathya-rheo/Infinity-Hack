from app import db
from flask import Blueprint, request, jsonify, send_file, g
from app.utils.helper import paginate, get_genre_list
from app.services.watchlist import paginate_list
from app.services.movie import get_signed_url
import math
from app.services.auth import require_auth
from app.services.movie import fetch_movies


user_details_collection = db.user_details


user_bp = Blueprint("user", __name__)

@user_bp.route("/add_liked_actor", methods=["POST"])
@require_auth
def create_or_update_liked_actors():
    data = request.json
    user_id = g.user_id

    actor_id = int(data.get("actor_id"))
    if not user_id or not actor_id:
        return jsonify({"error": "user_id and actor_id are required"}), 400

    user_details = user_details_collection.find_one({"user_id": user_id})
    if user_details:
        # Use .get with default empty list to avoid KeyError
        actor_ids = user_details.get("actor_ids", [])

        if actor_id not in actor_ids:
            actor_ids.append(actor_id)
            user_details_collection.update_one(
                {"user_id": user_id},
                {"$set": {"actor_ids": actor_ids}}
            )
            return jsonify({"message": "Actor added to liked list"}), 200
        else:
            return jsonify({"message": "Actor already liked"}), 400
    else:
        # Create new document with actor_ids list
        user_details_collection.insert_one({
            "user_id": user_id,
            "actor_ids": [actor_id]
        })
        return jsonify({"message": "Liked actor list created"}), 200


@user_bp.route("/remove_liked_actor", methods=["DELETE"])
@require_auth
def remove_liked_actor():
    user_id = g.user_id
    actor_id = request.args.get("actor_id")

    if not actor_id:
        return jsonify({"error": "actor_id is required"}), 400

    result = user_details_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"actor_ids": int(actor_id)}}
    )

    if result.modified_count == 0:
        return jsonify({"message": "Actor was not in Liked Actors or already removed"}), 200

    return jsonify({"message": "Actor removed from Liked Actors"}), 200


@user_bp.route("/add_liked_movie", methods=["POST"])
@require_auth
def create_or_update_liked_movie():
    data = request.json
    user_id = g.user_id

    movie_id = data.get("movie_id")
    preference = data.get("preference", "like")  # Default to 'like' if not given

    if not user_id or not movie_id:
        return jsonify({"error": "user_id and movie_id are required"}), 400

    movie_id = str(movie_id)
    new_entry = {"movie_id": movie_id, "preference": preference}

    user_details = user_details_collection.find_one({"user_id": user_id})
    if user_details:
        movie_entries = user_details.get("movie_ids", [])

        # Check if movie_id already exists
        if any(entry.get("movie_id") == movie_id for entry in movie_entries):
            return jsonify({"message": "Movie already liked"}), 400

        movie_entries.append(new_entry)

        user_details_collection.update_one(
            {"user_id": user_id},
            {"$set": {"movie_ids": movie_entries}}
        )
        
    else:
        user_details_collection.insert_one({
            "user_id": user_id,
            "movie_ids": [new_entry]
        })
    
    return jsonify({"message": "Movie added to preferred list"}), 201


@user_bp.route("/remove_liked_movie", methods=["DELETE"])
@require_auth
def remove_liked_movie():
    user_id = g.user_id
    movie_id = request.args.get("movie_id")

    if not movie_id:
        return jsonify({"error": "movie_id is required"}), 400

    result = user_details_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"movie_ids": {"movie_id": str(movie_id)}}}
    )

    if result.modified_count == 0:
        return jsonify({"message": "Movie was not in preferred movies or already removed"}), 400

    return jsonify({"message": "Movie removed from preferred movies"}), 200

@user_bp.route("/add_liked_genre", methods=["POST"])
@require_auth
def create_or_update_liked_genres():
    data = request.json
    user_id = g.user_id

    genre_id = int(data.get("genre_id"))
    if not user_id or not genre_id:
        return jsonify({"error": "user_id and genre_id are required"}), 400

    user_details = user_details_collection.find_one({"user_id": user_id})
    if user_details:
        # Use .get with default empty list to avoid KeyError
        genre_ids = user_details.get("genre_ids", [])

        if genre_id not in genre_ids:
            genre_ids.append(genre_id)
            user_details_collection.update_one(
                {"user_id": user_id},
                {"$set": {"genre_ids": genre_ids}}
            )
            return jsonify({"message": "Genre added to liked list"}), 200
        else:
            return jsonify({"message": "Genre already liked"}), 400
    else:
        # Create new document with actor_ids list
        user_details_collection.insert_one({
            "user_id": user_id,
            "genre_ids": [genre_id]
        })
        return jsonify({"message": "Liked genre list created"}), 200


@user_bp.route("/remove_liked_genre", methods=["DELETE"])
@require_auth
def remove_liked_genre():
    user_id = g.user_id
    genre_id = request.args.get("genre_id")

    if not genre_id:
        return jsonify({"error": "genre_id is required"}), 400

    result = user_details_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"genre_ids": int(genre_id)}}
    )

    if result.modified_count == 0:
        return jsonify({"message": "Genre was not in Liked Genres or already removed"}), 200

    return jsonify({"message": "Genre removed from Liked Genres"}), 200



@user_bp.route("/user_preference", methods=["GET"])
@require_auth
def get_user_preferences():
    user_id = g.user_id

    # Get user detail document
    user_details = db.user_details.find_one({"user_id": user_id}) or {}
    watchlist = db.watchlists.find_one({"user_id": user_id}) or {}

    liked_movie_entries = user_details.get("movie_ids", [])
    watchlisted_ids = watchlist.get("movie_ids", [])

    liked_ids = []
    watched_ids = []

    liked_lookup = {}

    for entry in liked_movie_entries:
        movie_id = entry.get("movie_id")
        preference = entry.get("preference")
        if movie_id:
            watched_ids.append(movie_id)
            if preference == "Like":
                liked_ids.append(movie_id)
            
    return jsonify({
        "liked_movies": fetch_movies(liked_ids),
        "watched_movies": fetch_movies(watched_ids),
        "watchlisted_movies": fetch_movies(watchlisted_ids)
    }), 200
