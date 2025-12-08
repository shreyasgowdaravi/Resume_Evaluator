import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

try:
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    # Check if container exists
    container_client = blob_service_client.get_container_client(container_name)
    
    print(f"Container '{container_name}' exists: {container_client.exists()}")
    
    # List recent blobs
    blobs = list(container_client.list_blobs())[:10]
    print(f"\nRecent blobs ({len(blobs)}):")
    for blob in blobs:
        print(f"  - {blob.name} ({blob.size} bytes)")
        
    if len(blobs) == 0:
        print("  No blobs found in container")
        
except Exception as e:
    print(f"Error: {e}")