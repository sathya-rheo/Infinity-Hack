from datetime import datetime, timedelta
from app import db
from flask import Blueprint, request, jsonify, send_file, g
import math
import ast
from app.services.movie import get_signed_url,get_castdetails,get_crewdetails
from app.utils.helper import paginate, get_liked_genres
from gridfs import GridFS
from jose import jwt, JWTError
import requests
from app.services.auth import require_auth

movies_collection = db.movies_metadata


fs = GridFS(db)
movie_bp = Blueprint("movie", __name__)


@movie_bp.route("/api/protected")
@require_auth
def protected():
    return jsonify({
        "message": "Access granted",
        "user_id": g.user_id,
        "full_payload": g.user_payload
    })



@movie_bp.route("/list", methods=["GET"])
@require_auth
def get_movies():
    keyword = request.args.get("keyword")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    sort_by = request.args.get("sort_by")
    skinny = request.args.get("skinny", "true").lower() != "false"  # Default to True

    user_id = g.user_id
    movie_ids = []

    watchlist = db.watchlists.find_one({"user_id": user_id})
    watchlisted_ids = set(watchlist.get("movie_ids", [])) if watchlist else set()

    user_details = db.user_details.find_one({"user_id": user_id})
    liked_movies_data = user_details.get("movie_ids", []) if user_details else []
    
    liked_lookup = {
        str(entry["movie_id"]): entry["preference"]
        for entry in liked_movies_data
    }
    if keyword:
        # First check by title and then by keywords
        matched_title = db.movies_metadata.find(
            {"title": {"$regex": keyword, "$options": "i"}},
            {"id": 1}
        )
        movie_ids = [doc["id"] for doc in matched_title]

        if not movie_ids:
            matched_keywords = db.keywords.find(
                {"keywords.name": {"$regex": keyword, "$options": "i"}},
                {"id": 1}
            )
            movie_ids = [doc["id"] for doc in matched_keywords]

        movies_cursor = db.movies_metadata.find(
            {"id": {"$in": movie_ids}}
        )

        total_count = db.movies_metadata.count_documents({"id": {"$in": movie_ids}})
    elif sort_by:
        movies_cursor = db.movies_metadata.find().sort(sort_by, -1)
        total_count = db.movies_metadata.estimated_document_count()
    else:
        movies_cursor = db.movies_metadata.find()
        total_count = db.movies_metadata.estimated_document_count()
        
    movies_cursor, _ = paginate(movies_cursor, page, limit)
    
    movie_list = list(movies_cursor)
    movie_ids = [movie["id"] for movie in movie_list]

    # Batch fetch credits
    credits = db.credits.find({"id": {"$in": movie_ids}})
    credits_map = {c["id"]: c for c in credits}

    # Get liked actor ids once
    liked_actor_ids = set(user_details.get("actor_ids", [])) if user_details else set()
    liked_genre_ids = set(user_details.get("genre_ids", [])) if user_details else set()
    
    movies = []
    for movie in movie_list:
        movie = get_liked_genres(movie, liked_genre_ids)
        movie["_id"] = str(movie["_id"])
        movie_id = movie.get("id")
        poster = get_signed_url(f"posters/{movie_id}.jpg")
        movie["poster_url"] = poster["signed_url"]
        movie["is_watchlisted"] = movie_id in watchlisted_ids
        
        preference = liked_lookup.get(movie_id)
        movie["watched"] = preference is not None
        movie["preference"] = preference 
        
        if not skinny:
            credit = credits_map.get(movie_id)
            if credit:
                # Build castdata
                cast = credit.get("cast", [])
                for c in cast:
                    if c.get('id'):
                        c['profile_url'] = get_signed_url(f"tmdb_profile_photos/{c['id']}.jpg").get('signed_url')
                        c["is_liked"] = c['id'] in liked_actor_ids
                movie["castdata"] = cast

                # Build crewdetails
                targetjobs = {"Executive Producer", "Original Music Composer", "Director"}
                crew = []
                for c in credit.get('crew', []):
                    if c.get('job') in targetjobs:
                        c['profile_url'] = get_signed_url(f"tmdb_profile_photos/{c['id']}.jpg").get('signed_url')
                        crew.append(c)
                movie["crewdetails"] = crew
            else:
                movie["castdata"] = {}
                movie["crewdetails"] = []
        
        movies.append(movie)

    return jsonify({
        "page": page,
        "total_pages": math.ceil(total_count / limit),
        "total_movies": total_count,
        "movies": movies
    }), 200


@movie_bp.route("/movie/<string:movie_id>", methods=["GET"])
@require_auth
def get_movie_details(movie_id):
    user_id = g.user_id
    movie = db.movies_metadata.find_one({"id": movie_id})
    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    movie["_id"] = str(movie["_id"])
    
    watchlist = db.watchlists.find_one({"user_id": user_id})
    watchlisted_ids = set(watchlist["movie_ids"]) if watchlist and "movie_ids" in watchlist else set()
    
    user_details = db.user_details.find_one({"user_id": user_id})
    liked_movies_data = user_details.get("movie_ids", []) if user_details else []
    
    liked_genre_ids = set(user_details.get("genre_ids", [])) if user_details else set()
        
    
    liked_lookup = {
        str(entry["movie_id"]): entry["preference"]
        for entry in liked_movies_data
    }

    movie = get_liked_genres(movie, liked_genre_ids)
    ratings_cursor = db.ratings.find({"movieId": movie_id})
    ratings = [{"userId": r["userId"], "rating": r["rating"], "timestamp": r["timestamp"]} for r in ratings_cursor]

    average_rating = round(sum(each_rating["rating"] for each_rating in ratings) / len(ratings) if ratings else 0, 2)

    movie["ratings"] = average_rating
    poster = get_signed_url(f"posters/{movie_id}.jpg")
    movie["poster_url"] = poster["signed_url"]
    movie["is_watchlisted"] = movie_id in watchlisted_ids
    preference = liked_lookup.get(movie_id)
    movie["watched"] = preference is not None
    movie["preference"] = preference 
    
    castdata = get_castdetails(movie_id, user_id)
    crewdetails = get_crewdetails(movie_id)
    return jsonify({
        "movie": movie,
        "ratings": ratings,
        "castdata": castdata,
        "crewdetails": crewdetails
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



@movie_bp.route('/cast_details')
@require_auth
def castdetails():
    user_id = g.user_id
    movie_id = request.args.get("movie_id")
    return get_castdetails(movie_id, user_id)


@movie_bp.route('/keywords', methods=['POST'])
@require_auth
def get_keywords():
    data = request.json
    movie_ids = data.get("movie_ids")

    keywords = db.keywords.find({"id": {"$in": movie_ids}})

    keywords_list = []
    for keyword in keywords:
        movie_keywords = {}
        movie_keywords["id"] = keyword["id"]
        movie_keywords["keywords"] = ','.join([each_keyword["name"] for each_keyword in keyword["keywords"]])
        keywords_list.append(movie_keywords)

    return jsonify(keywords_list)



@movie_bp.route('/crewdetails')
def crewdetails():
    movie_id = request.args.get("movie_id")
    return get_crewdetails(movie_id)
