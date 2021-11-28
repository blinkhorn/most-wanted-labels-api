from typing import Dict
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import ApiGatewayResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

import record_labels.record_labels as record_labels

logger = Logger()
app = ApiGatewayResolver()

app.include_router(record_labels.router, prefix="/api/record-labels")

def lambda_handler(event: Dict, context: LambdaContext):
    return app.resolve(event, context)
