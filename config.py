# Performance configuration
import os

class Config:
    # Flask optimizations
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # File processing limits
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Threading
    THREADED = True
    
    # JSON optimizations
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False