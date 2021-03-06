#!/usr/bin/env python
#
# TODO: remove source or package
# TODO: list packages with not enough recent sources
# TODO: verify packname-uuid correspondence
# TODO: add size of package and last modified time (while hash is already provided)
# TODO: make a source read-only and react with ERROR if it changed
#
# Goal: package like backup management, not full
# 
# File structure (toplevel)
# data/
#   source.yaml (uuid of source key <> sources.yaml)
#   packagename (unique)/
#       .picopak    contains UUID of package (for check against renames)
# meta/
#   .git
#   sources.yaml
#   paks/
#       <pakname>/
#           package.yaml == most up to date
#           sources/
#               <source>.yaml == details of version for source
#   sources/
#       <source>.yaml == list of packages
#       
# meta/paks/<pakname>/sources/<source>.yaml 
#   is motivated by synchronization easiness, contains details
# meta/sources/<source>.yaml 
#   just list of packages (rebuilt from files)
import argparse
import datetime
import yaml
import os
import uuid
import subprocess
from os.path import expanduser
import coloredlogs, logging
#default: %(asctime)s %(hostname)s %(name)s[%(process)d] %(levelname)s %(message)s
os.environ["COLOREDLOGS_LOG_FORMAT"]='%(asctime)s %(name)s %(message)s'
coloredlogs.install()
logger = logging

def pathlast(path):
    """Returns last modified file scanning the whole path and calling stat"""
    FNULL = open(os.devnull, 'w')
    r = subprocess.Popen("find . -type f -print0 | xargs -0 stat -f \"%m %N\" | sort -nr | head -n 1",cwd=path,stderr=FNULL,stdout=subprocess.PIPE,shell=True)
    d,n = r.stdout.readline().strip().split(" ",1)
    r.kill()
    FNULL.close()
    return (int(d),n)


def pathsize(path):
    # path must exist
    r = subprocess.Popen("du -d 0 \"%s\"" % path,stdout=subprocess.PIPE,shell=True,env=dict(BLOCKSIZE="1024"))
    return r.stdout.readline().split("\t")[0].strip()

#._.DS_Store
#.DS_Store
def pathsignature(path,mode="256"):
    # path must exist
    # spaces in files are ok
    # empty string: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    #
    # OPTIONAL: return the list of hashes instead of making a grand-hash
    # Note: metadata are not used in hash, BUT filename is used
    env = dict(XPATH=".",SUMCMD="shasum -a %s" % mode)
    r = subprocess.Popen("find \"$XPATH\" -type f -not -name \"*.DS_Store\" -and -not -name \"._*\" -and -not -name .picopak -print0 | sort -z | xargs -0 ${SUMCMD} | ${SUMCMD} | awk '{print $1}'",cwd=path,stdout=subprocess.PIPE,shell=True,env=env)
    return r.stdout.readline().strip()


# TODO crossplatform
# TODO given path extract volume then label+uuid+diskformat
#
# OSX: add path => volume using mount output
# OSX: add "Partition Type"
def get_volume_name_uuid(path):
    return ("unknown","unknown")
    print "lookup",path
    r = subprocess.Popen(
    "diskutil info %s | grep 'Volume UUID'" % path,stdout=subprocess.PIPE,shell=True)
    line = r.stdout.readline()
    print line
    uuid = line.split(":",1)[1].strip()

    r = subprocess.Popen(
    "diskutil info %s | grep 'Volume Name'" % path,stdout=subprocess.PIPE,shell=True)
    line = r.stdout.readline()
    print line
    volname = line.split(":",1)[1].strip()
    return (volname,uuid)

