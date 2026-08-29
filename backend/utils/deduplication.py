import imagehash
from PIL import Image
import io

def generate_phash(image_bytes: bytes) -> str:
    """
    Generate a perceptual hash (pHash) from image bytes.
    """
    image = Image.open(io.BytesIO(image_bytes))
    hash_val = imagehash.phash(image)
    return str(hash_val)

def is_duplicate(new_hash_str: str, existing_hashes: list[str], threshold: int = 10):
    """
    Checks if a new hash is a duplicate of any existing hashes based on Hamming distance.
    threshold: The maximum Hamming distance to be considered a duplicate. Default is 10.
    
    Returns: (is_duplicate: bool, duplicate_of: str or None)
    """
    new_hash = imagehash.hex_to_hash(new_hash_str)
    
    best_match = None
    min_distance = float('inf')
    
    for existing_hash_str in existing_hashes:
        existing_hash = imagehash.hex_to_hash(existing_hash_str)
        distance = new_hash - existing_hash
        
        if distance <= threshold and distance < min_distance:
            min_distance = distance
            best_match = existing_hash_str
            
    if best_match:
        return True, best_match
    return False, None
