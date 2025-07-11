import logging
import zipfile
import os
import shutil
import json

from fw_core_client import CoreClient
from flywheel_gear_toolkit import GearToolkitContext
import flywheel
from .run_level import get_analysis_run_level_and_hierarchy

log = logging.getLogger(__name__)

fw_context = flywheel.GearContext()
fw = fw_context.client

def run(client: CoreClient, gtk_context: GearToolkitContext):
    """Main entrypoint

    Args:
        client (CoreClient): Client to connect to API
        gtk_context (GearToolkitContext)
    """
    # get the Flywheel hierarchy for the run
    destination_id = gtk_context.destination["id"]
    session = fw.get(destination_id)
    session = session.reload()

    source_project_id = session.project

    # get the input file
    CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)

    destination_project = config['config']['destination_project']
    matching_session_tags = config['config']['matching_session_tags']

    if not session.tags:
        log.warning(f'Session {session.label} has no tags. Skipping.')
        return
    # check if session matches the tags
    if not all(tag in session.tags for tag in matching_session_tags):
        log.info(f'Session {session.label} does not match tags {matching_session_tags}. Skipping.')
        return
    else:
        log.info(f'Session {session.label} matches tags {matching_session_tags}. Moving to project {destination_project}.')
        # get the project
        project = fw.projects.find_first(f'label={destination_project}')
        project = project.reload()
        project_id = project.id

        try:
            session.update({'project': project_id})
        except:
            # if couldn't update using project ID then see if 
            # it's a duplicate session (already exists in destination)
            # if not a duplicate, then move it using the destination subject ID instead
            dest_sub = fw.lookup(f'{project.parents.group}/{project.label}/{session.subject.label}')
            dest_sub = dest_sub.reload()
            ses_list=[]
            for dest_ses in dest_sub.sessions.iter():
                ses_list.append(dest_ses.label)
            if session.label not in ses_list:
                session.update({'subject':dest_sub.id})
            else:
                log.warning(f'Session {session.label} already exists in project {destination_project} under subject {dest_sub.label}. Skipping.')
                return

    # if Ambra study, add to list of received StudyInstanceUIDs
    if project.label == 'D3b_Ambra_raw_external_data':
        log.info(f'Logging StudyInstanceUID in source project.')
        source_project = fw.get(source_project_id)
        source_project = source_project.reload()
        # get existing list
        existing_uid_list = source_project.info.get('received_study_uids')
        try:
            this_session_uid =  session.info['ambra_metadata']['study_uid']
            if this_session_uid not in existing_uid_list:
                    existing_uid_list.append(this_session_uid)
            else:
                log.warning(f'StudyInstanceUID {this_session_uid} already exists in source project info. Skipping.')
        except:
            log.warning(f'Session {session.label} does not have a StudyInstanceUID in ambra_metadata/study_uid. Skipping.')
        # update the source project info
        source_project.update({'info': {'received_study_uids':existing_uid_list}})