class Config:
    def __init__(self,meta="",data=""):
        """initializes separately metadata (repo) and data (source)"""
        self.remote = "https://bitbucket.org/eruffaldi/picopak_store"
        self.meta = os.path.abspath(meta)
        self.data = os.path.abspath(data)
        self.name = "here"
        self.solveuuid()
    def source_marker_path(self):
        """sourc file name"""
        return os.path.join(self.data,"source.yaml")
    def solveuuid(self):
        """solves source uuid file"""
        if not os.path.isfile(self.source_marker_path()):
            self.uuid = None
            return None
        else:
            self.uuid = open(self.source_marker_path(),"rb").read().strip()
            return self.uuid
    def meta_paks_path(self):
        """folder containing package data"""
        return os.path.join(self.meta,"paks")
    def meta_sources_list_path(self):
        """file containing source listing"""
        return os.path.join(self.meta,"sources.yaml")
    def meta_sources_path(self):
        """file containing source listing"""
        return os.path.join(self.meta,"sources")
    def source_pak_path(self,name):
        """content folder of given package in the source"""
        return os.path.join(self.data,name)
    def meta_pak_path(self,name):
        """metadata folder of given package in meta"""
        return os.path.join(self.meta,"paks",name)
    def meta_pak_sources_path(self,name):
        """general detaisl"""
        return os.path.join(self.meta_pak_path(name),"sources")
    def meta_source_path(self,source):
        """details about source in metadata"""
        return os.path.join(self.meta,"sources",source + ".yaml")
    def meta_pak_source_path(self,name,source_uuid):
        """source in pack"""
        return os.path.join(self.meta_pak_sources_path(name),source_uuid + ".yaml")
    def loadsources(self):
        fp = self.meta_sources_list_path()
        if os.path.isfile(fp) == 0:
            return None
        else:
            with open(fp) as w:
                s = yaml.load(w)
                if s is None:
                    return dict()
                else:
                    return dict([(uuid,Source(uuid).fromdict(x)) for uuid,x in s.iteritems()])
    def solvesource(self,ss,req):
        # self
        if req == "" or req == "this":
            return Source(self.uuid).fromdict(dict(path=self.data,name="here"))
        else:
            # by uuid
            s = ss.get(req)
            if s is not None:
                return s
            # or by name
            for s in ss.values():
                if s.name == req:
                    return s
            return None

    def meta_pak_sources_list(self,name,load=False):
        """all packages of a given source"""
        fp = self.meta_pak_sources_path(name)        

        if load:
            if not os.path.isdir(fp):
                return dict()
            else:
                z = [yaml.load(open(os.path.join(fp,x))) for x in os.listdir(fp) if x.endswith(".yaml")]
                return dict([(x["uuid"],x) for x in z])
        else:
            if not os.path.isdir(fp):
                return []
            else:
                return [os.path.splitext(x)[0] for x in os.listdir(fp) if x.endswith(".yaml")]
    def meta_list_paks(self):
        """list packages"""
        fp = self.meta_paks_path()
        return [x for x in os.listdir(fp) if x[0] != "." and os.path.isdir(os.path.join(fp,x))]
    def source_list_paks(self):
        """list source packages"""
        r = []
        for x in os.listdir(self.data):
            fp = os.path.join(self.data,x)
            if os.path.isdir(fp):
                fpp = os.path.join(fp,".picopak")
                if os.path.isfile(fpp):                    
                    q = open(fpp,"rb").read().strip()
                    r.append((x,q))
                else:
                    r.append((x,None))
        return r

    def git_clean(self):
        return os.system("cd %s; git clean -f" % (self.meta)) 

    def git_reset(self):
        return os.system("cd %s; git reset --hard" % (self.meta)) 

    def git_rm(self,files):
        if type(files) is str:
            return os.system("cd %s; git rm %s" % (self.meta,files)) 
        else:
            return os.system("cd %s; git rm %s" % (self.meta," ".join(files))) 

    def git_add(self,files):
        """Add file or files to repo"""
        #print "git_add ",files," to ",self.meta
        if type(files) is str:
            return os.system("cd %s; git add %s" % (self.meta,files)) 
        else:
            return os.system("cd %s; git add %s" % (self.meta," ".join(files))) 
    def git_commit(self,msg="auto"):
        """Commit to repo"""
        #print "committing to ",self.meta
        return os.system("cd %s; git commit -am \"%s\"" % (self.meta,msg))      
    def git_pull(self):
        """Pull from repo"""
        #--work-tree=%s --git-dir=%s/.git 
        return os.system("cd %s; git pull origin master" % self.meta)
    def git_push(self):
        """Push to repo"""
        return os.system("cd %s; git push --set-upstream origin master" % self.meta)

