import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas



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
