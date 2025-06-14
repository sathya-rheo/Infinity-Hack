from app import db
from flask import Blueprint, request, jsonify, send_file, g
from app.utils.helper import paginate, get_genre_list
from app.services.watchlist import paginate_list
from app.services.movie import get_signed_url
import math
from app.services.auth import require_auth


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
