import logging
import datetime

class MongoLogHandler(logging.Handler):
    def __init__(self, mongo):
        super().__init__()
        self.mongo = mongo

    def emit(self, record):
        log_document = {
            "level": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.datetime.utcnow(),
            "pathname": record.pathname,
            "funcName": record.funcName,
        }
        self.mongo.db.logs.insert_one(log_document)


def setup_logging(app, mongo):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s : %(message)s"
    )
    file_handler = logging.FileHandler(app.config["LOG_FILE"])
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    mongo_handler = MongoLogHandler(mongo)
    mongo_handler.setLevel(logging.WARNING)
    logger.addHandler(mongo_handler)
    logger.info("Loglama Başladı - INFO ")
    logger.debug("Loglama Başladı - DEBUG ")
    logger.warning("Loglama Başladı - WARNING")
