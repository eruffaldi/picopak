# picopak
Personal Package Based Backup with Sources, simpler than git-annex but for my needs


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