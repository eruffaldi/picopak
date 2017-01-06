#!/usr/bin/env python
#
# Goal: package like backup management, not full
#
# Usage
# - initialize it on localhost. Default localhost is .picopak
#   picopak init <path?>
# - add external source
#   picopak source add <path>
# - add packages
# 
# File structure (toplevel)
# data/
#   .picopak-source contains UUID of source
#   packagename/
#       .picopak    contains UUID of package
# meta/
#   .git
#   sources.yaml
#   paks/
#       package.yaml == most up to date
#       sources/
#           sourceuuid.yaml == details of version for source
#   sources/
#       sourceuuid.yaml == list of packages
#       
import argparse
import datetime
import yaml
import os
import uuid
import subprocess
from os.path import expanduser

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
        self.meta = os.path.abspath(meta)
        self.data = os.path.abspath(data)
        self.name = "here"
        self.solveuuid()
    def getthissourcefile(self):
        """sourc file name"""
        return os.path.join(self.data,"source.yaml")
    def solveuuid(self):
        """solves source uuid file"""
        if not os.path.isfile(self.getthissourcefile()):
            self.uuid = None
            return None
        else:
            self.uuid = open(self.getthissourcefile(),"rb").read().strip()
            return self.uuid
    def getpacksmetadir(self):
        """folder containing package data"""
        return os.path.join(self.meta,"paks")
    def getsourcesfile(self):
        """file containing source listing"""
        return os.path.join(self.meta,"sources.yaml")
    def getpackdatadir(self,name):
        """content folder of given package in the source"""
        return os.path.join(self.data,name)
    def getpackmetadir(self,name):
        """metadata folder of given package in meta"""
        return os.path.join(self.meta,"paks",name)
    def getpacksourcesdir(self,name):
        """general detaisl"""
        return os.path.join(self.meta,name,"sources")
    def getsourcefile(self,source):
        """details about source in metadata"""
        return os.path.join(self.meta,"sources",source + ".yaml")
    def getpacksourcefile(self,name,source):
        """source in pack"""
        return os.path.join(self.meta,name,"sources",source + ".yaml")
    def listpacksources(self,name,load=False):
        """all packages of a given source"""
        fp = self.getpacksourcesdir(name)
        z = [os.path.join(fp,x) for x in os.listdir(fp) if x.endswith(".yaml")]
        if load:
            z = [yaml.load(open(x,"rb")) for x in z]
            return dict([(x["uuid"],x) for x in z])
        else:
            return z
    def listmetapacks(self):
        """list packages"""
        fp = os.path.join(self.meta,"paks")
        return [x for x in os.listdir(fp) if x[0] != "." and os.path.isdir(os.path.join(fp,x))]
    def listdatapacks(self):
        """list source pckages"""
        fp = self.data
        return [x for x in os.listdir(fp) if os.path.isfile(os.path.join(fp,x,".picopak"))]
    def add(self,files):
        """Add file or files to repo"""
        print "adding ",files," to ",self.meta
        if type(files) is str:
            return os.system("cd %s; git add %s" % (self.meta,files)) 
        else:
            return os.system("cd %s; git add %s" % (self.meta," ".join(files))) 
    def commit(self,msg="auto"):
        """Commit to repo"""
        print "committing to ",self.meta
        return os.system("cd %s; git commit -am \"%s\"" % (self.meta,msg))      
    def pull(self):
        """Pull from repo"""
        #--work-tree=%s --git-dir=%s/.git 
        return os.system("cd %s; git pull origin master" % self.meta)
    def push(self):
        """Push to repo"""
        return os.system("cd %s; git push --set-upstream origin master" % self.meta)

class Source:
    def __init__(self,u=""):
        self.content = {}
        self.uuid = u
        self.name = ""
        self.path = ""
        self.label = ""
    def fromdict(self,x):
        self.content = x
        self.name = x["name"]
        self.path = x.get("path","")
        self.label = x.get("label","")
        return self
    def todict(self):
        self.content.update(dict(name=self.name,path=self.path,label=self.label))
        return self.content
    
def loadsources(cfg):
    fp = cfg.getsourcesfile()
    if os.path.isfile(fp) == 0:
        return None
    else:
        with open(fp) as w:
            s = yaml.load(w)
            if s is None:
                return dict()
            else:
                return dict([(uuid,Source(uuid).fromdict(x)) for uuid,x in s.iteritems()])

