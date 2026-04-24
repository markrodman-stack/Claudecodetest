# Azure Functions Timer Trigger - Python v2 Programming Model
#
# Runs on a schedule defined by a cron expression.
# This example runs every 5 minutes.
#
# Cron format: {second} {minute} {hour} {day} {month} {day-of-week}
# Examples:
#   "0 */5 * * * *"    - every 5 minutes
#   "0 0 * * * *"      - every hour
#   "0 0 9 * * *"      - daily at 9 AM
#   "0 30 9 * * 1-5"   - weekdays at 9:30 AM

import datetime
import logging

import azure.functions as func

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 */5 * * * *",
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True,
)
def timer_function(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.warning("The timer is running late!")

    logging.info(f"Python timer trigger function executed at: {utc_timestamp}")

    # Add your scheduled task logic here, e.g.:
    # - Data cleanup
    # - Report generation
    # - Cache refresh
    # - Health checks
