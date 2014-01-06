# -*- coding: utf8 -*-
"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from os.path import join
from traceback import print_exc
from time import strftime,strptime

import xbmc
import xbmcgui
import common
import dbabstractionlayer as dblayer


DB_VERSION19      = '1.9.12'
DB_VERSION201     = '2.0.1'
DB_VERSION229     = '2.2.9'
DB_VERSION1202    = '12.0.2'
DB_VERSION        = '12.2.4'
lists_separator   = "||"

class MyPictureDBException(Exception):
    pass

class MyPictureDB(object):
    
    def __init__(self):
        self.tagTypeDBKeys = {}
        self.db_backend = common.getaddon_setting('db_backend')

        if not self.db_backend:
            self.db_backend = 'sqlite'
            
        if self.db_backend.lower() == 'mysql':
            self.db_name    = common.getaddon_setting('db_name')
            self.db_user    = common.getaddon_setting('db_user')
            self.db_pass    = common.getaddon_setting('db_pass')
            self.db_address = common.getaddon_setting('db_address')
            self.db_port    = common.getaddon_setting('db_port')     

        else:
            db_name         = common.getaddon_setting('db_name_sqlite')
            if not db_name:
                db_name = 'MyPictures.db'
                
            db_path         = xbmc.translatePath( "special://database/")
            self.db_name    = join(db_path, db_name)
            self.db_user    = ''
            self.db_pass    = ''
            self.db_address = ''
            self.db_port    = ''
            
        common.log('', "Used DB Backend = " + self.db_backend)
        #common.log('', "Path = " + self.db_name)
        self.con = dblayer.DBFactory(self.db_backend, self.db_name, self.db_user, self.db_pass, self.db_address, self.db_port)
        self.cur = self.con.cursor()
        
    def version_table(self):
        
        # Test Version of DB
        try:
            strVersion = self.cur.request("Select strVersion from DBVersion")[0][0]
        except Exception,msg:
            common.log("Database abstraction layer",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )    
            strVersion = '1.0.0'            
    
        common.log("MPDB.version_table", "MyPicsDB database version is %s"%str(strVersion) ) 
    
        # version of DB is greater/equal than 1.9.0 but less then 2.0.1
        if common.check_version(strVersion, DB_VERSION201)>0 and common.check_version(strVersion, DB_VERSION19) <=0:
            common.log("MPDB.version_table", "MyPicsDB database with version %s will be updated to version %s"%(str(strVersion),str(DB_VERSION)) ) 
            self.version_201_tables()
            # update tags for new introduced yyyy-mm  tag
            self.update_yyyy_mm_tags()
            
        # version of DB is less then 1.9.0
        elif common.check_version(strVersion, DB_VERSION19) >0:
            dialog = xbmcgui.Dialog()
            dialog.ok(common.getstring(30000).encode("utf8"), "Database will be updated", "You must re-scan your folders")
            common.log("MPDB.Versiversion_tableonTable", "MyPicsDB database will be updated", xbmc.LOGNOTICE )
            self.make_new_base(True)
            #VersionTable()

        # version of DB is less then 2.2.9
        elif common.check_version(strVersion, DB_VERSION229)>0:
            # update tags for new introduced yyyy-mm  tag
            common.log("MPDB.version_table", "MyPicsDB database will be updated to version %s. New YYYY-MM tags will be inserted."%str(DB_VERSION), xbmc.LOGNOTICE )
            self.update_yyyy_mm_tags()
            self.version_211_tables()         
            self.version_1202_tables()
            self.cur.execute("update DBVersion set strVersion = '"+DB_VERSION+"'")
            self.con.commit()
                        
        # version of DB is less then 12.0.2
        elif common.check_version(strVersion, DB_VERSION1202)>0:
            # update tags for new introduced yyyy-mm  tag
            common.log("MPDB.version_table", "MyPicsDB database will be updated to version %s. New YYYY-MM tags will be inserted."%str(DB_VERSION), xbmc.LOGNOTICE )
            self.update_yyyy_mm_tags()
            if self.con.get_backend() == "mysql":
                self.version_201_tables()         
            self.version_1202_tables()
            self.cur.execute("update DBVersion set strVersion = '"+DB_VERSION+"'")
            self.con.commit()
            
        # version of DB is less then current version
        elif common.check_version(strVersion, DB_VERSION)>0:
            self.cur.execute("update DBVersion set strVersion = '"+DB_VERSION+"'")
            self.con.commit()
            try:
                self.cur.execute("CREATE INDEX idxFiles2 ON Files(ImageDateTime)")
            except:
                pass
            try:
                self.cur.execute("CREATE INDEX idxFiles3 ON Files (DateAdded)")
            except:
                pass
            try:
                self.cur.execute("CREATE INDEX idxFiles4 ON Files (idFolder)")
            except:
                pass
            if self.con.get_backend() == "mysql":
                try:
                    self.cur.execute("alter table FilterWizard modify pkFilter integer auto_increment not null")
                    self.cur.execute("alter table FilterWizardItems modify idItems integer auto_increment not null")
                except:
                    pass
        else:
            common.log("MPDB.version_table", "MyPicsDB database contains already current schema" )
            

    
    # new tag type YYYY-MM in version 2.10
    def update_yyyy_mm_tags(self):   

        dictionnary = {}
        common.show_notification(common.getstring(30000), 'DB-Update', 2000)
        rows = [row for row in self.cur.request("SELECT idFile, strFilename, strPath, ImageDateTime FROM Files")]
        
        for row in rows:
            dictionnary['YYYY-MM'] = str(row[3])[:7]
            try:
                self.tags_insert( row[0], row[1], row[2], dictionnary)
                common.log( 'MPDB.update_yyyy_mm_tags()', 'Tag YYYY-MM with value %s inserted for "%s"'%(dictionnary['YYYY-MM'], row[1]) )
            except:
                common.log( 'MPDB.update_yyyy_mm_tags()', 'Tag YYYY-MM with value %s NOT inserted for "%s"'%(dictionnary['YYYY-MM'], row[1]) )
                
        self.con.commit()

        return True

    def version_1202_tables(self):
  
        try:
            self.cur.execute("create table fc_bak as select * from FilesInCollections")
            self.cur.execute("drop table FilesInCollections")

            self.cur.execute("create table FilesInCollections (idCol INTEGER, idFile INTEGER NOT NULL, Constraint UNI_COLLECTION UNIQUE (idCol, idFile))")
            self.cur.execute("CREATE INDEX idxFilesInCollections1 ON FilesInCollections(idCol)")
            self.cur.execute("CREATE INDEX idxFilesInCollections2 ON FilesInCollections(idFile)")
            
            self.cur.execute("insert into FilesInCollections select * from fc_bak ")
            self.cur.execute("drop table fc_bak")
            self.con.commit()
        except:
            pass
           
               
    def version_211_tables(self):
  
        try:
            self.cur.execute("drop table FilterWizard ")
            self.cur.execute("drop table FilterWizardItems ")
        except:
            pass
           
        self.version_201_tables()
            
    # new tables in version 2.0.1
    def version_201_tables(self ):
        #table 'FilterWizard'
        try:
            self.cur.execute("""create table FilterWizard (pkFilter integer %s, strFilterName %s unique, bMatchAll integer, StartDate date, EndDate date)"""%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(255)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else:
                common.log("MPDB.version_201_tables", "CREATE TABLE FilterWizard ...", xbmc.LOGERROR )
                common.log("MPDB.version_201_tables", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    
        #table 'FilterWizardItems'
        try:
            self.cur.execute("""create table FilterWizardItems (idItems integer %s, fkFilter integer, strItem %s, nState integer, FOREIGN KEY(fkFilter) REFERENCES FilterWizard(pkFilter))"""%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(255)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else:
                common.log("MPDB.version_201_tables", "CREATE TABLE FilterWizardItems ...", xbmc.LOGERROR )
                common.log("MPDB.version_201_tables", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
                
        self.cur.close()
        self.cur = self.con.cursor()                
        self.cur.execute("update DBVersion set strVersion = '"+DB_VERSION+"'")
        self.con.commit()            
        #self.cur.close()
    
        
    def make_new_base(self, ecrase=True):
    
        if ecrase:
            #drop table
            for table in ['FilterWizard', 'FilterWizardItems', 'Persons', 'PersonsInFiles', 'tags', 'TagContent', 'TagContents', 'TagsInFiles', 'TagTypes','files', 'Files', "keywords", 'folders', 'Folders',"KeywordsInFiles","Collections","FilesInCollections", "periodes", "Periodes","CategoriesInFiles","Categories","SupplementalCategoriesInFiles","SupplementalCategories","CitiesInFiles","Cities","CountriesInFiles","Countries","DBVersion"]:
                common.log("MPDB.make_new_base >> Dropping table", "%s"%table)
                try:
                    self.cur.execute("""DROP TABLE %s"""%table)
                except Exception,msg:
                    common.log("MPDB.make_new_base", "DROP TABLE %s"%table, xbmc.LOGERROR )
                    common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    
        # table: version
        try:
            self.cur.execute("""CREATE TABLE DBVersion ( strVersion VARCHAR(20))""")
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else: 
                common.log("MPDB.make_new_base", "CREATE TABLE Files ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )    
    
        try:
            self.cur.execute("insert into DBVersion values('"+DB_VERSION+"')")
            self.con.commit()
        except:
            pass
            
        #table 'Files'
        try:
            self.cur.execute("""CREATE TABLE Files ( idFile INTEGER %s, 
                                                   idFolder integer, 
                                                   strPath %s, 
                                                   strFilename %s, 
                                                   ftype %s,
                                                   DateAdded DATETIME, 
                                                   Thumb %s,  
                                                   ImageRating %s,
                                                   ImageDateTime DATETIME, 
                                                   Sha %s, 
                                                   CONSTRAINT UNI_FILE UNIQUE (strPath,strFilename))"""%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(200), self.con.get_ddl_varchar(128), self.con.get_ddl_varchar(40), self.con.get_ddl_varchar(1024), self.con.get_ddl_varchar(40), self.con.get_ddl_varchar(100)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else: 
                common.log("MPDB.make_new_base", "CREATE TABLE Files ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    
        #table 'Folders'
        try:
            self.cur.execute("CREATE TABLE Folders (idFolder INTEGER %s, FolderName %s, ParentFolder INTEGER, FullPath %s UNIQUE, HasPics INTEGER)"%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(255), self.con.get_ddl_varchar(255)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else:
                common.log("MPDB.make_new_base", "CREATE TABLE Folders ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        #table 'Collections'
        try:
            self.cur.execute("CREATE TABLE Collections (idCol INTEGER %s, CollectionName %s UNIQUE)"%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(255)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else: 
                common.log("MPDB.make_new_base", "CREATE TABLE Collections ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        #table 'FilesInCollections'
        try:
            self.cur.execute("CREATE TABLE FilesInCollections (idCol INTEGER, idFile INTEGER NOT NULL, Constraint UNI_COLLECTION UNIQUE (idCol,idFile))")
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else: 
                common.log("MPDB.make_new_base", "CREATE TABLE FilesInCollections ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        #table 'Periodes'
        try:
            self.cur.execute("CREATE TABLE Periodes(idPeriode INTEGER %s, PeriodeName %s UNIQUE NOT NULL, DateStart DATETIME NOT NULL, DateEnd DATETIME NOT NULL, CONSTRAINT UNI_PERIODE UNIQUE (PeriodeName,DateStart,DateEnd) )"%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(255)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else: 
                common.log("MPDB.make_new_base", "CREATE TABLE Periods ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        #table 'Rootpaths'
        try:
            self.cur.execute("CREATE TABLE Rootpaths (idRoot INTEGER %s, Path %s UNIQUE NOT NULL, Recursive INTEGER NOT NULL, Remove INTEGER NOT NULL, Exclude INTEGER DEFAULT 0)"%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(255)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else: 
                common.log("MPDB.make_new_base", "CREATE TABLE RootPaths ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    
    
        #table 'TagTypes'
        try:
            self.cur.execute("CREATE TABLE TagTypes (idTagType INTEGER %s, TagType %s, TagTranslation %s, CONSTRAINT UNI_TAG UNIQUE(TagType) )"%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(128), self.con.get_ddl_varchar(128)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else:
                common.log("MPDB.make_new_base", "CREATE TABLE TagTypes ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    
        #table 'TagContent'
        try:
            self.cur.execute("CREATE TABLE TagContents (idTagContent INTEGER %s, idTagType INTEGER, TagContent %s, CONSTRAINT UNI_TAG UNIQUE(idTagType, TagContent) )"%(self.con.get_ddl_primary_key(), self.con.get_ddl_varchar(255)))
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else:
                common.log("MPDB.make_new_base", "CREATE TABLE Tags ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    
        #table 'TagsInFiles'
        try:
            self.cur.execute("CREATE TABLE TagsInFiles (idTagContent INTEGER, idFile INTEGER NOT NULL)")
        except Exception,msg:
            if str(msg).find("already exists") > -1:
                pass
            else:
                common.log("MPDB.make_new_base", "CREATE TABLE TagsInFiles ...", xbmc.LOGERROR )
                common.log("MPDB.make_new_base", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
    
        self.version_201_tables()
        
        try:
            self.cur.execute("CREATE INDEX idxFilesInCollections1 ON FilesInCollections(idCol)")
            self.cur.execute("CREATE INDEX idxFilesInCollections2 ON FilesInCollections(idFile)")
        except Exception,msg:
            pass
    
    
        # Index creation for new tag tables
        try:
            self.cur.execute("CREATE INDEX idxTagTypes1 ON TagTypes(idTagType)")
        except Exception,msg:
            pass
    
        try:
            self.cur.execute("CREATE INDEX idxTagContent1 ON TagContents(idTagContent)")
        except Exception,msg:
            pass
    
        try:
            self.cur.execute("CREATE INDEX idxTagsInFiles1 ON TagsInFiles(idTagContent)")
            self.cur.execute("CREATE INDEX idxTagsInFiles2 ON TagsInFiles(idFile)")
        except Exception,msg:
            pass
    
        try:
            self.cur.execute("CREATE INDEX idxFolders1 ON Folders(idFolder)")
            self.cur.execute("CREATE INDEX idxFolders2 ON Folders(ParentFolder)")
        except Exception,msg:
            pass
    
        try:
            self.cur.execute("CREATE INDEX idxFiles1 ON Files(idFile, idFolder)")
            self.cur.execute("CREATE INDEX idxFiles2 ON Files(ImageDateTime)")
            
        except Exception,msg:
            pass
    
        self.con.commit()
    
        #self.cur.close()
    """
    columnList = []
    def addColumn(table,colheader,formatstring="VARCHAR(1024)"):
        global columnList
        key = table + '||' + colheader + '||' + formatstring
        try:
            columnList.index(key);
            return
        except:
            conn = sqlite.connect(pictureDB)
            cn=conn.cursor()
            try:
                self.cur.execute('ALTER TABLE %s ADD "%s" %s'%(table,colheader,formatstring))
            except Exception,msg:
                if not msg.args[0].startswith("duplicate column name"):
                    common.log("MPDB.addColumn", 'EXCEPTION  %s,%s,%s'%(table,colheader,formatstring), xbmc.LOGERROR )
                    common.log("MPDB.addColumn", "\t%s - %s"%(Exception,msg), xbmc.LOGERROR )
    
            self.con.commit()
            self.cur.close()
            columnList.append(key)
    """
    
    def cleanup_keywords(self):
    
        try:

            common.log("", "Tag tables will be cleaned.")
            self.cur.execute('delete from Files where idFolder not in( select idFolder from Folders)')
            if self.con.get_backend() == "mysql":
                self.cur.execute('delete from Folders where idFolder not in( select fi.idFolder from Files fi) and ParentFolder is not null and idFolder not in (select coalesce(fold.ParentFolder,0) from (select * from Folders) fold)')
            else:
                self.cur.execute('delete from Folders where idFolder not in( select idFolder from Files) and ParentFolder is not null and idFolder not in (select coalesce(ParentFolder,0) from Folders)')
            self.cur.execute( "delete from TagsInFiles where idFile not in(select idFile from Files )")
            self.cur.execute( "delete from TagContents where idTagContent not in (select idTagContent from TagsInFiles)")
            # Only delete tags which are not translated!
            self.cur.execute( "delete from TagTypes where idTagType not in (select idTagType from TagContents) and TagType = TagTranslation")
            self.con.commit()
            
        except Exception,msg:
            common.log("MPDB.cleanup_keywords", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            #self.cur.close()
            raise
    
        #self.con.commit()
        #self.cur.close()
    
    def pic_exists(self, picpath, picfile):
        """
        Check whether or not a file exists in the DB
        """
    
        try:
            count = self.cur.request("SELECT count(*) FROM Files WHERE strPath = ? AND strFilename = ?",(picpath,picfile,) )
        except Exception,msg:
            common.log("MPDB.pic_exists", "EXCEPTION >> pic_exists %s,%s"%(picpath,picfile), xbmc.LOGERROR )
            common.log("MPDB.pic_exists", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            raise Exception, msg
        if count==0:
            retour= False
        else:
            retour= True
        #self.cur.close()
        return retour

        
    def listdir(self, path):
        """
        List Files from DB where path
        """

        full_filename = []
        try:
            pictures = [row for row in self.cur.request( u"SELECT f.strPath, f.strFilename FROM Files f,Folders p WHERE f.idFolder=p.idFolder AND p.FullPath=(?) order by f.idFile",(path,))]
            for entry in pictures:
                full_filename.append(join(entry[0], entry[1]))

        except Exception,msg:
            common.log( "", "path = "%path, xbmc.LOGERROR )
            common.log( "", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            self.cur.close()
            raise
        
        return full_filename

        
    def file_insert(self, path,filename,dictionnary,update=False, sha=0):
        """
        insert into file database the dictionnary values into the dictionnary keys fields
        keys are DB fields ; values are DB values
        """
        
        try:
            
            if self.con.get_backend() == "mysql":
                imagedatetime = "0000-00-00 00:00:00"
            else:
                imagedatetime = "null"
                
            if  "EXIF DateTimeOriginal" in dictionnary:
                imagedatetime = dictionnary["EXIF DateTimeOriginal"]
                #print "1 = " + str(imagedatetime)
            if len(imagedatetime.strip()) < 10 and "ImageDateTime" in dictionnary:
                imagedatetime = dictionnary["ImageDateTime"]
                #print "2 = " + str(imagedatetime)
            if len(imagedatetime.strip()) < 10 and "EXIF DateTimeDigitized" in dictionnary:
                imagedatetime = dictionnary["EXIF DateTimeDigitized"]
                #print "3 = " + str(imagedatetime)
             
            dictionnary['YYYY-MM'] = imagedatetime[:7]

        except:
            pass        
    
        try:
            if update :
                if self.pic_exists(path,filename):
                    try:
                        #print "file exists in database and rescan is set to true..."
                        (id_files, ) = self.cur.request("Select idFile FROM Files WHERE idFolder = (SELECT idFolder FROM Folders WHERE FullPath=?) AND strFilename=? ",(path,filename))
                        id_file=id_files[0]
                    except:
                        return
                        
                    try:
                        
                        #print "File = " + str(id_file)
                        
                        #self.cur.execute("Delete From Files Where idFile=?", (id_file,))
                        #self.cur.execute("Delete From FilesInCollections Where idFile=?", (id_file,))
                        
                        id_tagcontents=[row for row in self.cur.request("SELECT idTagContent FROM TagsInFiles WHERE idFile=?", (id_file,))]
                        self.cur.execute("Delete From TagsInFiles Where idFile=?", (id_file,))
                        
                        for id_tagcontent in id_tagcontents:
                            self.cur.execute("Delete From TagsContents Where idTagContent= ?", (id_tagcontent,))
                        
                        self.cur.execute("""Update Files set ftype=?, Thumb=?, ImageRating=?, ImageDateTime=?, Sha=? where idFile=?""", ( dictionnary["ftype"], dictionnary["Thumb"], dictionnary["Image Rating"], imagedatetime, sha, id_file ) )
                    except:
                        pass
                    
            else:
             
                self.cur.execute( """INSERT INTO Files(idFolder, strPath, strFilename, ftype, DateAdded,  Thumb,  ImageRating, ImageDateTime, Sha) values (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                          ( dictionnary["idFolder"],  dictionnary["strPath"], dictionnary["strFilename"], dictionnary["ftype"], dictionnary["DateAdded"], dictionnary["Thumb"], dictionnary["Image Rating"], imagedatetime, sha ) )
            #self.con.commit()
        except Exception,msg:
    
            common.log("file_insert", "path = %s"%common.smart_unicode(filename).encode('utf-8'), xbmc.LOGERROR)
            common.log("file_insert",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            common.log( "file_insert", """INSERT INTO Files('%s') values (%s)""" % ( "','".join(dictionnary.keys()) , ",".join(["?"]*len(dictionnary.values())) ), xbmc.LOGERROR )
            #self.con.commit()
            #self.cur.close()
            raise MyPictureDBException
    
    
        # meta table inserts
        try:
            id_file = [row[0] for row in self.cur.request("SELECT idFile FROM Files WHERE strPath = ? AND strFilename = ?",(path,filename,) )] [0]
            self.tags_insert(id_file, filename, path, dictionnary)
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )             
    
        self.con.commit()
        #self.cur.close()
        return True
    
    
    def tags_insert(self, idfile, filename, path, dictionnary):

        # loop over tags dictionary
        for tag_type, value in dictionnary.iteritems():
    
            if isinstance(value, basestring) and dictionnary[tag_type]:
    
                # exclude the following tags
                if tag_type not in ['sha', 'strFilename', #'strPath',
                                   'mtime', #'ftype',
                                   'source', 'urgency', 'time created', 'date created']:
    
                    tag_values = dictionnary[tag_type].split(lists_separator)
    
                    tag_type = tag_type[0].upper() + tag_type[1:]
    
                    for value in tag_values:
    
                        if len(value.strip()) > 0:
                            # change dates
                            if tag_type == 'EXIF DateTimeOriginal':
                                value = value[:10]
        
                            # first make sure that the tag exists in table TagTypes
                            # is it already in our list?
                            if not tag_type in self.tagTypeDBKeys:
        
                                common.log("tags_insert", "tag_type %s not in self.tagTypeDBKeys"%tag_type)
                                
                                # not in list therefore insert into table TagTypes
                                try:
                                    self.cur.execute(" INSERT INTO TagTypes(tagType, TagTranslation) VALUES(?, ?) ",(tag_type,tag_type))
                                except Exception,msg:
                                    if str(msg)=="column TagType is not unique" or "Duplicate entry" in str(msg):
                                        pass
                                    else:
                                        common.log("tags_insert", "path = %s"%common.smart_unicode(filename).encode('utf-8'), xbmc.LOGERROR)
                                        common.log("tags_insert",  'tagType = %s'%tag_type, xbmc.LOGERROR )
                                        common.log("tags_insert",  "\t%s - %s"%(Exception,msg), xbmc.LOGERROR )
        
                                # select the key of the tag from table TagTypes
                                try:
                                    id_tag_type= [row[0] for row in self.cur.request("SELECT min(idTagType) FROM TagTypes WHERE TagType = ? ",(tag_type,) )][0]
                                except Exception,msg:
                                    common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )             

                                self.tagTypeDBKeys[tag_type] = id_tag_type
                                common.log("tags_insert", 'self.tagTypeDBKeys["%s"] = %s'%(tag_type, id_tag_type))
                            else :
                                id_tag_type = self.tagTypeDBKeys[tag_type]
                                common.log("tags_insert", '%s = self.tagTypeDBKeys["%s"]'%(id_tag_type, tag_type))
                                
                            try:
                                self.cur.execute(" INSERT INTO TagContents(idTagType,TagContent) VALUES(?,?) ",(id_tag_type,value))
                            except Exception,msg:
                                if str(msg)=="columns idTagType, TagContent are not unique" or "Duplicate entry" in str(msg):
                                    pass
                                else:
                                    common.log("tags_insert", "path = %s"%common.smart_unicode(filename).encode('utf-8'), xbmc.LOGERROR)
                                    common.log("tags_insert", 'EXCEPTION >> tags', xbmc.LOGERROR )
                                    common.log("tags_insert", 'tagType = %s'%tag_type, xbmc.LOGERROR )
                                    common.log("tags_insert", 'tagValue = %s'%common.smart_utf8(value), xbmc.LOGERROR )
                                    common.log("tags_insert", "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        
       
                            #Then, add the corresponding id of file and id of tag inside the TagsInFiles database
                            try:
                                self.cur.execute(" INSERT INTO TagsInFiles(idTagContent,idFile) SELECT t.idTagContent, %d FROM TagContents t WHERE t.idTagType=%d AND t.TagContent = ? "%(idfile,id_tag_type), (value,))

                            # At first column was named idTag then idTagContent
                            except Exception,msg:
                                if str(msg)=="PRIMARY KEY must be unique" or "Duplicate entry" in str(msg):
                                    pass
                                else:
                                    common.log("tags_insert", "Error while adding TagsInFiles")
                                    common.log("tags_insert", "%s - %s"% (Exception,msg) )
                                    common.log("tags_insert", "%s %s - %s"%(idfile,id_tag_type,common.smart_utf8(value)))
    
        return True
    
    
    def folder_insert(self, foldername, folderpath, parentfolderID, haspic):
        """insert into Folders database, the folder name, folder parent, full path and if has pics
            Return the id of the folder inserted"""
    
        #insert in the Folders database
        try:
            self.cur.execute("""INSERT INTO Folders(FolderName,ParentFolder,FullPath,HasPics) VALUES (?,?,?,?) """,(foldername,parentfolderID,folderpath,haspic))
        except:
            pass
        self.con.commit()
        #return the id of the folder inserted
        
        try:
            retour = [row for (row,) in self.cur.request("""SELECT idFolder FROM Folders where FullPath= ?""",(folderpath,))][0]
        except:
            retour = 0
        #self.cur.close()
        return retour
    
    def get_children(self, folderid):
        #print "get_children(" + str(folderid) + ")"
        """search all children Folders ids for the given folder id"""
        childrens=[c[0] for c in self.cur.request("SELECT idFolder FROM Folders WHERE ParentFolder=? ", (folderid,))]
        list_child=[]
        list_child.extend(childrens)
        for idchild in childrens:
            list_child.extend(self.get_children(idchild))
        return list_child
    
    def del_pic(self, picpath, picfile=None): 
    
        if picfile:
            self.cur.request("""DELETE FROM Files WHERE idFolder = (SELECT idFolder FROM Folders WHERE FullPath Like '%s_') AND strFilename=? """%picpath,(picfile, ))
    
        else:
    
            try:
                if picpath:
                    try:
                        idpath = self.cur.request("""SELECT idFolder FROM Folders WHERE FullPath = ? """, (picpath,))[0][0]
                    except Exception,msg:
                        common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )             

                else:
                    try:
                        idpath = self.cur.request("""SELECT idFolder FROM Folders WHERE FullPath is null""")[0][0]
                    except Exception,msg:
                        common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )             

                common.log( "del_pic", "(%s,%s)"%( common.smart_utf8(picpath),common.smart_utf8(picfile)) )
    
                deletelist=[]
                deletelist.append(idpath)
                deletelist.extend(self.get_children(str(idpath)))
    
                self.cur.request( """DELETE FROM Files WHERE idFolder in ("%s")"""%""" "," """.join([str(i) for i in deletelist]) )
                common.log( "del_pic", """DELETE FROM Folders WHERE idFolder in ("%s") """%""" "," """.join([str(i) for i in deletelist]))
                self.cur.request( """DELETE FROM Folders WHERE idFolder in ("%s") """%""" "," """.join([str(i) for i in deletelist]) )
            except:
                pass
            
        self.cleanup_keywords()
    
        return
    
    def sha_of_file ( self, filepath, length = None ) :
        #found here : http://sebsauvage.net/python/doublesdetector.py
        #thanks sebsauvage for all its snippets !
        """ Compute SHA (Secure Hash Algorythm) of a file.
            Input : filepath : full path and name of file (eg. 'c:\windows\emm386.exe')
            Output : string : contains the hexadecimal representation of the SHA of the file.
                              returns '0' if file could not be read (file not found, no read rights...)
        """
    
        loaded_bytes = 65536
        
        try:
            import hashlib
            digest = hashlib.md5()
        except ImportError:
            # for Python << 2.5
            import md5
            digest = md5.new()    
    
        filepath = common.smart_unicode(filepath)
        try:
            try:
                filehandle = open(filepath,'rb')
            except:
                filehandle = open(filepath.encode('utf-8'),'rb')
    
            data = filehandle.read(65536)
            while len(data) != 0:
                digest.update(data)
                data = filehandle.read(65536)
                loaded_bytes += 65536
                #common.log("", "file = %s   loaded = %s"%(filepath, loaded_bytes))
                if length != None and loaded_bytes >= length:
                    break
            filehandle.close()
        except:
            print_exc()
            return '0'
        else:
            return digest.hexdigest()
    
    def stored_sha (self, path, filename): 
        #return the SHA in DB for the given picture
        try:
            return [row for row in self.cur.request( """select sha from Files where strPath=? and strFilename=? """,(path, filename))][0][0]
        except:
            return "0"

    
    def get_rating(self, path, filename):   
        try:
            return [row for row in self.cur.request( """SELECT Files.ImageRating FROM Files WHERE strPath=? AND strFilename=? """, (path, filename) )][0][0]
        except IndexError:
            return None
    
    
    
    #####################################
    # Filter Wizard functions
    #####################################
    
    def filterwizard_result(self, set_tags, unset_tags, match_all, start_date='', end_date=''):

        if len(set_tags) == 0 and len(unset_tags) == 0 and start_date == '' and end_date == '':
            return
        match_all = '1' if match_all not in [0,'0',False] else '0' # Sometimes match_all can be ambiguous
        set_tags_array = set_tags.split("|||")
        unset_tags_array = unset_tags.split("|||")    

        outer_select = "SELECT distinct strPath,strFilename, ImageDateTime FROM Files WHERE 1=1 "

        # These selects are joined with an IN clause
        inner_select = "SELECT tif.idfile FROM TagContents tc, TagsInFiles tif , TagTypes tt WHERE tif.idTagContent = tc.idTagContent AND tc.idTagType = tt.idTagType "

        # Build the conditions
        if match_all == "1":
            if len(set_tags) > 0:
                for filter_tags in set_tags_array:

                    key_value = filter_tags.split("||")
                    key = key_value[0]
                    value = key_value[1].replace("'", "''")

                    condition = "AND tt.TagTranslation = '"+key+"' AND tc.TagContent = '"+value+"' "
                    outer_select += " AND idFile in ( " + inner_select + condition + " ) "

            if len(unset_tags) > 0:
                for filter_tags in unset_tags_array:

                    key_value = filter_tags.split("||")
                    key = key_value[0]
                    value = key_value[1].replace("'", "''")

                    condition = "AND tt.TagTranslation = '"+key+"' AND tc.TagContent = '"+value+"' "
                    outer_select += " AND idFile not in ( " + inner_select + condition + " ) "            

        else:

            if len(set_tags) > 0:
                old_key = ""
                old_value = ""

                for filter_tags in set_tags_array:

                    key_value = filter_tags.split("||")
                    key = key_value[0]
                    value = key_value[1].replace("'", "''")

                    if key != old_key:
                        if len(old_key) > 0:
                            condition = "AND tt.TagTranslation = '"+old_key+"' AND tc.TagContent in( "+old_value+" ) "
                            outer_select += " AND idFile in ( " + inner_select + condition + " ) "
                        old_key = key
                        old_value = "'" + value + "'"
                    else:
                        old_value += ", '" + value + "'"
                condition = "AND tt.TagTranslation = '"+old_key+"' AND tc.TagContent in( "+old_value+" ) "
                outer_select += " AND idFile in ( " + inner_select + condition + " ) "

            if len(unset_tags) > 0:
                old_key = ""
                old_value = ""
                
                for filter_tags in unset_tags_array:

                    key_value = filter_tags.split("||")
                    key = key_value[0]
                    value = key_value[1].replace("'", "''")
    
                    if key != old_key:
                        if len(old_key) > 0:
                            condition = "AND tt.TagTranslation = '"+old_key+"' AND tc.TagContent in( "+old_value+" ) "
                            outer_select += " AND idFile not in ( " + inner_select + condition + " ) "
                        old_key = key
                        old_value = "'" + value + "'"
                    else:
                        old_value += ", '" + value + "'"

                condition = "AND tt.TagTranslation = '"+old_key+"' AND tc.TagContent in( "+old_value+" ) "
                outer_select += " AND idFile not in ( " + inner_select + condition + " ) "

        outer_select += " order by imagedatetime "

        # test if start or end_date is set
        if start_date != '' or end_date != '':
            dates_set = 0
            outer_select = 'Select strPath,strFilename from (' + outer_select + ' ) mainset '
            
            if start_date != '':
                dates_set += 1
                if self.con.get_backend() == "mysql":
                    outer_select += " where ImageDateTime >= date_format('%s', '%%Y-%%m-%%d') "%(start_date,)
                else:
                    outer_select += " where ImageDateTime >= date('%s') "%(start_date,)

            if end_date != '':
                dates_set += 1
                if dates_set == 1:
                    if self.con.get_backend() == "mysql":
                        outer_select += " where ImageDateTime <= date_format('%s', '%%Y-%%m-%%d') "%(end_date,)
                    else:
                        outer_select += " where ImageDateTime <= date('%s') "%(end_date,)
                else:
                    if self.con.get_backend() == "mysql":   
                        outer_select += " and ImageDateTime <= date_format('%s', '%%Y-%%m-%%d') "%(end_date,)
                    else:
                        outer_select += " and ImageDateTime <= date('%s') "%(end_date,)

        else:
            outer_select = 'Select strPath,strFilename from (' + outer_select + ' ) maindateset '

        common.log('filterwizard_result', outer_select, xbmc.LOGDEBUG)
        return [row for row in self.cur.request(outer_select)]


    def filterwizard_list_filters(self):
        filterarray = []
        for row in self.cur.request( """select strFilterName from FilterWizard order by 1"""):
            filterarray.append(row[0])
        return filterarray


    def filterwizard_delete_filter(self, filter_name):
        try:
            filterkey = self.cur.request( "select pkFilter from FilterWizard where strFilterName = ? ",(filter_name, ))[0][0]
            
            self.cur.request( "delete from FilterWizardItems where fkFilter = ?", (filterkey, ))
            self.cur.request( "delete from FilterWizardItems where fkFilter not in (select pkFilter from FilterWizard)")
            self.cur.request( "delete from FilterWizard where pkFilter = ? ",(filterkey, ))    
        except:
            pass
        
        
        if self.db_backend.lower() == 'mysql':
            self.cur.request("analyze table FilterWizard")
            self.cur.request("analyze table FilterWizardItems")
        else:
            self.cur.request("analyze")           

        self.con.commit()

    def filterwizard_save_filter(self, filter_name, items, bmatch_all, start_date ='', end_date = ''):

        if self.db_backend.lower() == 'mysql':

            if start_date == '':
                start_date = "0000-00-00 00:00:00"

            if end_date == '':
                end_date = "0000-00-00 00:00:00"

        match_all = (1 if bmatch_all == True else 0)

        try:
            rows = [row for row in self.cur.request( "select count(*) from FilterWizard where strFilterName = ? ",(filter_name, ))] [0][0]
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )             
            rows = 0

        if rows == 0:
            self.cur.request( "insert into FilterWizard(strFilterName, bMatchAll, StartDate, EndDate) values (?, ?, ?, ?) ",(filter_name, match_all, start_date, end_date ))
        else:
            self.cur.request( "update FilterWizard set bMatchAll = ?, StartDate = ?, EndDate = ? where strFiltername = ? ",(match_all, start_date, end_date, filter_name ))

        try:
            filter_key = [row for row in self.cur.request( "select pkFilter from FilterWizard where strFilterName = ? ",(filter_name, ))] [0][0]
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )             
            return

        self.cur.request("delete from FilterWizardItems where fkFilter = ?", (filter_key, ))
        for item, state in items.iteritems():
            if state != 0:
                self.cur.request("insert into FilterWizardItems(fkFilter, strItem, nState) values(?, ?, ?)", (filter_key, item, state))

        """
        if self.db_backend.lower() == 'mysql':
            self.cur.request("analyze table FilterWizard")
            self.cur.request("analyze table FilterWizardItems")
        else:
            self.cur.request("analyze")           
        """
        
        self.con.commit()
            
    def filterwizard_load_filter(self, filter_name):
        items = {}
        match_all = 0
        start_date = ''
        end_date = ''
        #
        try:
            rows = [row for row in self.cur.request( "select count(*) from FilterWizard where strFilterName = ? ",(filter_name, ))] [0][0]
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )             

        if rows > 0:
            filter_key, match_all, start_date, end_date = [row for row in self.cur.request( "select pkFilter, bMatchAll, StartDate, EndDate from FilterWizard where strFilterName = ? ",(filter_name, ))] [0]
            for state, item in self.cur.request( "select nState, strItem from FilterWizardItems where fkFilter = ?", (filter_key,)):
                items[item] = state

                
        return items, (True if match_all == 1 else False), ('' if start_date == None else start_date), ('' if end_date == None else end_date)
        
    def filterwizard_get_pics_from_filter(self, filter_name):
        (items, match_all, start_date, end_date) = self.filterwizard_load_filter(filter_name)
        set_tags = ""
        unset_tags = ""
        for key, value in items.iteritems():
            if value == 1:
                if len(set_tags)==0:
                    set_tags = key
                else:
                    set_tags += "|||" + key                        

            if value == -1:
                if len(unset_tags)==0:
                    unset_tags = key
                else:
                    unset_tags += "|||" + key    

        
        return self.filterwizard_result(set_tags, unset_tags, match_all, start_date, end_date)

        
        
        for item in items:
            print item
        
    ###################################
    # Collection functions
    #####################################
    def collections_list(self):
        """List all available collections"""
        return [row for row in self.cur.request( """SELECT CollectionName FROM Collections""")]
    
    
    def collection_new(self, colname):
        """Add a new collection"""       
        if colname :
            self.cur.request( "INSERT INTO Collections(CollectionName) VALUES (?) ",(colname, ))
            self.con.commit()
        else:
            common.log( "collection_new", "User did not specify a name for the collection.")
            
            
    def collection_delete(self, colname):      
        """delete a collection"""
        common.log( "collection_delete", "Name = %s"%colname)
        if colname:
            self.cur.request( """DELETE FROM FilesInCollections WHERE idCol=(SELECT idCol FROM Collections WHERE CollectionName=?)""", (colname,))
            self.cur.request( """DELETE FROM Collections WHERE CollectionName=? """,(colname,) )
            self.con.commit()
        else:
            common.log( "collection_delete",  "User did not specify a name for the collection" )
    
    
    def collection_get_pics(self, colname):      
        """List all pics associated to the Collection given as Colname"""
        return [row for row in self.cur.request( """SELECT strPath,strFilename FROM Files WHERE idFile IN (SELECT idFile FROM FilesInCollections WHERE idCol IN (SELECT idCol FROM Collections WHERE CollectionName=?)) ORDER BY ImageDateTime ASC""",(colname,))]
    
    
    def collection_rename(self, colname,newname):   
        """rename give collection"""
        if colname:
            self.cur.request( """UPDATE Collections SET CollectionName = ? WHERE CollectionName=? """, (newname, colname) )
            self.con.commit()
        else:
            common.log( "collection_rename",  "User did not specify a name for the collection")
    
    
    def collection_add_pic(self, colname, filepath, filename):    
    
        #cette requête ne vérifie pas si :
        #   1- le nom de la collection existe dans la table Collections
        #   2- si l'image est bien une image en base de donnée Files
        #ces points sont solutionnés partiellement car les champs ne peuvent être NULL
        #   3- l'association idCol et idFile peut apparaitre plusieurs fois...
        #print """(SELECT idFile FROM Files WHERE strPath="%s" AND strFilename="%s")"""%(filepath,filename)
        self.cur.request( """INSERT INTO FilesInCollections(idCol,idFile) VALUES ( (SELECT idCol FROM Collections WHERE CollectionName=?) , (SELECT idFile FROM Files WHERE strPath=? AND strFilename=?) )""",(colname,filepath,filename) )
        self.con.commit()
    
    
    def collection_del_pic(self, colname, filepath, filename):
        common.log("collection_del_pic","%s, %s, %s"%(colname, filepath, filename))
        self.cur.request( """DELETE FROM FilesInCollections WHERE idCol=(SELECT idCol FROM Collections WHERE CollectionName=?) AND idFile=(SELECT idFile FROM Files WHERE strPath=? AND strFilename=?)""",(colname, filepath, filename) )
        self.con.commit()
    
    
    ####################
    # Periodes functions
    #####################
    def periods_list(self):
        """List all Periodes"""
        return [row for row in self.cur.request( """SELECT PeriodeName,DateStart,DateEnd FROM Periodes""")]
    
    def period_add(self, periodname, datestart, dateend):
        if self.con.get_backend() == "mysql":
            datestart = "date_format('%s', '%%Y-%%m-%%d %%H:%%i:%%S')"%datestart
            dateend   = "date_format('%s', '%%Y-%%m-%%d %%H:%%i:%%S')"%dateend
            common.log("", "datestart = %s"%datestart)
            common.log("", "dateend   = %s"%dateend)
        else:
            datestart = "datetime('%s')"%datestart
            dateend   = "datetime('%s')"%dateend
            common.log("", "datestart = %s"%datestart)
            common.log("", "dateend   = %s"%dateend)

        insert = """INSERT INTO Periodes(PeriodeName,DateStart,DateEnd) VALUES (?,%s,%s)"""%(datestart,dateend)
        common.log("", insert)
        self.cur.request( insert, (periodname,) )
        self.con.commit()
        return
    
    def period_delete(self, periodname):
        self.cur.request( """DELETE FROM Periodes WHERE PeriodeName=? """,(periodname,) )
        self.con.commit()
        return
    
    def period_rename(self, periodname, newname, newdatestart, newdateend):
        if self.con.get_backend() == "mysql":
            self.cur.request( """UPDATE Periodes SET PeriodeName = ?,DateStart = date_format(?, '%%Y-%%m-%%d') , DateEnd = date_format(?, '%%Y-%%m-%%d') WHERE PeriodeName=? """,(newname,newdatestart,newdateend,periodname) )
        else:
            self.cur.request( """UPDATE Periodes SET PeriodeName = ?,DateStart = datetime(?) , DateEnd = datetime(?) WHERE PeriodeName=? """,(newname,newdatestart,newdateend,periodname) )
        self.con.commit()
        return
    
    def period_dates_get_pics(self, dbdatestart, dbdateend):
        if self.con.get_backend() == "mysql":
            return self.cur.request("SELECT date_format('%s', '%%Y-%%m-%%d'),date_format(date_format('%s', '%%Y-%%m-%%d') + INTERVAL 1 DAY - INTERVAL 1 SECOND, '%%Y-%%m-%%d')"%(dbdatestart,dbdateend))[0]    
        else:
            return self.cur.request("SELECT strftime('%%Y-%%m-%%d',('%s')),strftime('%%Y-%%m-%%d',datetime('%s','+1 days','-1.0 seconds'))"%(dbdatestart,dbdateend))[0]    


    def search_in_files(self, tag_type, tagvalue, count=False):
        val = tagvalue.lower().replace("'", "''")
    
        if self.con.get_backend() == 'mysql':
            val = val.replace("\\", "\\\\\\\\")


        if count:
            return [row for row in self.cur.request( """select count(*) from (select distinct fi.strFilename, fi.strPath
                                                          from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                                         where tt.idTagType = tc.idTagType
                                                           and tc.idTagContent = tif.idTagContent
                                                           and tt.TagTranslation = ?
                                                           and lower(tc.TagContent) LIKE '%%%s%%'
                                                           and tif.idFile = fi.idFile) a"""%val, (tag_type,))][0][0]
        else:
            return [row for row in self.cur.request( """select distinct fi.strPath, fi.strFilename
                                                          from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                                         where tt.idTagType = tc.idTagType
                                                           and tc.idTagContent = tif.idTagContent
                                                           and tt.TagTranslation = ?
                                                           and lower(tc.TagContent) LIKE '%%%s%%'
                                                           and tif.idFile = fi.idFile"""%val, (tag_type, ))]
    
    
    def get_gps(self, filepath, filename):
    
        latR = self.cur.request( """select tc.TagContent from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                    where tt.TagType = 'GPS GPSLatitudeRef'
                                      and tt.idTagType = tc.idTagType
                                      and tc.idTagContent = tif.idTagContent
                                      and tif.idFile = fi.idFile
                                      and fi.strPath = ?
                                      and fi.strFilename = ?""",  (filepath,filename) )
        lat = self.cur.request( """select tc.TagContent from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                    where tt.TagType = 'GPS GPSLatitude'
                                      and tt.idTagType = tc.idTagType
                                      and tc.idTagContent = tif.idTagContent
                                      and tif.idFile = fi.idFile
                                      and fi.strPath = ?
                                      and fi.strFilename = ?""",  (filepath,filename) )
        lonR = self.cur.request( """select tc.TagContent from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                    where tt.TagType = 'GPS GPSLongitudeRef'
                                      and tt.idTagType = tc.idTagType
                                      and tc.idTagContent = tif.idTagContent
                                      and tif.idFile = fi.idFile
                                      and fi.strPath = ?
                                      and fi.strFilename = ?""",  (filepath,filename) )
        lon = self.cur.request( """select tc.TagContent from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                                    where tt.TagType = 'GPS GPSLongitude'
                                      and tt.idTagType = tc.idTagType
                                      and tc.idTagContent = tif.idTagContent
                                      and tif.idFile = fi.idFile
                                      and fi.strPath = ?
                                      and fi.strFilename = ?""",  (filepath,filename) )
        try:
            latR=latR[0][0]
            lat=lat[0][0]
            lonR=lonR[0][0]
            lon=lon[0][0]
        except IndexError:
            return None
        if not latR or not lat or not lonR or not lon: 
            return None                            
    
        #tuplat = lat.replace(" ","").replace("[","").replace("]","").split(",")
        #tuplon = lon.replace(" ","").replace("[","").replace("]","").split(",")
        lD,lM,lS = lat.replace(" ","").replace("[","").replace("]","").split(",")[:3]
        LD,LM,LS = lon.replace(" ","").replace("[","").replace("]","").split(",")[:3]
        exec("lD=%s"%lD)
        exec("lM=%s"%lM)
        exec("lS=%s"%lS)
        exec("LD=%s"%LD)
        exec("LM=%s"%LM)
        exec("LS=%s"%LS)
        latitude =  (int(lD)+(int(lM)/60.0)+(int(lS)/3600.0)) * (latR=="S" and -1 or 1)
        longitude = (int(LD)+(int(LM)/60.0)+(int(LS)/3600.0)) * (lonR=="W" and -1 or 1)
        return (latitude,longitude)
    
    ######################################"
    #  Fonctions pour les dossiers racines
    ######################################"
    
    def get_all_root_folders(self):
        "return Folders which are root for scanning pictures"
        return [row for row in self.cur.request( """SELECT path,recursive,remove,exclude FROM Rootpaths ORDER BY path""")]
    
    def add_root_folder(self, path, recursive, remove, exclude):
        "add the path root inside the database. Recursive is 0/1 for recursive scan, remove is 0/1 for removing Files that are not physically in the place"
        self.cleanup_keywords()
        self.cur.request( """INSERT INTO Rootpaths(path,recursive,remove,exclude) VALUES (?,?,?,?)""",(common.smart_unicode(path),recursive,remove,exclude) )
        self.con.commit()
        common.log( "add_root_folder", "%s"%common.smart_utf8(path))
    
    def get_root_folders(self, path):
        common.log( "get_root_folders", "%s"%common.smart_utf8(path))
        #print common.smart_utf8(path)

        try:
            rows = [row for row in self.cur.request( """SELECT path,recursive,remove,exclude FROM Rootpaths WHERE path=? """, (common.smart_unicode(path),) )][0]
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            rows = []
        
        return rows
    
    
    def delete_root(self, path):
        "remove the given rootpath, remove pics from this path, ..."
        common.log( "delete_root", "name = %s"%common.smart_utf8(path))
        #first remove the path with all its pictures / subfolders / keywords / pictures in collections...
        self.delete_paths_from_root(path)
        #then remove the rootpath itself
        common.log( "delete_root",   """DELETE FROM Rootpaths WHERE path='%s' """%common.smart_utf8(path))
        self.cur.request( """DELETE FROM Rootpaths WHERE path=? """, (common.smart_unicode(path),) )
        self.con.commit()
    
    def delete_paths_from_root(self, path):
        "remove the given rootpath, remove pics from this path, ..."
        common.log( "delete_paths_from_root", "name = %s"%common.smart_utf8(path))
        cptremoved = 0
        try:
            idpath = self.cur.request( """SELECT idFolder FROM Folders WHERE FullPath = ?""",(common.smart_unicode(path),) )[0][0]
        except:
            common.log( "delete_paths_from_root",  "Path %s not found"%path)
            return 0
    
        try:
            cptremoved = self.cur.request( """SELECT count(*) FROM Files WHERE idFolder='%s'"""%idpath )[0][0]
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            return 0
            
        common.log( "delete_paths_from_root",  """DELETE FROM Files WHERE idFolder='%s'"""%idpath)
        self.cur.request( """DELETE FROM Files WHERE idFolder='%s'"""%idpath)

        for idchild in self.all_children_of_folder(idpath):

            self.cur.request( """DELETE FROM FilesInCollections WHERE idFile in (SELECT idFile FROM Files WHERE idFolder='%s')"""%idchild )
            try:
                cptremoved = cptremoved + self.cur.request( """SELECT count(*) FROM Files WHERE idFolder='%s'"""%idchild)[0][0]
            except Exception,msg:
                common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
                return 0

            self.cur.request( """DELETE FROM Files WHERE idFolder='%s'"""%idchild)
            common.log( "delete_paths_from_root",  """DELETE FROM Files WHERE idFolder='%s'"""%idchild)
            self.cur.request( """DELETE FROM Folders WHERE idFolder='%s'"""%idchild)
            common.log( "delete_paths_from_root",  """DELETE FROM Folders WHERE idFolder='%s'"""%idchild)

        common.log( "delete_paths_from_root",  """DELETE FROM Folders WHERE idFolder='%s'"""%idpath)
        self.cur.request( """DELETE FROM Folders WHERE idFolder='%s'"""%idpath)

        try:
            for periodname,datestart,dateend in self.periods_list():
                if self.cur.request( """SELECT count(*) FROM Files WHERE datetime(ImageDateTime) BETWEEN '%s' AND '%s'"""%(datestart,dateend) )[0][0]==0:
                    self.cur.request( """DELETE FROM Periodes WHERE PeriodeName='%s'"""%periodname )
            self.cleanup_keywords()
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )

        self.con.commit()
        return cptremoved


    def search_tag(self, tag=None,tag_type='a',limit=-1,offset=-1):
        """Look for given keyword and return the list of pictures.
    If tag is not given, pictures with no keywords are returned"""
        if tag is not None: 
            return [row for row in self.cur.request( "SELECT distinct strPath,strFilename FROM Files f, TagContents tc, TagsInFiles tif, TagTypes tt WHERE f.idFile = tif.idFile AND tif.idTagContent = tc.idTagContent AND tc.TagContent = ? and tc.idTagType = tt.idTagType  and length(trim(tt.TagTranslation))>0 and tt.TagTranslation = ?  order by imagedatetime ",(tag.encode("utf8"),tag_type.encode("utf8")) )]
        else: 
            return [row for row in self.cur.request( "SELECT distinct strPath,strFilename FROM Files WHERE idFile NOT IN (SELECT DISTINCT idFile FROM TagsInFiles) order by imagedatetime " )]
    
    
    def default_tagtypes_translation(self):
    
        """Return a list of all keywords in database """
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Country/primary location name'", (common.getstring(30700),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:Country'", (common.getstring(30700),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpExt:CountryName'", (common.getstring(30700),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Country/primary location code'", (common.getstring(30701),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpCore:CountryCode'", (common.getstring(30701),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpCore:Country'", (common.getstring(30701),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Province/state'", (common.getstring(30702),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:State'", (common.getstring(30702),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpExt:ProvinceState'", (common.getstring(30702),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Photoshop:City'", (common.getstring(30703),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpExt:City'", (common.getstring(30703),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'City'", (common.getstring(30703),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpCore:Location'", (common.getstring(30704),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpExt:Event'", (common.getstring(30705),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'DateAdded'", (common.getstring(30706),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF DateTimeOriginal'", (common.getstring(30707),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:DateCreated'", (common.getstring(30708),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Image DateTime'", (common.getstring(30708),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Caption/abstract'", (common.getstring(30709),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Dc:description'", (common.getstring(30709),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpCore:Description'", (common.getstring(30709),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpCore:Headline'", (common.getstring(30710),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:Headline'", (common.getstring(30710),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Headline'", (common.getstring(30710),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Object name'", (common.getstring(30711),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Dc:title'", (common.getstring(30711),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Iptc4xmpCore:Title'", (common.getstring(30711),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Writer/editor'", (common.getstring(30712),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'By-line'", (common.getstring(30712),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Dc:creator'", (common.getstring(30712),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'By-line title'", (common.getstring(30713),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Dc:rights'", (common.getstring(30714),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation = 'Copyright notice'", (common.getstring(30714),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Xmp:Label'", (common.getstring(30715),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Xmp:Rating'", (common.getstring(30716),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Xap:Rating'", (common.getstring(30716),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Image Rating'", (common.getstring(30716),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'MicrosoftPhoto:LastKeywordIPTC'", (common.getstring(30717),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'MicrosoftPhoto:LastKeywordXMP'", (common.getstring(30717),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Dc:subject'", (common.getstring(30717),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpCore:Keywords'", (common.getstring(30717),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Keywords'", (common.getstring(30717),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Category'", (common.getstring(30718),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:Category'", (common.getstring(30718),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Photoshop:SupplementalCategories'", (common.getstring(30719),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Supplemental category'", (common.getstring(30719),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'MPReg:PersonDisplayName'", (common.getstring(30720),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Iptc4xmpExt:PersonInImage'", (common.getstring(30720),))
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Mwg-rs:RegionList:Face'", (common.getstring(30720),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF ExifImageWidth'", (common.getstring(30721),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF ExifImageLength'", (common.getstring(30722),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF SceneCaptureType'", (common.getstring(30723),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'EXIF Flash'", (common.getstring(30724),))
    
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Image Model'", (common.getstring(30725),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Image Make'", (common.getstring(30726),))
        
        self.cur.request("update TagTypes set TagTranslation = ? where TagTranslation =  'Image Artist'", (common.getstring(30727),))
    
        # default to not visible
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'EXIF DateTimeDigitized'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'EXIF DigitalZoomRatio'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'EXIF ExifVersion'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'EXIF FileSource'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Image Orientation'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Image ResolutionUnit'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Image XResolution'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Image YResolution'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'GPS GPSLatitude'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'GPS GPSLatitudeRef'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'GPS GPSLongitude'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'GPS GPSLongitudeRef'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Original transmission reference'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Photoshop:CaptionWriter'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Photoshop:Instructions'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Special instructions'")    
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Credit'")    
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Sub-location'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'Ftype'")
        self.cur.request("update TagTypes set TagTranslation = '' where TagTranslation =  'StrPath'")
        
        if self.con.get_backend() == 'mysql':
            self.cur.request("ANALYZE TABLE Files")
            self.cur.request("ANALYZE TABLE FilesInCollections")
            self.cur.request("ANALYZE TABLE Collections")
            self.cur.request("ANALYZE TABLE Periods")
            self.cur.request("ANALYZE TABLE Folders")
            self.cur.request("ANALYZE TABLE Rootpaths")
            self.cur.request("ANALYZE TABLE TagTypes")
            self.cur.request("ANALYZE TABLE TagContents")
            self.cur.request("ANALYZE TABLE TagsInFiles")
        else:
            self.cur.request("vacuum")
            self.cur.request("analyze")
        self.con.commit()
        
    def list_TagTypes(self):
    
        return [row for (row,) in self.cur.request( """SELECT distinct tt.TagTranslation FROM TagTypes tt, TagContents tc, TagsInFiles tif 
    where length(trim(TagTranslation))>0 
    and tt.idTagType = tc.idTagType
    and tc.idTagContent = tif.idTagContent
    ORDER BY TagTranslation ASC""" )]
    
    def list_tagtypes_count(self):
    
        return [row for row in self.cur.request( """
    SELECT tt.TagTranslation, count(distinct tagcontent)
      FROM TagTypes tt, TagContents tc, TagsInFiles tf 
     where length(trim(TagTranslation)) > 0 
       and tf.idTagContent              = tc.idTagContent
       and tt.idTagType                 = tc.idTagType
    group by tt.tagtranslation """   )]
    
    def count_tagtypes(self, tagType, limit=-1, offset=-1):
        try:
            if tagType is not None:
                return self.cur.request("""SELECT count(distinct TagContent) FROM tagsInFiles tif, TagContents tc, TagTypes tt WHERE tif.idTagContent = tc.idTagContent AND tc.idTagType = tt.idTagType and length(trim(tt.TagTranslation))>0 and tt.idTagType =? """, (tagType,) )[0][0]
            else:
                return self.cur.request("""SELECT count(*) FROM TagTypes where length(trim(TagTranslation))>0""" )[0][0]
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            return 0
            
    def set_tagtype_translation(self, TagType, TagTranslation):
        self.cur.request("Update TagTypes set TagTranslation = ? where TagType = ? ",(TagTranslation.encode('utf-8'), TagType.encode('utf-8')))
        self.con.commit()
        
    def get_tagtypes_translation(self):
        return [row for row in self.cur.request('select TagType, TagTranslation from TagTypes order by 2,1')]
    
    def list_tags(self,tagType):
        """Return a list of all tags in database"""
        return [row for (row,) in self.cur.request( """select distinct TagContent from TagContents tc, TagsInFiles tif, TagTypes tt  where tc.idTagContent = tif.idTagContent and tc.idTagType = tt.idTagType and tt.TagTranslation='%s' ORDER BY LOWER(TagContent) ASC"""%tagType.encode("utf8") )]
    
    def list_tags_count(self, tagType):
        """Return a list of all tags in database"""
        return [row for row in self.cur.request( """
        select TagContent, count(distinct idFile) 
      from TagContents tc, TagsInFiles tif, TagTypes tt  
     where tc.idTagContent = tif.idTagContent
       and tc.idTagType = tt.idTagType 
       and tt.TagTranslation = ? 
    group BY TagContent""",(tagType.encode("utf8"),) )]
    
    def count_tags(self, kw, tagType, limit=-1, offset=-1):
        try:
            if kw is not None:
                return self.cur.request("""select count(distinct idFile) from  TagContents tc, TagsInFiles tif, TagTypes tt  where tc.idTagContent = tif.idTagContent and tc.TagContent = ? and tc.idTagType = tt.idTagType and tt.TagTranslation = ? """,(kw, tagType))[0][0]
            else:
                return self.cur.request("""SELECT count(*) FROM Files WHERE idFile not in (SELECT DISTINCT idFile FROM TagsInFiles)""" )[0][0]
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            return 0
    
    def count_pics_in_folder(self,folderid):
        # new part
        count = 0
        try:
        
            #folderPath    = self.cur.request("""Select FullPath from Folders where idFolder = ?""", (folderid,))[0][0]
            #parent_folder = self.cur.request("""Select ParentFolder from Folders where idFolder = ?""", (folderid,))[0][0]
            
            row = self.cur.request("""Select FullPath, ParentFolder from Folders where idFolder = ?""", (folderid,))
            folderPath = row[0][0]
            parent_folder = row[0][1]
            
            common.log("", "folderid = %s"%folderid)
            common.log("", "folderPath = %s"%folderPath)
            common.log("", "parent_folder = %s"%parent_folder)
            
            # mask the apostrophe
            folderPath = folderPath.replace("'", "''")
                
            if self.con.get_backend() == 'mysql':
                folderPath = folderPath.replace("\\", "\\\\\\\\")            
            
            if parent_folder:
                if self.con.get_backend() == 'mysql':
                    count = self.cur.request("""select count(*) from Files f, Folders p where f.idFolder=p.idFolder and (p.FullPath like '%s' or p.FullPath like '%s%%' or p.FullPath like '%s%%')"""%(folderPath, folderPath + '/', folderPath + '\\\\\\\\'))[0][0]
                else:
                    count = self.cur.request("""select count(*) from Files f, Folders p where f.idFolder=p.idFolder and (p.FullPath = '%s' or p.FullPath like '%s%%' or p.FullPath like '%s%%')"""%(folderPath, folderPath + '/', folderPath + '\\'))[0][0]
            else:
                count = self.cur.request("""select count(*) from Files f, Folders p where f.idFolder=p.idFolder and p.FullPath like '%s%%'"""%(folderPath))[0][0]            
            
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
        
        return count
    
        # old part
    
        children = self.all_children_of_folder(folderid)
    
        cpt = self.cur.request("SELECT count(*) FROM Files f,Folders p WHERE f.idFolder=p.idFolder AND f.idFolder='%s'"%folderid)[0][0]
        for idchild in children:
            cpt = cpt + self.cur.request("SELECT count(*) FROM Files f,Folders p WHERE f.idFolder=p.idFolder AND f.idFolder='%s'"%idchild)[0][0]
        return cpt#Request("SELECT count(*) FROM Files f,Folders p WHERE f.idFolder=p.idFolder AND f.idFolder='%s'"%folderid)[0][0]
    
    def count_pics_in_period(self, period, value):
        #   lister les images pour une date donnée
        formatstring = {"year":"%Y","month":"%Y-%m","date":"%Y-%m-%d","":"%Y"}[period]
        if period=="year" or period=="":
            if value:
                #filelist = search_between_dates( (value,formatstring) , ( str( int(value) +1 ),formatstring) )
                filelist = self.pics_for_period('year',value)
            else:
                filelist = self.search_all_dates()

        elif period in ["month","date"]:
            filelist = self.pics_for_period(period,value)

        else:
            #pas de periode, alors toutes les photos du 01/01 de la plus petite année, au 31/12 de la plus grande année
            listyears=self.get_years()
            amini=min(listyears)
            amaxi=max(listyears)
            if amini and amaxi:
                filelist = self.search_between_dates( ("%s"%(amini),formatstring) , ( "%s"%(amaxi),formatstring) )
            else:
                filelist = []
        return len(filelist)


    """
    def list_cam_models():
        return [row for (row,) in self.cur.request('SELECT DISTINCT "Image Model" FROM Files WHERE "Image Model" NOT NULL')]
    """


    def list_path(self):
        """retourne la liste des chemins en base de données"""
        return [row for (row,) in self.cur.request( """SELECT DISTINCT strPath FROM Files""" )]


    def all_children_of_folder(self, rootid):
        """liste les id des dossiers enfants"""
        #A REVOIR : Ne fonctionne pas correctement !
        enfants=[]
        childrens=[rootid]
        #continu = False
        while True:
            try:
                chid = childrens.pop(0)
            except:
                #fin
                break
            chlist = [row for (row,) in self.cur.request( """SELECT idFolder FROM Folders WHERE ParentFolder='%s'"""%chid )]#2,10,17
            childrens=childrens+chlist
            enfants=enfants+chlist
    
        return enfants


    def search_between_dates(self, DateStart=("2007","%Y"),DateEnd=("2008","%Y")):
        """Cherche les photos qui ont été prises entre 'datestart' et 'dateend'."""
        common.log( "search_between_dates", DateStart)
        common.log( "search_between_dates", DateEnd)
        DS = strftime("%Y-%m-%d %H:%M:%S",strptime(DateStart[0],DateStart[1]))
        DE = strftime("%Y-%m-%d %H:%M:%S",strptime(DateEnd[0],DateEnd[1]))
        if self.con.get_backend() == "mysql":
            if DateEnd[1]=="%Y-%m-%d":
                Emodifier = "date_format(date_format('%s', '%%Y-%%m-%%d') + INTERVAL 1 DAY - INTERVAL 1 MINUTE, '%%Y-%%m-%%d %%H:%%i:%%S')"%DateEnd[0]
                Smodifier = "date_format('%s', '%%Y-%%m-%%d')"%DateStart[0]
            elif DateEnd[1]=="%Y-%m":
                Emodifier = "date_format(date_format('%s-01', '%%Y-%%m-%%d') + INTERVAL 1 MONTH - INTERVAL 1 MINUTE, '%%Y-%%m-%%d %%H:%%i:%%S')"%DateEnd[0]
                Smodifier = "date_format('%s-01', '%%Y-%%m%%d')"%DateStart[0]
            elif DateEnd[1]=="%Y":
                Emodifier = "date_format(date_format('%s-01-01', '%%Y-%%m-%%d') + INTERVAL 1 YEAR - INTERVAL 1 MINUTE, '%%Y-%%m-%%d %%H:%%i:%%S')"%DateEnd[0]
                Smodifier = "date_format('%s-01-01', '%%Y-%%m-%%d')"%DateStart[0]
            else:
                Emodifier = "''"
                Smodifier = "''"
        
            request = """SELECT strPath,strFilename FROM Files WHERE ImageDateTime BETWEEN %s AND %s ORDER BY ImageDateTime ASC"""%(Smodifier, Emodifier)
        else:
            if DateEnd[1]=="%Y-%m-%d":
                Emodifier = "'start of day','+1 days','-1 minutes'"
                Smodifier = "'start of day'"
            elif DateEnd[1]=="%Y-%m":
                Emodifier = "'start of month','+1 months','-1 minutes'"
                Smodifier = "'start of month'"
            elif DateEnd[1]=="%Y":
                Emodifier = "'start of year','+1 years',-1 minutes'"
                Smodifier = "'start of year'"
            else:
                Emodifier = "''"
                Smodifier = "''"
        
            request = """SELECT strPath,strFilename FROM Files WHERE datetime(ImageDateTime) BETWEEN datetime('%s',%s) AND datetime('%s',%s) ORDER BY ImageDateTime ASC"""%(DS,Smodifier,DE,Emodifier)
        return [row for row in self.cur.request(request)]

        
    def del_pics_wo_sha(self, is_cancelled):
        count = 0
        if is_cancelled == False:
            count = [row for row in self.cur.request("select count(*) from Files where Sha is null")][0][0]
            self.cur.request("delete from Files where Sha is null");
        return count

    def pics_for_period(self, periodtype, date):
        if self.con.get_backend() == "mysql":
            try:
                sdate,edate = {'year' :["date_format('%s-01-01', '%%Y-%%m-%%d')"%date,"date_format(date_format('%s-01-01', '%%Y-%%m-%%d') + INTERVAL 1 YEAR - INTERVAL 1 MINUTE, '%%Y-%%m-%%d %%H:%%i:%%S')"%date],
                               'month':["date_format('%s-01', '%%Y-%%m-%%d')"%date,"date_format(date_format('%s-01', '%%Y-%%m-%%d') + INTERVAL 1 MONTH - INTERVAL 1 MINUTE, '%%Y-%%m-%%d %%H:%%i:%%S')"%date],
                               'date' :["date_format('%s', '%%Y-%%m-%%d')"%date,"date_format(date_format('%s', '%%Y-%%m-%%d') + INTERVAL 1 DAY - INTERVAL 1 MINUTE, '%%Y-%%m-%%d %%H:%%i:%%S')"%date]}[periodtype]
            except:
                print_exc()
                #log ("pics_for_period ( periodtype = ['date'|'month'|'year'] , date = corresponding to the period (year|year-month|year-month-day)")
            request = """SELECT strPath,strFilename FROM Files WHERE ImageDateTime BETWEEN %s AND %s ORDER BY ImageDateTime ASC"""%(sdate,edate)
        else:
            try:
                sdate,modif1,modif2 = {'year' :['%s-01-01'%date,'start of year','+1 years'],
                                       'month':['%s-01'%date,'start of month','+1 months'],
                                       'date' :['%s'%date,'start of day','+1 days']}[periodtype]
            except:
                print_exc()
                #log ("pics_for_period ( periodtype = ['date'|'month'|'year'] , date = corresponding to the period (year|year-month|year-month-day)")
            request = """SELECT strPath,strFilename FROM Files WHERE datetime(ImageDateTime) BETWEEN datetime('%s','%s') AND datetime('%s','%s','%s') ORDER BY ImageDateTime ASC;"""%(sdate,modif1,sdate,modif1,modif2)
        return [row for row in self.cur.request(request)]


    def get_years(self):
        if self.con.get_backend() == "mysql":    
            return [t for (t,) in self.cur.request("""SELECT DISTINCT date_format(ImageDateTime, '%Y') FROM Files where ImageDateTime is NOT NULL ORDER BY ImageDateTime ASC""")]
        else:
            return [t for (t,) in self.cur.request("""SELECT DISTINCT strftime("%Y",ImageDateTime) FROM Files where ImageDateTime NOT NULL ORDER BY ImageDateTime ASC""")]


    def get_months(self, year):
        if self.con.get_backend() == "mysql":    
            return [t for (t,) in self.cur.request("""SELECT distinct date_format(ImageDateTime, '%%Y-%%m') FROM Files where date_format(ImageDateTime, '%%Y') = '%s' ORDER BY ImageDateTime ASC"""%year)]
        else:
            return [t for (t,) in self.cur.request("""SELECT distinct strftime("%%Y-%%m",ImageDateTime) FROM Files where strftime("%%Y",ImageDateTime) = '%s' ORDER BY ImageDateTime ASC"""%year)]


    def get_dates(self, year_month):
        if self.con.get_backend() == "mysql":    
            return [t for (t,) in self.cur.request("""SELECT distinct date_format(ImageDateTime, '%%Y-%%m-%%d') FROM Files where date_format(ImageDateTime, '%%Y-%%m') = '%s' ORDER BY ImageDateTime ASC"""%year_month)]
        else:
            return [t for (t,) in self.cur.request("""SELECT distinct strftime("%%Y-%%m-%%d",ImageDateTime) FROM Files where strftime("%%Y-%%m",ImageDateTime) = '%s' ORDER BY ImageDateTime ASC"""%year_month)]


    def search_all_dates(self):# TODO check if it is really usefull (check 'get_pics_dates' to see if it is not the same)
        """return all Files from database sorted by 'EXIF DateTimeOriginal' """
        return [t for t in self.cur.request("""SELECT strPath,strFilename FROM Files ORDER BY ImageDateTime ASC""")]


    def get_pics_dates(self):
        """return all different dates from 'EXIF DateTimeOriginal'"""
        if self.con.get_backend() == "mysql":
            return [t for (t,) in self.cur.request("""SELECT DISTINCT date_format(ImageDateTime, '%Y-%m-%d') FROM Files WHERE length(trim(ImageDateTime))>8  ORDER BY ImageDateTime ASC""")]
        else:
            return [t for (t,) in self.cur.request("""SELECT DISTINCT strftime("%Y-%m-%d",ImageDateTime) FROM Files WHERE length(trim(ImageDateTime))>8  ORDER BY ImageDateTime ASC""")]


    def get_pic_date(self, path, filename):
        try:
            (rows, ) = [row for (row,) in self.cur.request( "SELECT ImageDateTime FROM Files WHERE strPath=? AND strFilename=? ",(path,filename) )]

            return str(rows)
        except Exception,msg:
            common.log("",  "%s - %s"%(Exception,msg), xbmc.LOGERROR )
            return None


if __name__=="__main__":
    pass

