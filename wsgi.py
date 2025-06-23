import os
from app import create_app


config_path = os.getenv("APP_CONFIG", "config.ProductionConfig")
app = create_app(config_path)

if __name__ == "__main__":
    debug_mode = config_path.endswith("DevelopmentConfig")
    app.run(debug=debug_mode)
