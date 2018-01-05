# picopak

Picopak is an archival software aimed at storing task/project archives and tracking their locations across different data sources. Picopak allows for detached/distributed archival using git as a metadata storage mechanism.

Concepts:
* repository: the location in which metatada is stored, based on git
* package: a unit of management of picopak
* source: a location that stores packages (e.g. external disk, remote)
* snapshot: a snapshot of a given package located in a given source 

The key point of the system is the tracking of location of the different snapshots of a package across sources. The granularity is high (e.g. hunders of MB, or GBs) while for finer tracking other solutions do exist like git-annex. Deduplication of data in a source is not a requirement but it can be provided by a source backend.



# Usage

Start with:

	picopak init ~/.picopak

Add sources

	picopak source add MYPATH_ON_HDD name

Sync

	picopak sync

# Source Operations

List known source

	picopak source list

Rename source

	picopak source rename UUID_or_name newname

Remove source

	MANUALLY edit sources.yaml, remove folders

Show details about source TBD

	picopak source show UUID_or_name

	The content is:
	- last seen
	- packages contained

# Package Operations

List known packages

Add packages (found in source)

Remove package
	
	MANUALLY edit folders and source listing