class SourcePak:
    def __init__(self):
        self.content = {}
    def create(self,uuid,pak,time):
        self.uuid = uuid
        self.pak = pak
        self.firsttime = time
        #self.lasttime = time
    def fromdict(self,d):
        self.content.update(d)
        self.uuid = d["uuid"]
        self.pak = d["pak"]
        self.firsttime = d["firsttime"]
        #self.lasttime = d["lasttime"]
    def todict(self):
        self.content["uuid"] = self.uuid
        self.content["pak"] = self.pak
        self.content["firsttime"] = self.firsttime
        #self.content["lasttime"] = self.lasttime
        return self.content

class Source:
    def __init__(self,u=""):
        self.content = {}
        self.uuid = u
        self.name = ""
        self.path = ""
        self.label = ""
        self.firsttime = ""
        # last time is in the per-source information
    def fromdict(self,x):
        self.content = x
        self.name = x["name"]
        self.path = x.get("path","")
        self.label = x.get("label","")
        self.firsttime = x.get("firsttime","")
        return self
    def todict(self):
        self.content.update(dict(name=self.name,path=self.path,label=self.label,firsttime=self.firsttime))
        return self.content
    
class SourceState:
    def __init__(self):
        pass
    @staticmethod
    def create(uuid,cfg):
        self = SourceState()
        self.uuid = uuid
        self.cfg = cfg
        self.paks = []
        self.lasttime = ""
        self.locked = False
        return self
    @staticmethod
    def load(name,cfg):
        self = SourceState.create(name,cfg)
        tt = cfg.meta_source_path(self.uuid)
        if os.path.isfile(tt):
            q = yaml.load(open(tt,"rb"))
            self.lasttime = q.get("lasttime","")
            self.paks = q["paks"]
            self.locked = q.get("locked",False)
        return self

    #list(source_paks_set)
    def write(self):
        tt = self.cfg.meta_source_path(self.uuid)
        yaml.dump(dict(paks=self.paks,lasttime=self.lasttime,locked=self.locked),openmkdir(tt))
        self.cfg.git_add(tt)

def openmkdir(fp):
    q = os.path.split(fp)[0]
    if not os.path.isdir(q):
        os.makedirs(q)
    return open(fp,"wb")
def package_add(cfg,packname,now):
    pmetadir = cfg.meta_pak_path(packname)
    pmetadir_sig = os.path.join(pmetadir,"package.yml")
    pmetadir_sources = os.path.join(pmetadir,"sources")

    pdatadir = cfg.source_pak_path(packname)
    pdatadir_sig = os.path.join(pdatadir,".picopak")
    
    if os.path.isdir(pmetadir):
        logging.error("package with given name already existent: "+pmetadir)
        return False
    if not os.path.isdir(pdatadir):
        logging.error("missing data folder " + pdatadir)
        return False
    importing = os.path.isfile(pdatadir_sig)
    if importing:
        puuid = open(pdatadir_sig,"r").read().strip()
        logging.error("already existing .picopack, importing into listing "+puuid)
    else:
        puuid = str(uuid.uuid4())
        open(pdatadir_sig,"wb").write(puuid)
        logging.error("created package with name " + puuid)

    # create package folder
    os.makedirs(pmetadir_sources)
    x = dict(name=packname,uuid=puuid)
    yaml.dump(x,open(pmetadir_sig,"wb"))
    cfg.git_add(pmetadir_sig)
    cfg.git_commit("added " + packname)

    # then add cfg.uuid as source
    sp = SourcePak()
    sp.create(uuid=cfg.uuid,pak=packname,time=now)
    sig = pathsignature(cfg.source_pak_path(packname))
    sp.content["sha256"] = sig

    psf = cfg.meta_pak_source_path(packname,cfg.uuid)
    yaml.dump(sp.todict(),openmkdir(psf))
    cfg.git_add(psf)
    cfg.git_commit("added source " + cfg.uuid + " to package " + packname)
    return True

