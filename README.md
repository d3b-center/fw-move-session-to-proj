# Moves a session to a different Flywheel project

Finds sessions with a specific tag(s) and moves them to a specified project.

Will skip sessions without tags, sessions without all matching tags, and sessions with an equal session label in the destination project/subject container.

### Classification

_Category:_ Utility

_Gear Level:_

- [x] Project
- [ ] Subject
- [ ] Session
- [ ] Acquisition
- [ ] Analysis

## Usage

Runs at the project-level, iterates through all sessions.

This gear is intended to be run on a source project and will evaluate each session in that project against the configured tag list.

### Inputs

- `api-key` (required, base type `api-key`, read-only): Flywheel API key used to query and update projects, sessions, acquisitions, and files.

### Configuration

* __destination_project__ (string, default D3b_Ambra_raw_external_data): Destination project to route the session to.
* __matching_session_tags__ (array, default ["ambra_imported"]): Session tags to match. If multiple tags are provided, the session must match all of them.
* __debug__ (boolean, default False): Include debug statements in output.

## What This Gear Does

For each session in the source project, the gear:

1. Reloads the session and checks whether tags exist.
2. Verifies that all configured `matching_session_tags` are present.
3. Resolves the destination project by label.
4. Attempts to move the session directly to the destination project.
5. If direct project move fails, falls back to subject/session/acquisition-level reconciliation in the destination.

## Duplicate Handling

If a session with the same subject and session label already exists in the destination project:

- Missing acquisitions are moved into the existing destination session.
- For matching acquisitions, files are compared by acquisition label and file name.
- Files not already present in the destination are moved.
- Duplicate files in the source acquisition are deleted.
- Empty acquisitions are deleted after file moves.
- Empty source sessions are deleted after acquisition cleanup.

## Source Project Special Case

If the source project label is `d3b_landing_zone`, the gear also maintains `project.info.received_study_uids`.

Behavior in this case:

- For sessions matching the configured tags, it tries to read `session.info.ambra_metadata.study_uid`.
- New study UIDs are appended to `project.info.received_study_uids`.
- Sessions in `d3b_landing_zone` are only moved if their study UID is present in that project-level list.

## Prerequisites

- The gear must be run on a project container.
- The provided API key must have permissions to update sessions, acquisitions, files, and project info.
- The destination project must already exist.
- For duplicate fallback behavior, the destination subject is expected to exist when moving by subject ID.
- For `d3b_landing_zone` workflows, matching sessions should include `info.ambra_metadata.study_uid`.

## Output / Side Effects

This gear does not generate output files.

It mutates Flywheel containers by:

- Updating session project or subject membership
- Moving acquisitions between sessions
- Deleting duplicate acquisition files in the source
- Deleting empty acquisitions
- Deleting empty source sessions
- Updating `project.info.received_study_uids` for `d3b_landing_zone`

## Skip Conditions

Sessions are skipped when:

- The session has no tags.
- The session does not include all configured matching tags.
- The session lacks `ambra_metadata.study_uid` in the `d3b_landing_zone` path.
- The session is not yet recorded in `project.info.received_study_uids` for `d3b_landing_zone`.

## Repository Notes

- Manifest name: `fw-move-session-to-proj`
- Entry point: `python run.py`
- Current manifest version: `0.1.2`

### Limitations

- Destination project lookup is label-based and assumes a unique project label.
- Some fallback move behavior assumes the destination subject already exists.
- The `d3b_landing_zone` study UID bookkeeping is project-name-specific.
- Current control flow uses early `return` statements when some sessions are skipped, which may stop iteration earlier than intended.
