# -*- coding: utf-8 -*-
"""
Created on Sun Jul 20 19:25:37 2014

@author: pcr20
"""


import parse
import os
import re
import pdb
import traceback
import sys
import shutil
import time
import sqlite3 as lite
from PIL import Image

#rootPath = 'I:\\Documents and Settings\\pcr20\\My Documents\\My Pictures'
#rootPath = '/volume1/Documents/pcr20/My Documents/My Pictures'
#albumPath = '/volume1/Documents/albums'


#initialise list
albumsfound=[]
#init dictionary
albumcontents={}
picasablock = re.compile("\[[^\[]*")

import ConfigParser
config = ConfigParser.ConfigParser()
config.read(os.path.join(os.path.dirname(sys.argv[0]), "picasaTrawl.ini"))
configUploadr = ConfigParser.ConfigParser()
configUploadr.read(os.path.join(os.path.dirname(sys.argv[0]), "uploadr.ini"))

EXCLUDED_FOLDERS = eval(config.get('Config','EXCLUDED_FOLDERS'))
PICASA_INI_FILES  = eval(config.get('Config','PICASA_INI_FILES'))
albumPath = eval(config.get('Config','ALBUM_PATH'))
rootPath = eval(config.get('Config','ROOT_PATH'))
DB_PATH = eval(config.get('Config','DB_PATH'))
FLICKR = eval(configUploadr.get('Config','FLICKR'))
is_public_default=int(FLICKR["is_public"])
is_friend_default=int(FLICKR["is_friend"])
is_family_default=int(FLICKR["is_family"])

ispublicre = re.compile("(\s*)(?:ispublic)(?:\s*)=(?:\s*)([0-9]+)(?:\s*)")
isfamilyre = re.compile("(\s*)(?:isfamily)(?:\s*)=(?:\s*)([0-9]+)(?:\s*)")
isfriendre = re.compile("(\s*)(?:isfriend)(?:\s*)=(?:\s*)([0-9]+)(?:\s*)")

if os.path.isfile(DB_PATH):
    os.remove(DB_PATH)
con = lite.connect(DB_PATH)
con.text_factory = str
cur = con.cursor()
cur.execute('create table if not exists albums (name text, albumtime REAL, isfamily INTEGER, isfriend INTEGER, ispublic INTEGER)')
cur.execute('create index if not exists setsindex on albums (name)')
con.commit()