def _update_one_source_dict(cfg,uuid,su,msg="update source"):
    # add to sources.yaml
    ss = yaml.load(open(cfg.meta_sources_list_path(),"rb"))
    if ss is None:
        ss = dict()
    ss[uuid] = su
    yaml.dump(ss,open(cfg.meta_sources_list_path(),"wb"))
    # create source.yaml
    cfg.git_add("sources.yaml")
    cfg.git_commit(msg)

def addsource(cfg,path,uuid,name):
    uuid = str(uuid)
    volname,voluuid = get_volume_name_uuid(path)

    if not os.path.isfile(cfg.source_marker_path()):
        logging.info("making source file " + cfg.source_marker_path())
        open(cfg.source_marker_path(),"wb").write(uuid)    
    su = dict(name=name,path=path,volume_uuid=voluuid,volume_name=volname)
    _update_one_source_dict(cfg,uuid,su,"added source " + uuid +" to " + path)


def splitsets3(A,B):
    # return only A,common,only 
    common = A & B
    return A-common,common,B-common


def verify_source(cfg,s,args):
    logger.info("source verification %s with repo %s uuid %s" % (cfg.data,cfg.meta,s.uuid))
    now = datetime.datetime.now().isoformat()
    
    # scan folders for new pakcages
    # remove missing ones
    # MAYBE check changed
    source_paks = dict()
    for pathname,picocontent in cfg.source_list_paks():
        if picocontent != "":
            source_paks[pathname] = dict(uuid=uuid,name=pathname)
        else:
            source_paks[pathname] = dict(uuid="",name=pathname)


    source_paks_set = set(source_paks.keys())
    meta_paks_set = set(cfg.meta_list_paks())
    only_insource,common,only_inmeta = splitsets3(source_paks_set,meta_paks_set)
        
    # Load Source 
    su = SourceState.load(s.uuid,cfg)
    #tt = cfg.meta_source_path(s.uuid)
    #q = yaml.load(open(tt,"rb"))
    meta_source_paks_set = set(su.paks) #q["paks"])

    # readonly behavior due to Locking or due to asked sync 
    readonly = su.locked or args.readonly

    known_but_missing,common,known_but_removed = splitsets3(common,meta_source_paks_set)

    changed = False
    modified = False

    # Case 1: package unknown to meta => add to repo and to source
    for u in only_insource:
        changed = True
        if not readonly:
            logger.warn("\tunknown to meta: %s" % u)
            modified = modified or package_add(cfg,u,now)
        else:
            logger.error("\tRDONLY source changed: unknown to meta %s" % u)

    # Case 2: (source.paks & meta.paks)-meta.source.paks => need to add
    for pak in known_but_missing:
        changed = True
        if not readonly:
            logger.info("\tknown but missing - scanning: %s " % pak)
            tp = cfg.meta_pak_source_path(pak,s.uuid)
            sp = SourcePak()
            sp.create(cfg.uuid,pak,now)
            sig = pathsignature(cfg.source_pak_path(pak))
            sp.content["sha256"] = sig        
            yaml.dump(sp.todict(),openmkdir(tp))
            cfg.git_add(tp)
            modified = True
        else:
            logger.error("\tRDONLY source changed: known but missing %s" % pak)


    # Case 3: meta.source.paks-source.paks => removed => AUTO
    for u in known_but_removed:
        changed = True
        if not readonly:
            logger.warn("\tknown but removed %s" % u)
            cfg.git_rm(cfg.meta_pak_source_path(u,s.uuid))
            modified = True
        else:
            logger.error("\tRDONLY source changed: known but removed %s" % u)

    # Case 4: the remaining in source.paks => verify
    for pak in common:
        logger.info("\tpack verification, content scanning: %s" % pak)
        fp = cfg.meta_pak_source_path(pak,s.uuid)
        sp = SourcePak()
        pp = cfg.source_pak_path(pak)
        changed = True
        if os.path.isfile(fp):
            if not args.verifynew:
                sig = pathsignature(pp)
                tt = open(fp,"rb")
                sp.fromdict(yaml.load(tt))
                tt.close()
                if sp.content.get("sha256","") != sig:
                    if not readonly:
                        logger.info("\tcontent changed %s as %s" % (pp,sig))
                        sp.content["sha256"] = sig
                        yaml.dump(sp.todict(),openmkdir(fp))
                        cfg.git_add(fp)  
                        modified = True              
                    else:
                        logger.error("\tsource changed: content changed %s as %s" % (pp,sig))
                else:
                    changed = False
        elif not readonly:
            logger.error("\tRDONLY source changed: missing pak.source file %s" % fp)
        else:
            logger.warn("\tmissing pak.source file %s" % fp)
            sig = pathsignature(pp)
            sp.create(s.uuid,pak,time)
            sp.content["sha256"] = sig
            yaml.dump(sp.todict(),openmkdir(fp))
            cfg.git_add(fp)
            modified = True              

    # argument readonly mens no writes at all
    if not args.readonly:
        if changed:
            if su.locked:
                # writes down verification
                # MAYBE write down failure
                # NOTE no packs changes
                logger.error("source changed but locked, verify your source")
                su.lasttime = now
                su.write()
            else:
                # full write
                su.paks = list(source_paks_set)
                su.lasttime = now
                su.write()
        else:
            # only the timestamp
            su.lasttime = now
            su.write()
        modified = True              
    return modified