def package_add(cfg,packname):
    pmetadir = cfg.getpackmetadir(packname)
    pmetadir_sig = os.path.join(pmetadir,"package.yml")
    pmetadir_sources = os.path.join(pmetadir,"sources")

    pdatadir = cfg.getpackdatadir(packname)
    pdatadir_sig = os.path.join(pdatadir,".picopak")
    
    if os.path.isdir(pmetadir):
        print "package with given name already existent:",pmetadir
        return              
    if not os.path.isdir(pdatadir):
        print "missing data folder",pdatadir
        return
    importing = os.path.isfile(pdatadir_sig)
    if importing:
        puuid = open(pdatadir_sig,"r").read().strip()
        print "already existing .picopack, importing into listing",puuid
    else:
        puuid = str(uuid.uuid4())
        open(pdatadir_sig,"wb").write(puuid)
        print "created package with name",puuid

    # create package folder
    os.makedirs(pmetadir_sources)
    x = dict(name=packname,uuid=puuid)
    yaml.dump(x,open(pmetadir_sig,"wb"))
    cfg.add(pmetadir_sig)
    cfg.commit("added " + packname)

    # then add cfg.uuid as source
    x = dict(source=cfg.uuid,name=packname,lasttime=datetime.datetime.now().isoformat())
    psf = cfg.getpacksourcefile(packname,cfg.uuid)
    yaml.dump(x,open(psf,"wb"))
    cfg.add(pmetadir_sig)
    cfg.commit("added source " + cfg.uuid + " to package " + packname)

def _update_one_source_dict(cfg,uuid,su,msg="update source"):
    # add to sources.yaml
    ss = yaml.load(open(cfg.getsourcesfile(),"rb"))
    if ss is None:
        ss = dict()
    ss[uuid] = su
    yaml.dump(ss,open(cfg.getsourcesfile(),"wb"))
    # create source.yaml
    cfg.add("sources.yaml")
    cfg.commit(msg)

def addsource(cfg,path,uuid,name):
    uuid = str(uuid)
    volname,voluuid = get_volume_name_uuid(path)

    if not os.path.isfile(cfg.getthissourcefile()):
        print "making source file",cfg.getthissourcefile()
        open(cfg.getthissourcefile(),"wb").write(uuid)    
    su = dict(name=name,path=path,volume_uuid=voluuid,volume_name=volname)
    _update_one_source_dict(cfg,uuid,su,"added source " + uuid +" to " + path)


def solvesource(cfg,ss,req):
    # self
    if req == "" or req == "this":
        return Source(cfg.uuid).fromdict(dict(path=cfg.data,name="here"))
    else:
        # by uuid
        s = ss.get(req)
        if s is not None:
            return s
        # or by name
        for s in ss:
            if s["name"] == req:
                return s
        return None

def verify_source(acfg,s):
    print "source verification",acfg.data,"with repo",acfg.meta,"uuid",s.uuid

    # scan folders for new pakcages
    # remove missing ones
    # MAYBE check changed
    indata = dict()
    for x in os.listdir(acfg.data):
        fp = os.path.join(acfg.data,x)
        if x[0] != "." and os.path.isdir(fp):
            fpp = os.path.join(fp,".picopak")
            if not os.path.isfile(fpp):
                print "\tignoring folder",x,"missing",fpp
                continue
            # file contains UUID
            uuid = open(fpp,"rb").read().strip()
            indata[uuid] = x
    print "\tfound:",",".join(["%s" % x for x in indata.keys()])

    # Relatively to the source a package can be in one of the following states:
    # 1- in data but not known => add to repo
    # 2- in data but not listed to source =>  add to source
    # 3- listed but not in data => remove
    # 4- both => need check
    indataset = set(indata.keys())
    allpacks = set(acfg.listmetapacks())
    unknownpacks = allpacks-indataset
    # Case 1
    for u in unknownpacks:
        pass #package_add(acfg,indata[u])

    print "Need to deal with cases 2..4"
    for u in (indataset-unknownpacks):
        pass

    for x in indata:
        pass
    #    sources = acfg.listpacksources(x,load=True)
    #    if not s.uuid in sources:
    #        print "need to add",x,"to",s.uuid
def process_source(args,cfg,ss):
    if args.subparser2_name == "list":
        # list known sources as of meta
        print "\n".join(["%s\t%s\t%s" % (s.name,s.uuid,s.path) for s in ss.values()])
    elif args.subparser2_name == "rename":
        s = solvesource(cfg,ss,args.uuid)
        if s is None:
            print "unknown source",args.uuid
        else:
            if s.name != args.name:
                s.name = args.name
                _update_one_source_dict(cfg,s.uuid,s.todict())
                cfg.push()
    elif args.subparser2_name == "show":
        print "UNTESTED"
        # for given source show details
        s = solvesource(cfg,ss,args.name)
        if s is None:
            print "unknown source"
        else:
            indata = set(acfg.listdatapacks())
            print "\n".join(indata)
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
        print "UNCOMPLETED"
        # sourcename/id => source object
        # verify objects
        s = solvesource(cfg,ss,args.name)
        if s is None:
            print "unknown source",args.name
        # verify uuid
        elif s.uuid != cfg.uuid:
            acfg = Config(s.path)
            if not acfg.solveuuid():
                print "missing source",acfg.meta
                return
        else:
            acfg = cfg
        verifysource(acfg,s)

