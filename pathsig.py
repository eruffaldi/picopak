# File and Path Signature of Large folders using bash (OSX and Linux)
# thanks to: http://stackoverflow.com/questions/1657232/how-can-i-calculate-an-md5-checksum-of-a-directory
import subprocess

def pathsize(path):
	# path must exist
	r = subprocess.Popen("du -d 0 \"%s\"" % path,stdout=subprocess.PIPE,shell=True,env=dict(BLOCKSIZE="1024"))
	return r.stdout.readline().split("\t")[0].strip()

def pathsignature(path,mode="256"):
	# path must exist
	# spaces in files are ok
	# empty string: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
	#
	# OPTIONAL: return the list of hashes instead of making a grand-hash
	# Note: metadata are not used in hash, BUT filename is used
	env = dict(XPATH=".",SUMCMD="shasum -a %s" % mode)
	r = subprocess.Popen("find \"$XPATH\" -type f -print0 | sort -z | xargs -0 ${SUMCMD} | ${SUMCMD} | awk '{print $1}'",cwd=path,stdout=subprocess.PIPE,shell=True,env=env)
	return r.stdout.readline().strip()

if __name__ == '__main__':
	import sys
	print pathsize(sys.argv[1])
	print pathsignature(sys.argv[1])
