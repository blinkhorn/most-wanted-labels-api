import requests
import json
from requests.models import Response
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler.api_gateway import Router


from environment import secret, key

logger = Logger(child=True)
router = Router()

@router.post("/add-new")
def post_record_labels() -> list[dict]:
    json_payload = router.current_event.json_body
    record_label_name = json_payload.get('name')
    record_label_id = find_record_label_on_discogs(record_label_name)
    record_label_releases = retrieve_record_label_releases(record_label_id)
    # TODO: update dynamoDB with format_releases_stats(record_label_releases) for label
    return format_releases_stats(record_label_releases)

@router.get("/")
def get_record_labels() -> dict:
    return {"items": "record_labels"}

@router.get("/<id>")
def get_record_label(id: str) -> dict:
    logger.info(f"Fetching record label with id {id}")
    return {"details": id}

def find_record_label_on_discogs(record_label_name: str) -> str:
    url = f'https://api.discogs.com/database/search?q={record_label_name}&type=label&key={key}&secret={secret}' 
    return requests.get(url).json().get('results')[0].get('id')

def retrieve_record_label_releases(record_label_id: str) -> list[dict]:
    url = f'https://api.discogs.com/labels/{record_label_id}/releases?page=1&per_page=50&sort=year&sort_order=desc&key={key}&secret={secret}'
    return requests.get(url).json().get('releases')

def format_releases_stats(record_label_releases: list[dict]) -> list[dict]:
    return [{str(release.get('id')): get_release_stats(str(release.get('id')), release.get('title'))} for release in record_label_releases]

def get_release_stats(release_id: str, title: str) -> dict:
    url = f'https://api.discogs.com/releases/{release_id}?key={key}&secret={secret}'
    community_response = requests.get(url).json().get('community')
    return {'have_count': community_response.get('have'), 'want_count': community_response.get('want'), 'title': title}
