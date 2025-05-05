🔧 Features
-----------
- ✅ Drop-in replacement for Redis/Memcached backends
- ☁️ Firestore-compatible (GCP-managed, serverless, global scale)
- 🧹 Built-in TTL auto-cleanup via `expires_at` field
- 🔐 No extra infrastructure needed on Google App Engine/Cloud Run
- 🧪 Fully compatible with Flask-Limiter ≥3.5+

📦 Installation
---------------
    pip install Flask-Limiter-Firestore

🚀 Usage
--------
    from flask import Flask, request
    from flask_limiter import Limiter
    from flask_limiter_firestore import FirestoreStorage

    def get_client_ip():
        xff = request.headers.get("X-Forwarded-For", "")
        return xff.split(",")[0].strip() if xff else request.remote_addr

    app = Flask(__name__)
    limiter = Limiter(
        app=app,
        key_func=get_client_ip,
        storage=FirestoreStorage(collection_name="rate_limits"),
        default_limits=["10 per minute"],
    )

🔐 Authentication
-----------------
If you're running locally, authenticate with:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

On GAE / Cloud Run / Cloud Functions: ADC is automatic.

✅ Example Route
----------------
    @app.route("/api/data")
    @limiter.limit("5 per minute")
    def data():
        return "Rate limited!"

🧹 Cleanup Policy
-----------------
Use a TTL index on the `expires_at` field in Firestore for auto-deletion.

🐛 Troubleshooting
------------------
- FirestoreStorage.incr() got unexpected keyword 'amount' → Upgrade Flask-Limiter ≥ 3.5
- Invalid document key → Avoid slashes in limiter keys
- 'wrap_exceptions' attribute missing → ensure base_exceptions property exists

🔗 Links
--------
- Flask-Limiter: https://flask-limiter.readthedocs.io
- Firestore: https://cloud.google.com/firestore
- PyPI: https://pypi.org/project/Flask-Limiter-Firestore

📄 License
----------
MIT License © 2025 Delivery Disruptor Inc.
