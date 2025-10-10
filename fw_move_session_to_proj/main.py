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
    destination_id = gtk_context.destination["id"] # utility gear
    destination = fw.get(destination_id)
    project_id = destination.parents["project"] # analysis gear
    project = fw.get(project_id)

    # get the input file
    CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)

    destination_project = config['config']['destination_project']
    matching_session_tags = config['config']['matching_session_tags']

    # ============== Update project.info for Ambra studies ==========
    # first, update the list of existing StudyInstanceUIDs if this is the Ambra project
    if project.label == 'd3b_landing_zone':
        log.info(f'Logging StudyInstanceUID for all sessions in source project to project.info.received_study_uids')
        # get existing list of study UIDs
        project = project.reload()
        existing_uid_list = project.info.get('received_study_uids')
        for session in project.sessions.iter():
            session = session.reload()
            if not all(tag in session.tags for tag in matching_session_tags):
                log.info(f'  Session {session.label} does not match tags {matching_session_tags}. Skipping.')
            # get the StudyInstanceUID from the ambra_metadata
            else:
                try:
                    this_session_uid =  session.info['ambra_metadata']['study_uid']
                    if this_session_uid not in existing_uid_list:
                            existing_uid_list.append(this_session_uid)
                    else:
                        log.warning(f'  StudyInstanceUID {this_session_uid} already exists in source project info. Skipping.')
                except:
                    log.warning(f'  Session {session.label} does not have a StudyInstanceUID in ambra_metadata/study_uid. Skipping.')
                # update the source project info
                try:
                    project.update({'info': {'received_study_uids':existing_uid_list}})
                except:
                    try:
                        project.update({'info': {'received_study_uids':existing_uid_list}})
                    except:
                        try:
                            project.update({'info': {'received_study_uids':existing_uid_list}})
                        except:
                            log.error(f'  Could not add StudyInstanceUID to project.info due to WriteConflict error')

    # ============== Move sessions ==================================
    project = project.reload()
    existing_uid_list = project.info.get('received_study_uids')
    n_sessions = project.stats.number_of.sessions
    count = 0
    # iterate through sessions in the current project
    for session in project.sessions.iter():
        session = session.reload()
        count += 1
        if not session.tags:
            log.warning(f'{count}/{n_sessions} Session {session.label} has no tags. Skipping.')
            return
        # check if session matches the tags
        if not all(tag in session.tags for tag in matching_session_tags):
            log.info(f'{count}/{n_sessions} Session {session.label} does not match tags {matching_session_tags}. Skipping.')
            return
        else:
            this_session_uid =  session.info['ambra_metadata']['study_uid']
            if (project.label == 'd3b_landing_zone') & (this_session_uid not in existing_uid_list):
                # avoid moving sessions that haven't been logged in the source project info for d3b_landing_zone
                log.info(f'{count}/{n_sessions} Session {session.label} not logged in project.info.received_study_uids. Skipping.')
            else:
                log.info(f'{count}/{n_sessions} Session {session.label} matches tags {matching_session_tags}. Moving to project {destination_project}.')
                # get the project
                dest_project = fw.projects.find_first(f'label={destination_project}')
                dest_project = dest_project.reload()
                dest_project_id = dest_project.id

                try:
                    session.update({'project': dest_project_id})
                except:
                    # if couldn't update using project ID then see if 
                    # it's a duplicate session (already exists in destination)
                    # if not a duplicate, then move it using the destination subject ID instead
                    dest_sub = fw.lookup(f'{dest_project.parents.group}/{dest_project.label}/{session.subject.label}')
                    dest_sub = dest_sub.reload()
                    dest_ses_list=[]
                    for dest_ses in dest_sub.sessions.iter():
                        dest_ses_list.append(dest_ses.label)
                    if session.label not in dest_ses_list:
                        # if the session is not already in the destination subject, move it
                        session.update({'subject':dest_sub.id})
                    else:
                        log.warning(f'{count}/{n_sessions} Session {session.label} already exists in project {destination_project} under subject {dest_sub.label}. Checking acquisitions.')
                        dest_ses = fw.lookup(f'{dest_project.parents.group}/{dest_project.label}/{session.subject.label}/{session.label}')
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
                                dest_acq = fw.lookup(f'{dest_project.parents.group}/{dest_project.label}/{session.subject.label}/{session.label}/{acq.label}')
                                move = 0
                                for file in acq.files:
                                    if [acq.label, file.name] not in file_list:
                                        log.info(f'{count}/{n_sessions} Moving file {acq.label}/{file.name} to destination project')
                                        move = 1
                                    else:
                                        log.info(f'{count}/{n_sessions} Deleting duplicate file {acq.label}/{file.name}')
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
