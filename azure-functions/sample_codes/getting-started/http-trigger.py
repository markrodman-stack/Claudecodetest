# Azure Functions HTTP Trigger - Python v2 Programming Model
#
# Prerequisites:
#   pip install azure-functions
#
# Run locally: func start
# Test: GET http://localhost:7071/api/HttpExample?name=World
#       POST http://localhost:7071/api/HttpExample (body: {"name": "World"})

import azure.functions as func
import logging
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="HttpExample")
def http_example(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    # Read name from query string
    name = req.params.get("name")

    # Or read from request body
    if not name:
        try:
            req_body = req.get_json()
            name = req_body.get("name")
        except ValueError:
            pass

    if name:
        return func.HttpResponse(
            f"Hello, {name}!",
            status_code=200
        )
    else:
        return func.HttpResponse(
            "Pass a name in the query string or request body.",
            status_code=200
        )
