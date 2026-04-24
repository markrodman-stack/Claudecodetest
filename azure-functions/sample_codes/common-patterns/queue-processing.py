# Azure Functions Queue Trigger with Output Binding - Python v2
#
# Reads messages from an input queue, processes them,
# and writes results to an output queue.
#
# Required app setting in local.settings.json:
#   "STORAGE_CONNECTION": "<your-storage-connection-string>"
#   (or "UseDevelopmentStorage=true" for local Azurite)

import json
import logging

import azure.functions as func

app = func.FunctionApp()


@app.queue_trigger(
    arg_name="inputmsg",
    queue_name="input-queue",
    connection="STORAGE_CONNECTION",
)
@app.queue_output(
    arg_name="outputmsg",
    queue_name="output-queue",
    connection="STORAGE_CONNECTION",
)
def process_queue_message(
    inputmsg: func.QueueMessage,
    outputmsg: func.Out[str],
) -> None:
    # Read the incoming message
    message_body = inputmsg.get_body().decode("utf-8")
    logging.info(f"Processing queue message: {message_body}")

    try:
        payload = json.loads(message_body)

        # Process the message (your business logic here)
        result = {
            "original_id": payload.get("id"),
            "status": "processed",
            "result": f"Processed: {payload.get('data', 'no data')}",
        }

        # Write to output queue
        outputmsg.set(json.dumps(result))
        logging.info(f"Message processed successfully: {result}")

    except Exception as e:
        logging.error(f"Error processing message: {e}")
        raise  # Re-raise to trigger retry policy
