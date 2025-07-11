# Moves a session to a different Flywheel project

Finds sessions with a specific tag(s) and moves them to a specified project.

Will skip sessions without tags, sessions without all matching tags, and sessions with an equal session label in the destination project/subject container.

### Classification

_Category:_ Utility

_Gear Level:_

- [ ] Project
- [ ] Subject
- [x] Session
- [ ] Acquisition
- [ ] Analysis

## Usage

Runs at the session-level

### Inputs

None

### Configuration

* __destination_project__ (string, default D3b_Ambra_raw_external_data): Destination project to route the session to.
* __matching_session_tags__ (array, default ["ambra_imported"]): Session tags to match. If multiple tags are provided, the session must match all of them.
* __debug__ (boolean, default False): Include debug statements in output.

### Limitations

Hard-coded Ambra credentials. 
