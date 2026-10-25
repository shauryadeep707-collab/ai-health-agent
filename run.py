import sys
from backend.config import Config
from backend.app import app

if __name__ == "__main__":
    print("=" * 64)
    print(f" AI Health Agent running on http://127.0.0.1:{Config.PORT}")
    print(f" Database: {Config.DB_TYPE.upper()} (Supabase Cloud)")
    print(f" AI Provider: {Config.AI_PROVIDER.upper()}")
    print("=" * 64)
    app.run(host="127.0.0.1", port=Config.PORT, debug=Config.DEBUG)