def process_source(args,cfg,ss):
    if args.subparser2_name == "list":
        # list known sources as of meta
        load_sources_lasttime(cfg,ss)
        print "\n".join(["%s\t%s\t%s\t%s" % (s.name,s.uuid,s.lasttime,s.path) for s in ss.values()])
    elif args.subparser2_name == "rename":
        s = cfg.solvesource(ss,args.uuid)
        if s is None:
            logging.error("unknown source " + args.uuid)
        else:
            if s.name != args.name:
                s.name = args.name
                _update_one_source_dict(cfg,s.uuid,s.todict())
                cfg.git_push()
    elif args.subparser2_name == "lock" or args.subparser2_name == "unlock":
        s = cfg.solvesource(ss,args.name)
        if s is None:
            logging.error("unknown source " + args.name)
        else:
            su = SourceState.load(s.uuid,cfg)
            n = args.subparser2_name == "lock"
            if n != su.locked:
                su.locked = n
                su.write()
                cfg.git_commit("committing locking op")
                cfg.git_pull()
                cfg.git_push()
    elif args.subparser2_name == "show":
        # for given source show details
        s = cfg.solvesource(ss,args.name)
        if s is None:
            logging.error("unknown source " + args.name)
        else:
            su = SourceState.load(s.uuid,cfg)
            print "\n".join(["uuid: %s" % s.uuid,"name: %s" %s.name,"lasttime: %s"%su.lasttime,"locked: %s"% su.locked])
            print "paks:"
            print "\n".join(["\t%s" % x for x in su.paks])
    elif args.subparser2_name == "add":
        # args.path EXIST
        # args.path CONTAINS source.yaml
        # args.path source.yaml uuid in list
        acfg = Config(cfg.meta,args.path)
        if not os.path.isdir(cfg.data):
            print "unknown path",args.path
        elif not acfg.uuid:
            puuid = str(uuid.uuid4())
            print "creating source at folder",cfg.data,"as",puuid
            addsource(acfg,acfg.data,puuid,args.name)
            if not acfg.solveuuid():
                print "!!failed source creation"
        else:
            s = ss.get(acfg.uuid)
            if s:
                print "source is known"
            else:
                print "adding unknown source",cfg.data,"as",cfg.uuid
                addsource(acfg,acfg.data,acfg.uuid,args.name)
    elif args.subparser2_name == "verify":
        logging.warn("UNCOMPLETED - make multiple sources")
        # sourcename/id => source object
        # verify objects
        s = cfg.solvesource(ss,args.name)
        if s is None:
            logging.error("unknown source %s",args.name)
            return
        # verify uuid
        elif s.uuid != cfg.uuid:
            acfg = Config(cfg.meta,s.path)
            if not acfg.solveuuid():
                logging.error("missing source %s for %s %s %s",acfg.data,s.path,s.uuid,s.name)
                return
        else:
            acfg = cfg
        modified = verify_source(acfg,s,args)
        if modified:
            cfg.git_commit("sync")
            # push changes
            cfg.git_push()