def process_pack(args,cfg,ss):
    if args.subparser2_name == "list":
        print "\n".join(cfg.listmetapacks())
    elif args.subparser2_name == "add":
        package_add(cfg,args.name)
    elif args.subparser2_name == "sources":
        packname = args.name
        print "NOT IMPLEMENTED"
        # check existent pack
        # check sources         
    elif args.subparser2_name == "sync":
        print "NOT IMPLEMENTED"
    
def main():
    argparser = argparse.ArgumentParser(prog="picpak my backup management")  
    subparsers = argparser.add_subparsers(help='sub-command help', dest='subparser_name')
    argparser.add_argument("--root",default="~/.picopak")

    parser_init = subparsers.add_parser('init', help = "initializs a picopak repository")
    parser_init.add_argument("path",default="",help="default is in ~/.picopak")
    parser_init.add_argument("--meta-only",dest="metaonly",action="store_true",help="is not creating a source")
    parser_init.add_argument("--name",dest="name",help="when this is not a meta-only this is the optional name of the source",default="")


    parser_sync = subparsers.add_parser('sync', help = "source help")

    parser_source = subparsers.add_parser('source', help = "source help")
    subparsers_source = parser_source.add_subparsers(help="sub-sub-command help",dest='subparser2_name')
    parser_source_add = subparsers_source.add_parser('add', help='adds')
    parser_source_list = subparsers_source.add_parser('list', help='list')
    parser_source_rename = subparsers_source.add_parser('rename', help='rename')
    parser_source_content = subparsers_source.add_parser('show', help='show content')
    parser_source_verify = subparsers_source.add_parser('verify', help='content')

    parser_source_add.add_argument("path")
    parser_source_add.add_argument("name")
    parser_source_rename.add_argument("uuid")
    parser_source_rename.add_argument("name")
    parser_source_verify.add_argument("name",default="this")

    parser_pack = subparsers.add_parser('pack', help = "pack help")
    subparsers_pack = parser_pack.add_subparsers(help="sub-sub-command help",dest='subparser2_name')
    parser_pack_list = subparsers_pack.add_parser('list', help='adds')
    parser_pack_add = subparsers_pack.add_parser('add', help='adds')
    parser_pack_add.add_argument("name")

    args = argparser.parse_args()
    args.root = expanduser(args.root)

    if args.subparser_name != "init":
        cfg = Config(os.path.join(args.root,"meta"),os.path.join(args.root,"data"))
        ss = loadsources(cfg)
        if False: # not needed
            if not cfg.solveuuid():
                print "missing source.yaml, use init or source add"
                return
            if not cfg.uuid in ss:
                print "missing this source in sources, adding"
                addsource(cfg,args.data,cfg.uuid,"")
            if False:
                cfg.uuid = str(uuid.uuid4())
                addsource(cfg,cfg.data,cfg.uuid,"")
                open(cfg.getthissourcefile(),"wb").write(cfg.uuid)
                if ss is None:
                    print "missing sources, not valid folder"
                    return

    if args.subparser_name == "init":
        if not os.path.isdir(args.path):
            cfg = Config(os.path.join(args.path,"meta"),os.path.join(args.path,"data"))
            print "initing",args.path
            os.makedirs(cfg.meta)
            os.makedirs(cfg.getpacksmetadir())
            os.system("cd %s; git init" % cfg.meta)
            os.system("cd %s; git remote add origin https://bitbucket.org/eruffaldi/picopak_store" % cfg.meta)
            cfg.pull()
            if not args.metaonly:
                print "adding data folder",cfg.data
                os.makedirs(cfg.data)
                addsource(cfg,cfg.data,uuid.uuid4(),args.name)
                cfg.push()
        else:
            print "already existing",args.path
    elif args.subparser_name == "source":
        process_source(args,cfg,ss)
    elif args.subparser_name == "pack":
        process_pack(args,cfg,ss)
    elif args.subparser_name == "sync":
        cfg.pull()
        cfg.push()
        # then check for attached sources
        ss = loadsources(cfg)
        for s in ss.values():
            if not os.path.isdir(s.path):
                print s.uuid,s.path,"not available"
                continue                
            # verify presence of uuid
            acfg = Config(cfg.meta,s.path)
            u = acfg.solveuuid()
            if u != s.uuid:
                print s.uuid,s.path,"not matching uuid",u
                continue
            # then verify the content
            verify_source(acfg,s)
        cfg.push()


if __name__ == '__main__':
    main()