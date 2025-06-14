import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from app import db
from flask import jsonify


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

        cast['crew'] = listofcast['crew']


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
        # dirictor_details = {}
        
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




