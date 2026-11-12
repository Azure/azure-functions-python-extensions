#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle Planner polling callbacks using generated SDK task items."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.planner as planner

app = func.FunctionApp()


@app.connector_trigger(arg_name="tasks")
def planner_new_task_single(tasks: List[planner.GetTaskResponseV2]) -> None:
    """Handle an OnNewTask_V3 split-on callback as a list of task items."""
    logging.info("Received %d new Planner tasks.", len(tasks))
    for task in tasks:
        logging.info("Planner task completion: '%s'.", task.percent_complete)


@app.connector_trigger(arg_name="tasks")
def planner_new_task_batch(tasks: List[planner.GetTaskResponseV2]) -> None:
    """Handle OnNewTask_V3 with split-on disabled."""
    logging.info("Received a batch of %d new Planner tasks.", len(tasks))
    for task in tasks:
        logging.info("Planner task completion: '%s'.", task.percent_complete)


@app.connector_trigger(arg_name="tasks")
def planner_task_completed(tasks: List[planner.GetTaskResponseV2]) -> None:
    """Handle OnCompleteTask_V3 without changing the SDK category model."""
    logging.info("Received %d completed Planner tasks.", len(tasks))
    for task in tasks:
        if task.applied_categories is not None:
            logging.info("Planner category 25 applied: '%s'.",
                         task.applied_categories.category25)


@app.connector_trigger(arg_name="tasks")
def planner_task_assigned_to_me(tasks: List[planner.GetTaskResponseV2]) -> None:
    """Handle OnTaskAssignedToMe_V2 with raw connector assignment entries."""
    logging.info("Received %d assigned Planner tasks.", len(tasks))
    for task in tasks:
        logging.info("Planner assignment count: '%s'.", len(task.assignments or []))
