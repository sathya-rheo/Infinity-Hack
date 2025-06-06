from app import db
from flask import Blueprint, request, jsonify
import math
import ast

movies_collection = db.movies_metadata



movie_bp = Blueprint("movie", __name__)

@movie_bp.route("/list", methods=["GET"])
def get_movies():
    keyword = request.args.get("keyword")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    skip = (page - 1) * limit

    movie_ids = []

    if keyword:
        matched_keywords = db.keywords.find(
            {"keywords": {"$regex": keyword, "$options": "i"}},
            {"id": 1}
        )
        movie_ids = [doc["id"] for doc in matched_keywords]

        movies_cursor = db.movies_metadata.find(
            {"id": {"$in": movie_ids}}
        ).skip(skip).limit(limit)

        total_count = db.movies_metadata.count_documents({"id": {"$in": movie_ids}})
    else:
        movies_cursor = db.movies_metadata.find().skip(skip).limit(limit)
        total_count = db.movies_metadata.estimated_document_count()

    movies = []
    for movie in movies_cursor:
        movie["_id"] = str(movie["_id"])
        movies.append(movie)

    return jsonify({
        "page": page,
        "total_pages": math.ceil(total_count / limit),
        "total_movies": total_count,
        "movies": movies
    }), 200
