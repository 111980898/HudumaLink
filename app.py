"""HudumaLink entry point for local development and managed Preview."""
import os

from hudumalink import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 3000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
