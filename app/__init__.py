from flask import Flask
from app.config import Config


def create_app(config_class=Config):
    application = Flask(__name__)
    application.config.from_object(config_class)

    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.views import views_bp

    application.register_blueprint(main_bp)
    application.register_blueprint(api_bp, url_prefix='/api')
    application.register_blueprint(views_bp)

    return application


# Create app instance for gunicorn (supports both `gunicorn app:app` and `gunicorn run:app`)
app = create_app()
