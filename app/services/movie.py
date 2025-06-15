import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from app import db
from flask import g, jsonify
from pymongo import UpdateOne
from bson import ObjectId


def get_signed_url(filename):
    try:
        # Azure Blob Storage config
        connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = "images"
        blob_name = filename  # file in blob storage

        # Initialize client
        blob_service_client = BlobServiceClient.from_connection_string(
            connect_str)

        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=15)
        )

        # Final signed URL
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

        return {"signed_url": blob_url}

    except Exception as e:
        return {"error": str(e)}


def get_castdetails(movie_id, user_id):
    try:
        listofcast = db.credits.find_one(
            {"id" : movie_id}
        ) 
        cast = {}
        cast['cast'] = listofcast['cast'] 
        user_details = db.user_details.find_one({"user_id": user_id})
        liked_actor_ids = set(user_details.get("actor_ids", [])) if user_details else set()
        print(liked_actor_ids)
        for c in cast['cast']:
            if c.get('id'):
                c['profile_url'] = get_signed_url(f"tmdb_profile_photos/{c['id']}.jpg").get('signed_url')
                c["is_liked"] = c['id'] in liked_actor_ids
        return cast
    except TypeError:
        return {"error": "Movie Not Found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500


def get_crewdetails(movie_id):
    try:
        listofcast = db.credits.find_one(
            {"id": movie_id}
        )
        targetjobs = {"Executive Producer", "Original Music Composer", "Director"}
        crew = [] 
        for c in listofcast.get('crew', []):
            job = c.get('job')
            if job in targetjobs:
                crew.append(c)
                c['profile_url'] = get_signed_url(f"tmdb_profile_photos/{c['id']}.jpg").get('signed_url')
        return crew
    except TypeError:
        return {"error": "Movie Not Found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500
    

def store_in_vector_db(data):
    updated_doc_count = 0
    operations = []

    for movie in data:
        operations.append(UpdateOne(
            {"_id": ObjectId(movie["_id"])},
            {"$set": {"embedding": movie["embedding"]}}
        ))
    if operations:
        res = db.movies_metadata.bulk_write(operations)
        updated_doc_count = res.modified_count

    return {"message": "Movies stored in vector database successfully", "updated_doc_count": updated_doc_count}

def get_movie_embedding(movie_id):
    movie = db.movies_metadata.find_one({"id": movie_id})
    return movie["embedding"]

def get_similar_movies(movie_id, limit=5):
    """
    Returns the top N most similar movies to the given movie_id based on vector similarity.
    """

    # Fetch the movie and its embedding
    movie = db.movies_metadata.find_one({"id": movie_id})
    if not movie or "embedding" not in movie:
        return {"error": "Movie or embedding not found"}, 404

    embedding = movie["embedding"]

    # Perform vector search in MongoDB
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": embedding,
                "numCandidates": 50,
                "limit": limit + 1  # +1 in case the movie itself is included
            }
        }
    ]
    results = list(db.movies_metadata.aggregate(pipeline))

    # Exclude the current movie from results
    filtered = [m for m in results if m.get("id") != movie_id]
    top_n = filtered[:limit]

    # Return relevant details
    res = []
    for m in top_n:
        m.pop("embedding", None)  # Remove embedding from output for brevity
        res.append(m.get("id"))
    return get_movies_by_ids(res, True, g.user_id)

def get_movies_by_ids(movie_ids, skinny=True, user_id=None):
    """
    Fetch movies by a list of movie_ids, enrich with poster_url, is_watchlisted, and optionally castdata and crewdetails.
    Args:
        movie_ids (List[int]): List of movie IDs to fetch.
        skinny (bool): If False, include cast and crew details.
        user_id (str or int, optional): User ID for watchlist and liked actors info.
    Returns:
        List[dict]: List of enriched movie dicts.
    """
    
    # Fetch user-related info if user_id is provided
    watchlisted_ids = set()
    liked_actor_ids = set()
    if user_id:
        watchlist = db.watchlists.find_one({"user_id": user_id})
        watchlisted_ids = set(watchlist.get("movie_ids", [])) if watchlist else set()
        user_details = db.user_details.find_one({"user_id": user_id})
        liked_actor_ids = set(user_details.get("actor_ids", [])) if user_details else set()
    
    # Batch fetch movies and credits
    movies_cursor = db.movies_metadata.find({"id": {"$in": movie_ids}})
    credits = db.credits.find({"id": {"$in": movie_ids}})
    credits_map = {c["id"]: c for c in credits}
    
    movies = []
    for movie in movies_cursor:
        movie["_id"] = str(movie["_id"])
        movie_id = movie.get("id")
        poster = get_signed_url(f"posters/{movie_id}.jpg")
        movie["poster_url"] = poster["signed_url"]
        movie["is_watchlisted"] = movie_id in watchlisted_ids

        movie.pop("embedding", None)
        
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
    return movies

def semantic_search_movies(query, limit=3, user_id=None):
    """
    Perform semantic search for movies based on a user query.
    Args:
        query (str): The user's search query.
        limit (int): Number of top results to return.
        user_id (str or int, optional): User ID for enrichment.
    Returns:
        List[dict]: List of enriched movie dicts.
    """
    from app.services.embedding import EmbeddingService
    embedder = EmbeddingService()
    query_embedding = embedder.get_embedding(query)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 50,
                "limit": limit
            }
        }
    ]
    results = list(db.movies_metadata.aggregate(pipeline))
    movie_ids = [m.get("id") for m in results]
    return get_movies_by_ids(movie_ids, skinny=True, user_id=user_id)