def load_sources_lasttime(cfg,ss):
    for s in ss.values():
        su = SourceState.load(s.uuid,cfg)
        s.lasttime = su.lasttime
def process_pack(args,cfg,ss):
    if args.subparser2_name == "list":
        print "\n".join(cfg.meta_list_paks())
    elif args.subparser2_name == "add":
        now = datetime.datetime.now().isoformat()
        package_add(cfg,args.name,now)
    elif args.subparser2_name == "sources" or args.subparser2_name == "where":        
        load_sources_lasttime(cfg,ss)
        if args.name == "all":
            names = cfg.meta_list_paks()
            for n in sorted(names):
                q = cfg.meta_pak_sources_list(n,load=True)
                print n
                print "\n".join(["\t%s %s %s" % (uuid,ss[uuid].lasttime,info.get("sha256","")) for uuid,info in q.iteritems()])
        else:
            q = cfg.meta_pak_sources_list(args.name,load=True)
            print "\n".join(["%s %s %s" % (uuid,ss[uuid].lasttime,info.get("sha256","")) for uuid,info in q.iteritems()])
    elif args.subparser2_name == "path":
        source_uuids = cfg.meta_pak_sources_list(args.name)
        for uuid in source_uuids:            
            s = ss.get(uuid)
            if s and os.path.isdir(s.path):
                print os.path.join(s.path,args.name)                
                return
        return "/dev/null"
    
