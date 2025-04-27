from flask import Flask
from flask_pymongo import PyMongo
from .config import Config
from .logger import setup_logging

mongo = PyMongo()
def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    mongo.init_app(app)
    setup_logging(app, mongo)
    from .routes import main
    app.register_blueprint(main)

    return app
