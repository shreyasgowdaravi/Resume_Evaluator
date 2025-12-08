#!/usr/bin/env python3
import os
from app import app

if __name__ == '__main__':
    # Production optimizations
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False,
        threaded=True,
        use_reloader=False
    )