def main():
    argparser = argparse.ArgumentParser(prog="picpak my backup management")  
    subparsers = argparser.add_subparsers(help='sub-command help', dest='subparser_name')
    argparser.add_argument("--root",default="~/.picopak")

    # Init Command
    parser_init = subparsers.add_parser('init', help = "initializs a picopak repository")
    parser_init.add_argument("path",default="",help="default is in ~/.picopak")
    parser_init.add_argument("--meta-only",dest="metaonly",action="store_true",help="is not creating a source")
    parser_init.add_argument("--name",dest="name",help="when this is not a meta-only this is the optional name of the source",default="")

    # Sync Command
    parser_sync = subparsers.add_parser('sync', help = "source help")
    parser_sync.add_argument("--verifynew",help="only verify new",action="store_true")
    parser_sync.add_argument("--read-only",dest="readonly",help="only verify new",action="store_true")
    parser_sync.add_argument("-r",dest="readonly",help="only verify new",action="store_true")

    # Source Commands
    parser_source = subparsers.add_parser('source', help = "source help")
    subparsers_source = parser_source.add_subparsers(help="sub-sub-command help",dest='subparser2_name')
    
    parser_source_add = subparsers_source.add_parser('add', help='adds')
    parser_source_add.add_argument("path")
    parser_source_add.add_argument("name")

    parser_source_list = subparsers_source.add_parser('list', help='list')

    parser_source_rename = subparsers_source.add_parser('rename', help='rename')
    parser_source_rename.add_argument("uuid")
    parser_source_rename.add_argument("name")

    parser_source_show = subparsers_source.add_parser('show', help='show content')
    parser_source_show.add_argument("name")
    
    parser_source_verify = subparsers_source.add_parser('verify', help='content')
    parser_source_verify.add_argument("name",default="this")
    parser_source_verify.add_argument("--read-only",dest="readonly",help="read-only operation",action="store_true")
    parser_source_verify.add_argument("-r",dest="readonly",help="read-only operation",action="store_true")
    parser_source_verify.add_argument("--verifynew",help="do not scan content of known packages",action="store_true")

    parser_source_lock = subparsers_source.add_parser('lock', help='lock source')
    parser_source_lock.add_argument("name")

    parser_source_unlock = subparsers_source.add_parser('unlock', help='unlock source')
    parser_source_unlock.add_argument("name")

    # Pack Commands
    parser_pack = subparsers.add_parser('pack', help = "pack help")
    subparsers_pack = parser_pack.add_subparsers(help="sub-sub-command help",dest='subparser2_name')
    parser_pack_list = subparsers_pack.add_parser('list', help='adds')

    parser_pack_add = subparsers_pack.add_parser('add', help='adds')
    parser_pack_add.add_argument("name")

    parser_pack_sources = subparsers_pack.add_parser('sources', help='list pak sources')
    parser_pack_sources.add_argument("name")

    parser_pack_where = subparsers_pack.add_parser('where', help='list pak where')
    parser_pack_where.add_argument("name")

    parser_pack_path = subparsers_pack.add_parser('path', help='return available local path')
    parser_pack_path.add_argument("name")

    # Go!
    args = argparser.parse_args()
    args.root = expanduser(args.root)

    if args.subparser_name != "init":
        cfg = Config(os.path.join(args.root,"meta"),os.path.join(args.root,"data"))
        ss = cfg.loadsources()
        if False: # not needed
            if not cfg.solveuuid():
                logging.error("missing source.yaml, use init or source add")
                return
            if not cfg.uuid in ss:
                logging.error("missing this source in sources, adding")
                addsource(cfg,args.data,cfg.uuid,"")
            if False:
                cfg.uuid = str(uuid.uuid4())
                addsource(cfg,cfg.data,cfg.uuid,"")
                open(cfg.source_marker_path(),"wb").write(cfg.uuid)
                if ss is None:
                    logging.error("missing sources, not valid folder")
                    return

    if args.subparser_name == "init":
        if not os.path.isdir(args.path):
            cfg = Config(os.path.join(args.path,"meta"),os.path.join(args.path,"data"))
            logging.info("initing" + args.path)
            os.makedirs(cfg.meta)
            os.makedirs(cfg.meta_paks_path())
            os.system("cd %s; git init" % cfg.meta)
            os.system("cd %s; git remote add origin %s" % (cfg.meta,cfg.remote))
            cfg.git_pull()
            if not args.metaonly:
                logging.info("adding data folder " + cfg.data)
                os.makedirs(cfg.data)
                addsource(cfg,cfg.data,uuid.uuid4(),args.name)
                cfg.git_push()
        else:
            logging.info("already existing " + args.path)
    elif args.subparser_name == "source":
        process_source(args,cfg,ss)
    elif args.subparser_name == "pack":
        process_pack(args,cfg,ss)
    elif args.subparser_name == "sync":
        # eventually even: git clean -f
        cfg.git_reset()
        cfg.git_pull()
        cfg.git_push()
        # then check for attached sources
        ss = cfg.loadsources()
        modified = False
        for s in ss.values():
            if not os.path.isdir(s.path):
                logging.warn("source %s %s not available" % (s.uuid,s.path))
                continue                
            # verify presence of uuid
            acfg = Config(cfg.meta,s.path)
            u = acfg.solveuuid()
            if u != s.uuid:
                logging.error("%s %s not matching uuid %s " % (s.uuid,s.path,u))
                continue
            # then verify the content
            modified = modified or verify_source(acfg,s,args)
        if modified:
            cfg.git_commit("sync")
            # push changes
            cfg.git_push()


if __name__ == '__main__':
    main()