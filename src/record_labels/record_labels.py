import os
from decimal import Decimal

import boto3
import requests
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler.api_gateway import Router
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.environ["TABLE_NAME"]
# Normally store secrets in Secrets Manager, but this is a personal AWS account, I'm
# the only one with access, and I don't want to pay a monthly fee for Secrets
API_KEY = os.environ["API_KEY"]
API_SECRET = os.environ["API_SECRET"]

logger = Logger(child=True)
router = Router()
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


@router.post("/add-new")
def post_record_labels() -> list[dict]:
    json_payload = router.current_event.json_body
    headers = router.current_event.headers
    record_label_name = json_payload.get('name')
    user_id = headers.get("userId", "pblinkhorn")
    record_label_id = find_record_label_on_discogs(record_label_name)
    record_label_releases = retrieve_record_label_releases(record_label_id)
    formatted_releases_stats = format_releases_stats(record_label_releases)
    calculated_record_label_scores = calculate_record_label_scores(
        formatted_releases_stats)
    return store_record_label_scores(user_id,
                                     record_label_id, record_label_name, calculated_record_label_scores)


@router.get("/")
def get_record_labels() -> dict:
    headers = router.current_event.headers
    user_id = headers.get("userId", "pblinkhorn")
    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id)
    )
    return response.get('Items')


@router.get("/<record_label_id>")
def get_record_label(record_label_id: str) -> dict:
    logger.info(f"Fetching record label with id {record_label_id}")
    headers = router.current_event.headers
    user_id = headers.get("userId", "pblinkhorn")
    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id) & Key('record_label_id').eq(record_label_id)
    )
    return response.get('Items')


def find_record_label_on_discogs(record_label_name: str) -> str:
    url = f'https://api.discogs.com/database/search?q={record_label_name}&type=label&key={API_KEY}&secret={API_SECRET}'
    return requests.get(url).json().get('results')[0].get('id')


def retrieve_record_label_releases(record_label_id: str) -> list[dict]:
    url = f'https://api.discogs.com/labels/{record_label_id}/releases?page=1&per_page=50&sort=year&sort_order=desc&key={API_KEY}&secret={API_SECRET}'
    return requests.get(url).json().get('releases')


def format_releases_stats(record_label_releases: list[dict]) -> list[dict]:
    formatted_record_label_releases = [{str(release.get('title')): get_release_stats(
        str(release.get('id')), release.get('title'))} for release in record_label_releases]
    unique_record_label_release_titles = set()
    formatted_unique_record_label_releases = []
    for formatted_release in formatted_record_label_releases:
        for title in formatted_release.keys():
            if title not in unique_record_label_release_titles:
                unique_record_label_release_titles.add(title)
                formatted_unique_record_label_releases.append(
                    formatted_release)
            # TODO: add optimized logic to add the releases with the most wants and haves if there are duplicate titles
    return formatted_unique_record_label_releases


def get_release_stats(release_id: str, title: str) -> dict:
    url = f'https://api.discogs.com/releases/{release_id}?key={API_KEY}&secret={API_SECRET}'
    community_response = requests.get(url).json().get('community')
    return {'have_count': community_response.get('have'), 'want_count': community_response.get('want'), 'title': title, 'id': release_id}


def calculate_record_label_scores(formatted_releases_stats: list[dict]) -> dict:
    release_stats = [list(release_statistic.values())
                     for release_statistic in formatted_releases_stats]
    have_sum = 0
    want_sum = 0
    for release_statistic in release_stats:
        have_sum = have_sum + release_statistic[0]['have_count']
        want_sum = want_sum + release_statistic[0]['want_count']
    average_have = have_sum / len(release_stats)
    average_want = want_sum / len(release_stats)
    # weight average_have score greater than average_want score since more people have supported label
    overall_label_score = average_have * 5 + average_want
    return {'overall_label_score': overall_label_score, 'average_want': average_want, 'average_have': average_have}


def store_record_label_scores(user_id: str, record_label_id: str, record_label_name: str, calculated_record_label_scores: dict) -> dict:
    formatted_result_to_store = format_stored_result(
        user_id, record_label_id, record_label_name, calculated_record_label_scores)
    table.put_item(Item=formatted_result_to_store)
    return formatted_result_to_store


def format_stored_result(user_id: str, record_label_id: str, record_label_name: str, calculated_record_label_scores: dict) -> dict:
    return {
        'user_id': user_id,
        'record_label_id': f"{record_label_id}",
        'name': record_label_name,
        'overall_label_score': Decimal(f"{calculated_record_label_scores['overall_label_score']}"),
        'average_want': Decimal(f"{calculated_record_label_scores['average_want']}"),
        'average_have': Decimal(f"{calculated_record_label_scores['average_have']}")
    }
