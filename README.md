# picopak

Picopak is an archival software aimed at storing task/project archives and tracking their locations across different data sources. Picopak allows for detached/distributed archival using git as a metadata storage mechanism.

Concepts:
* repository: the location in which metatada is stored, based on git
* package: a unit of management of picopak
* source: a location that stores packages (e.g. external disk)



Personal Package Based Backup with Sources, simpler than git-annex but for my needs

TODO support rename of package folders <-> 
TODO git --git-dir=.git --work-tree=.

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
