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
        try:
            source_project.update({'info': {'received_study_uids':existing_uid_list}})
        except:
            try:
                source_project.update({'info': {'received_study_uids':existing_uid_list}})
            except:
                try:
                    source_project.update({'info': {'received_study_uids':existing_uid_list}})
                except:
                    log.error(f'Could not add StudyInstanceUID to project.info due to WriteConflict error')

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
                # if the session is not already in the destination subject, move it
                session.update({'subject':dest_sub.id})
            else:
                log.warning(f'Session {session.label} already exists in project {destination_project} under subject {dest_sub.label}. Checking acquisitions.')
                dest_ses = fw.lookup(f'{project.parents.group}/{project.label}/{session.subject.label}/{session.label}')
                # initialize list of acquisitions and files in the destination
                acq_list=[]
                file_list = []
                for acq in dest_ses.acquisitions.iter():
                    for file in acq.files:
                        acq_list.append(acq.label)
                        file_list.append([acq.label, file.name])
                # if the whole acquisition isn't in the destination, move it
                for acq in session.acquisitions.iter():
                    if acq.label not in acq_list:
                        acq.update({'session':dest_ses.id})
                # if there is a matching acquisition, check if there is a duplicate file
                    else:
                        dest_acq = fw.lookup(f'{project.parents.group}/{project.label}/{session.subject.label}/{session.label}/{acq.label}')
                        for file in acq.files:
                            if [acq.label, file.name] not in file_list:
                                log.info(f'Moving file {acq.label}/{file.name} to destination project')
                                move = 1
                            else:
                                log.info(f'Deleting duplicate file {acq.label}/{file.name}')
                                fw.delete_acquisition_file(acq.id, file.name)
                        if move == 1:
                            acq.update({'session':dest_ses.id})
                        # delete empty acquisitions
                        acq=acq.reload()
                        if acq.files == []:
                            fw.delete_acquisition(acq.id)
            # delete empty session
            session=session.reload()
            acq_count=0
            for acq in session.acquisitions.iter():
                acq_count+=1
            if acq_count == 0:
                fw.delete_session(session.id)