try:

 #create albums directory if it doesn't exist:
 if os.path.isdir(albumPath):
    #clean existing albums:
    shutil.rmtree(albumPath)
 os.mkdir(albumPath)
 
 for root, dirs, files in os.walk(rootPath):
    #print root,dirs,files
    for excludedDirectory in EXCLUDED_FOLDERS: #remove directories from the .walk which match list in EXCLUDED_FOLDERS
        if excludedDirectory in dirs:
            dirs.remove(excludedDirectory)
    for filename in (set(files) & set(PICASA_INI_FILES)):
        print( os.path.join(root, filename))

        st = os.stat(os.path.join(root, filename))
        atime = st.st_atime #access time
        mtime = st.st_mtime #modification time

        #inputfile = open("I:\\Documents and Settings\\pcr20\\My Documents\\My Pictures\\2012_06_23\\.picasa.ini")
        inputfile = open(os.path.join(root, filename),'rU') #U for universal line ending mode, convert to unix line ending automatically if necessary
        
        my_text = inputfile.read() #reads to whole text file
        
        for match in picasablock.finditer(my_text):
            #print "%s: %s" % (match.start(), match.group(1))
            #find album    
            parsealbum=parse.parse("[.album:{albumid}]{:s}{fieldstart}",match.group())
            if parsealbum:
                #then we have an album
                parse_album_fields=parse.findall("{field}={fieldresult}\n",match.group(),parsealbum.spans["fieldstart"][0])                
                
                #check if album exists already
                albumidlist=[z["albumid"] for z in albumsfound]
                if parsealbum.named["albumid"] in albumidlist: 
                    idx=albumidlist.index(parsealbum.named["albumid"]) #duplicate album
                    
                    print "duplicate album in: ",os.path.relpath(os.path.join(root, filename),rootPath).replace(os.path.sep, '/'),str(parsealbum.named["albumid"])
                    
                    for r in parse_album_fields:
                        #print r.named
                        if albumsfound[idx].has_key(r.named["field"]):
                            if albumsfound[idx][r.named["field"]]!=r.named["fieldresult"]:
                                print("WARNING: "+r.named["field"]+" was: "+albumsfound[idx][r.named["field"]]+" replaced by: "+r.named["fieldresult"])
                        albumsfound[idx][r.named["field"]]=r.named["fieldresult"]
                    
                else:
                    albumsfound.append({"albumid":parsealbum.named["albumid"]})
                    parse_album_fields=parse.findall("{field}={fieldresult}\n",match.group(),parsealbum.spans["fieldstart"][0])
                    #print "%s:%s" % (match.start(),match.group())
                    albumsfound[-1]["mtime"]=mtime #storing mtime of .picasa file is not very useful, and rather misleading
                    #albumsfound[-1][".picasa"]=os.path.join(root, filename)
                    albumsfound[-1][".picasa"]=os.path.relpath(os.path.join(root, filename),rootPath).replace(os.path.sep, '/')
                
                    for r in parse_album_fields:
                        #print r.named
                        albumsfound[-1][r.named["field"]]=r.named["fieldresult"]
                #parse description field for permissions
                albumidlist=[z["albumid"] for z in albumsfound]
                idx=albumidlist.index(parsealbum.named["albumid"])
                ispublic=is_public_default
                isfriend=is_friend_default
                isfamily=is_family_default                
                if albumsfound[idx].has_key("description"):
                    #regex to find isfamily[any whitespace]=[any whitespace][at least one number digit][non number digit or eof]
                    description=albumsfound[idx]["description"]
                    ispublicfound = re.search(ispublicre,description)
                    isfriendfound = re.search(isfriendre,description)
                    isfamilyfound = re.search(isfamilyre,description)

                    startidx=len(description)
                    endidx=0
                    if ispublicfound:
                        if startidx>ispublicfound.start(1):
                            startidx=ispublicfound.start(1)
                        ispublic=int(ispublicfound.group(2))
                        if endidx<ispublicfound.end(2):
                            endidx=ispublicfound.end(2)

                    if isfriendfound:
                        if startidx>isfriendfound.start(1):
                            startidx=isfriendfound.start(1)    
                        isfriend=int(isfriendfound.group(2))
                        if endidx<isfriendfound.end(2):
                            endidx=isfriendfound.end(2)

                    if isfamilyfound:
                        if startidx>isfamilyfound.start(1):
                            startidx=isfamilyfound.start(1)
                        isfamily=int(isfamilyfound.group(2))
                        if endidx<isfamilyfound.end(2):
                            endidx=isfamilyfound.end(2)
                    if albumsfound[idx].has_key("ispublic"):
                        if albumsfound[idx]["ispublic"]!=ispublic:
                            print("WARNING: ispublic was: "+str(albumsfound[idx]["ispublic"])+" replaced by: "+str(ispublic))
                    if albumsfound[idx].has_key("isfriend"):
                        if albumsfound[idx]["isfriend"]!=isfriend:
                            print("WARNING: isfriend was: "+str(albumsfound[idx]["isfriend"])+" replaced by: "+str(isfriend))
                    if albumsfound[idx].has_key("isfamily"):
                        if albumsfound[idx]["isfamily"]!=isfamily:
                            print("WARNING: isfamily was: "+str(albumsfound[idx]["isfamily"])+" replaced by: "+str(isfamily))
                    albumsfound[idx]["description"]=description[:startidx]+description[endidx:] #remove meta data from description
                albumsfound[idx]["ispublic"]=ispublic
                albumsfound[idx]["isfriend"]=isfriend
                albumsfound[idx]["isfamily"]=isfamily                
  
            elif not (match.group().startswith("[Picasa]") or match.group().startswith("[Contacts]") or match.group().startswith("[Contacts2]") or match.group().startswith("[encoding]")):
                #a photo
                parsephoto=parse.parse("[{photofilename}]{:s}{fieldstart}",match.group())
                if parsephoto:
                    if os.path.isfile(os.path.join(root,parsephoto.named["photofilename"])): #check file exists
                    
                        st = os.stat(os.path.join(root,parsephoto.named["photofilename"]))
                        atimePhoto = st.st_atime #access time
                        mtimePhoto = st.st_mtime #modification time
                        try:
                            tags=Image.open(os.path.join(root,parsephoto.named["photofilename"]))._getexif()
                            DateTimeOriginal = time.mktime(time.strptime(tags[36867],"%Y:%m:%d %H:%M:%S"))                
                        except:
                            DateTimeOriginal = mtimePhoto    
                    
                        parseout2=parse.findall("{field}={fieldresult}\n",match.group(),parsephoto.spans["fieldstart"][0])
                        #print "%s:%s" % (match.start(),match.group())
                        for r in parseout2:
                            #print r.named
                            if r.named["field"]=="albums":
                                albumids=r.named["fieldresult"]+","
                                for albumgroup in re.finditer("[0-9a-f]*,",albumids):
                                    albummatch = albumgroup.group() #' remove trailing ,
                                    albummatch = albummatch[:-1]
                                    if not albummatch in albumcontents.keys():
                                        albumcontents[albummatch]={} #initialise dictionary if key doesn't exist
                                        albumcontents[albummatch]["photos"]=[]
                                    #albumcontents[albummatch]["photos"].append(os.path.join(root,parsephoto.named["photofilename"]))
                                    albumcontents[albummatch]["photos"].append(os.path.relpath(os.path.join(root,parsephoto.named["photofilename"]),rootPath).replace(os.path.sep, '/'))
                                    if "mtime" in albumcontents[albummatch].keys():
                                        if mtime > albumcontents[albummatch]["mtime"]:
                                            albumcontents[albummatch]["mtime"]=mtimePhoto #current mtime is newer than that stored, so update
                                    else:
                                        albumcontents[albummatch]["mtime"]=mtimePhoto #first entry, so add key
                                    if "DateTimeOriginal" in albumcontents[albummatch].keys():
                                        if DateTimeOriginal > albumcontents[albummatch]["DateTimeOriginal"]:
                                            albumcontents[albummatch]["DateTimeOriginal"]=DateTimeOriginal #current mtime is newer than that stored, so update
                                    else:
                                        albumcontents[albummatch]["DateTimeOriginal"]=DateTimeOriginal #first entry, so add key                                        
                    else:
                        print "WARNING No file named: ",os.path.join(root,parsephoto.named["photofilename"])
                        #pdb.set_trace()
            
        inputfile.close()

 #update album mtime to be the later of the date that the album was created and the date that a photo was added to the album
 numPhotosInAlbums=0
 for idx,album in enumerate(albumsfound):
    if album["albumid"] in albumcontents.keys():
        if album["mtime"]<albumcontents[album["albumid"]]["mtime"]:
            albumsfound[idx]["mtime"]=albumcontents[album["albumid"]]["mtime"]

    
        #create directory for this album
        if "name" in album.keys():
          thisAlbumPath=os.path.join(albumPath,album["name"])
        else:
          thisAlbumPath=os.path.join(albumPath,album["albumid"])
        os.mkdir(thisAlbumPath)

        
        for photofilename in albumcontents[album["albumid"]]["photos"]:
            os.link(os.path.join(rootPath,photofilename),os.path.join(thisAlbumPath,os.path.basename(photofilename)))
        numPhotosInAlbums=numPhotosInAlbums+len(albumcontents[album["albumid"]]["photos"])
        #revert folder time to album time
        timesForTuple=albumcontents[album["albumid"]]["DateTimeOriginal"]
        os.utime(thisAlbumPath,(timesForTuple,timesForTuple)) #set directory time to album time
        cur.execute('INSERT INTO albums (name, albumtime, isfamily, isfriend, ispublic) VALUES (?, ?, ?, ?, ?)',(album["name"],float(timesForTuple),album["isfamily"],album["isfriend"],album["ispublic"]))

    else:
        albumsfound.pop(idx) #remove item because the album is empty
                
 con.commit()  
 print numPhotosInAlbums," photos in ",len(albumsfound)," albums found (not all photos may be unique)"
 print albumsfound
 print albumcontents


 #import flickrsynctest2
 #flickrsynctest2.main(albumsfound,albumcontents,rootPath)

except:
 type, value, tb = sys.exc_info()
 traceback.print_exc()
 pdb.post_mortem(tb)  
