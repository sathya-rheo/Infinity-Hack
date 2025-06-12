
from datetime import datetime, timedelta
from app import db
from flask import Blueprint, request, jsonify, send_file
import math
import ast
from app.services.movie import get_signed_url
from gridfs import GridFS

movies_collection = db.movies_metadata


fs = GridFS(db)
movie_bp = Blueprint("movie", __name__)

@movie_bp.route("/list", methods=["GET"])
def get_movies():
    keyword = request.args.get("keyword")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    sort_by = request.args.get("sort_by")

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
    elif sort_by:
        movies_cursor = db.movies_metadata.find().sort(sort_by, -1).skip(skip).limit(limit)
        total_count = db.movies_metadata.estimated_document_count()
    else:
        movies_cursor = db.movies_metadata.find().skip(skip).limit(limit)
        total_count = db.movies_metadata.estimated_document_count()

    movies = []
    for movie in movies_cursor:
        movie["_id"] = str(movie["_id"])
        movie_id = movie.get("id")
        poster  = get_signed_url(f"posters/{movie_id}.jpg")
        movie["poster_url"] = poster["signed_url"]
        movies.append(movie)

    return jsonify({
        "page": page,
        "total_pages": math.ceil(total_count / limit),
        "total_movies": total_count,
        "movies": movies
    }), 200


@movie_bp.route("/movie/<string:movie_id>", methods=["GET"])
def get_movie_details(movie_id):
    movie = db.movies_metadata.find_one({"id": movie_id})
    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    movie["_id"] = str(movie["_id"])

    ratings_cursor = db.ratings.find({"movieId": movie_id})
    ratings = [{"userId": r["userId"], "rating": r["rating"], "timestamp": r["timestamp"]} for r in ratings_cursor]

    average_rating = round(sum(each_rating["rating"] for each_rating in ratings) / len(ratings) if ratings else 0, 2)

    movie["ratings"] = average_rating
    poster = get_signed_url(f"posters/{movie_id}.jpg")
    movie["poster_url"] = poster["signed_url"]
        
    return jsonify({
        "movie": movie,
        "ratings": ratings
    }), 200



@movie_bp.route("/poster/<movie_id>", methods=["GET"])
def get_poster(movie_id):
    file = fs.find_one({"filename": str(movie_id)})
    if not file:
        return jsonify({"error": "Poster not found"}), 404
    return send_file(file, mimetype=file.content_type)

@movie_bp.route('/get-signed-url', methods=['POST'])
def get_signed_url_route():   
    data = request.json
    filename = data.get("filename")
    try:
        return jsonify(get_signed_url(filename))

    except Exception as e:
        return {"error": str(e)}, 500
