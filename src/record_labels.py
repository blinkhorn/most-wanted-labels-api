from typing import Dict
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler.api_gateway import Router

logger = Logger(child=True)
router = Router()


@router.get("/")
def get_record_labels() -> Dict:
    return {"items": "record_labels"}

@router.get("/<id>")
def get_record_label(id: str) -> Dict:
    logger.info(f"Fetching record label with id {id}")
    return {"details": id}