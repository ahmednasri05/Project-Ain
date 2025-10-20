from db.client import media

def create_media_document(media_document: dict):
    media.insert_one(media_document)
    

def read_media_by_id(media_id: str):
    return media.find_one({"media_id": media_id})

def update_media_paths(media_id: str, video_path: str = None, audio_path: str = None):
    update_fields = {}
    if video_path:
        update_fields["video_path"] = video_path
    if audio_path:
        update_fields["audio_path"] = audio_path
    if update_fields:
        media.update_one({"media_id": media_id}, {"$set": update_fields})

def delete_media_by_id(media_id: str):
    media.delete_one({"media_id": media_id})


