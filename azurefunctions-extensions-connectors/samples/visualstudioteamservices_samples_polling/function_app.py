#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle Azure DevOps polling callbacks using generated SDK item models."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.visualstudioteamservices as devops

app = func.FunctionApp()


@app.connector_trigger(arg_name="builds")
def devops_build_completed_single(builds: List[devops.BuildResult]) -> None:
    """Handle OnBuildCompleted with split-on enabled; the binding returns a list."""
    logging.info("Received %d completed Azure DevOps builds.", len(builds))


@app.connector_trigger(arg_name="builds")
def devops_build_completed_batch(builds: List[devops.BuildResult]) -> None:
    """Handle OnBuildCompleted with split-on disabled."""
    logging.info("Received a batch of %d completed Azure DevOps builds.", len(builds))


@app.connector_trigger(arg_name="pushes")
def devops_git_push(pushes: List[devops.GitPush]) -> None:
    """Handle OnGitPush with typed repositories, identities, and ref updates."""
    logging.info("Received %d Azure DevOps Git pushes.", len(pushes))


@app.connector_trigger(arg_name="pull_requests")
def devops_pull_request_created(pull_requests: List[devops.GitPullRequest]) -> None:
    """Handle OnGitPullCreated with typed reviewer and option models."""
    logging.info("Received %d created Azure DevOps pull requests.", len(pull_requests))


@app.connector_trigger(arg_name="pull_requests")
def devops_pull_request_closed(pull_requests: List[devops.GitPullRequest]) -> None:
    """Handle OnGitPullClosed using the same SDK pull-request item type."""
    logging.info("Received %d closed Azure DevOps pull requests.", len(pull_requests))


@app.connector_trigger(arg_name="changesets")
def devops_tfvc_check_in(changesets: List[devops.TfvcChangeset]) -> None:
    """Handle OnTfvcCheckIn with SDK changesets, not Git commit objects."""
    logging.info("Received %d Azure DevOps TFVC changesets.", len(changesets))


@app.connector_trigger(arg_name="work_items")
def devops_work_item_assigned(work_items: List[devops.TriggerWorkItemResponse]) -> None:
    """Handle OnWorkItemAssignedV2 without guessing custom field types."""
    logging.info("Received %d assigned Azure DevOps work items.", len(work_items))
    for item in work_items:
        logging.info("Azure DevOps work-item field count: %d.", len(item.fields or {}))


@app.connector_trigger(arg_name="work_items")
def devops_work_item_closed(work_items: List[devops.TriggerWorkItemResponse]) -> None:
    """Handle OnWorkItemClosedV2, preserving dotted field names in item.fields."""
    logging.info("Received %d closed Azure DevOps work items.", len(work_items))


@app.connector_trigger(arg_name="work_items")
def devops_work_item_created(work_items: List[devops.TriggerWorkItemResponse]) -> None:
    """Handle OnWorkItemCreatedV2 with raw custom field values."""
    logging.info("Received %d created Azure DevOps work items.", len(work_items))


@app.connector_trigger(arg_name="work_items")
def devops_work_item_updated(work_items: List[devops.TriggerWorkItemResponse]) -> None:
    """Handle OnWorkItemUpdatedV2 with SDK id, rev, url, and fields properties."""
    logging.info("Received %d updated Azure DevOps work items.", len(work_items))
