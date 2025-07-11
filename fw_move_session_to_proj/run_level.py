# based on https://github.com/flywheel-apps/bids-fmriprep/blob/main/utils/bids/run_level.py

#!/usr/bin/env python3
"""Determine level at which the gear is running."""

import logging

# from flywheel import ApiException
import flywheel
fw_context = flywheel.GearContext()
fw = fw_context.client

log = logging.getLogger(__name__)


def get_analysis_run_level_and_hierarchy(gtk_context_client, destination_id):
    """Determine the level at which a job is running, given a destination
    Args:
        fw (gear_toolkit.GearToolkitContext.client): flywheel client
        destination_id (id): id of the destination of the gear
    Returns:
        hierarchy (dict): containing the run_level and labels for the
            run_label, group, project, subject, session, and
            acquisition.
    """

    hierarchy = {
        "group": None,
        "project_label": None,
        "subject_label": None,
        "session_label": None,
        "acquisition_label":None
    }

    run_level = 'session'
    destination = gtk_context_client.get(destination_id)
    analysis_id = fw_context.destination['id']

    # print(destination)
    if destination.container_type == run_level:

        hierarchy["group"] = destination.parents["group"]

        for level in ["project", "subject", "session"]:
            if level == run_level:
                analysis_container = fw.get(analysis_id)
                # print(analysis_container)
                # container = gtk_context_client.get(analysis_container.parent['id'])
                hierarchy[f"{level}_label"] = analysis_container.label # if gear run at session level, this is the session label
            elif destination.parents[level]:
                container = gtk_context_client.get(destination.parents[level])
                hierarchy[f"{level}_label"] = container.label
    else:
        log.error("The destination_id must reference a valid session container.")

    log.info(f"Gear run level and hierarchy labels: {hierarchy}")
    return hierarchy
