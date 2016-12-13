import argparse
import csv
from datetime import datetime
from apiclient.http import MediaIoBaseDownload
from apiclient.discovery import build
from oauth2client import client
from oauth2client.file import Storage
from oauth2client import tools
from collections import OrderedDict
import httplib2
import os
import io
import json

try:
    import argparse
    flags, uk = argparse.ArgumentParser(parents=[tools.argparser]).parse_known_args()
except ImportError:
    flags = None

# Auth Google Stuff
credentialFile = 'gd_cs148.json'
credentialStore = Storage(credentialFile)
credentials = credentialStore.get()

if not credentials or credentials.invalid:
    flow = client.flow_from_clientsecrets('gd_cs148_secrets.json', 'https://www.googleapis.com/auth/drive')
    flow.user_agent = 'cs148-final'
    credentials = tools.run_flow(flow, credentialStore, flags)
   
http = credentials.authorize(httplib2.Http())
# Setup Google stuff
service = build('drive', 'v3', http=http)

class StudentId:
    def __init__(self, name, sunet):
        self.name = name.strip()
        self.sunet = sunet.strip()

    def __str__(self):
        return "(Student: " + self.name + " // " + self.sunet + ")"

    def __repr__(self):
        return self.__str__()

class StudentGroup:
    def __init__(self):
        self.ids = []

    def AddStudent(self, student):
        self.ids.append(student)

    def UniqueId(self):
        # Create unique ID from sorted SUNetIDs
        sunets = []
        for id in self.ids:
            sunets.append(id.sunet)
        sunets.sort()
        return "-".join(sunets)
    
    def Size(self):
        return len(self.ids)

    def __str__(self):
        return str(self.ids)

    def __repr__(self):
        return self.__str__()

class Entry:
    def __init__(self, csvText, entryId):
        self.group = StudentGroup()
        self.timestamp = datetime.now()
        self.mainImageId = ""
        self.imageVarAId = ""
        self.imageVarBId = ""
        self.writeupId = ""
        self.entryId = entryId
        self.mainFilename = ""
        self.__parse(csvText)

    def __parse(self, csvText):
        # Item 0 -- Date time
        self.timestamp = datetime.strptime(csvText[0], "%m/%d/%Y %H:%M:%S")

        # Item 1 -- Names
        # Item 2 -- SUNetIds
        names = csvText[1].split(',')
        sunets = csvText[2].split(',')
        for i in range(0, len(names)):
            self.group.AddStudent(StudentId(names[i], sunets[i]))

        # Item 3 -- Image Drive URL
        self.mainImageId = csvText[3].split('id=')[1]

        # Item 4 -- Writeup Drive URL
        self.writeupId = csvText[4].split('id=')[1]

        # Item 5 -- Email (Ignore)

        # Item 6 -- Variant A Drive URL
        self.imageVarAId = csvText[6].split('id=')[1]

        # Item 7 -- Variant B Drive URL
        self.imageVarBId = csvText[7].split('id=')[1]

    def __str__(self):
        return "(Entry for: " + str(self.group) + " at " + str(self.timestamp) + " -- " + str(self.entryId) + ")"

    def __repr__(self):
        return self.__str__()

    def GroupId(self):
        return self.group.UniqueId()

def DownloadGDriveData(gId, userFolder, prefix):
    metadata = service.files().get(fileId=gId).execute()
    if not metadata:
        raise Exception('Failed to get meta data for ' + str(gId))
    
    fileType = metadata['mimeType']
    filename = userFolder + "/" + prefix + "_" + metadata['name'].replace(" ", "")

    # do not redownload
    if os.path.exists(filename):
        return filename

    with open(filename, 'wb') as fh:
        request = service.files().get_media(fileId=gId)
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print("Download (" + metadata['name'] + ") Percent: " + str(int(status.progress() * 100)) + "%")

    return filename

def DownloadAllData(entries, dataFolder):
    for key, entry in entries.items():
        userDirectory = dataFolder + "/" + key
        if not os.path.exists(userDirectory):
            os.makedirs(userDirectory)
        entry.mainFilename = DownloadGDriveData(entry.mainImageId, userDirectory, "main")
        DownloadGDriveData(entry.imageVarAId, userDirectory, "image_A")
        DownloadGDriveData(entry.imageVarBId, userDirectory, "image_B")
        DownloadGDriveData(entry.writeupId, userDirectory, "writeup")

def GeneratePresentation(entries, dataFolder, presentationFilename):
    templateFilename = "latex/template.tex"
    entryTemplateFilename = "latex/entry-template.tex"

    presentationTemplate = ""
    with open(templateFilename, 'r') as tf:
        presentationTemplate = tf.read()

    entryTemplate = ""
    with open(entryTemplateFilename, 'r') as etf:
        entryTemplate = etf.read()

    # create entries
    entryText = ""
    for key, entry in entries.items():
        newEntryText = entryTemplate
        newEntryText = newEntryText.replace("$EID$", str(entry.entryId))
        newEntryText = newEntryText.replace("$NAME1$", entry.group.ids[0].name)
        newEntryText = newEntryText.replace("$SUNET1$", entry.group.ids[0].sunet)
        if entry.group.Size() > 1:
            newEntryText = newEntryText.replace("$NAME2$", entry.group.ids[1].name)
            newEntryText = newEntryText.replace("$SUNET2$", entry.group.ids[1].sunet)
        else:
            newEntryText = newEntryText.replace("$NAME2$", "NA")
            newEntryText = newEntryText.replace("$SUNET2$", "NA")
        newEntryText = newEntryText.replace("$IMAGEPATH$", entry.mainFilename)
        newEntryText = newEntryText.replace("$WRITEUPURL$", "http://drive.google.com/open?id="+entry.writeupId)
        newEntryText = newEntryText.replace("$MAINURL$", "http://drive.google.com/open?id="+entry.mainImageId)
        newEntryText = newEntryText.replace("$VARAURL$", "http://drive.google.com/open?id="+entry.imageVarAId)
        newEntryText = newEntryText.replace("$VARBURL$", "http://drive.google.com/open?id="+entry.imageVarBId)
        newEntryText += "\n"
        entryText += newEntryText

    finalPresentationText = presentationTemplate.replace("$SLIDES$", entryText)

    with open(presentationFilename, 'w') as fh:
        fh.write(finalPresentationText)

def GenerateEntryIdMapping(entries, mappingFilename):
    with open(mappingFilename, 'w') as fh:
        data = {}
        for k, v in entries.items():
            data[str(v.entryId)] = k
        fh.write(json.dumps(data, indent=4))

def GenerateGradingTable(entries, tableFilename):
    with open(tableFilename, 'w') as fh:
        csvWriter = csv.writer(fh, delimiter=',')
        csvWriter.writerow(['Entry ID (EID)', 'SUNetID 1', 'SUNetID 2', 'David', 'Hanna', 'Mike', 'Shannon', 'Wenlong', 'Winnie', 'Yue'])
        for k, v in entries.items():
            sunet2 = ""
            if v.group.Size() > 1:
                sunet2 = v.group.ids[1].sunet
            csvWriter.writerow([str(v.entryId), v.group.ids[0].sunet, sunet2, "", "", "", "", "", "", ""])

def Parse(csvFilename):
    # Load entries from CSV file and overwrite duplicates based on SUNetId
    # Assume data is sorted by time.
    entries = OrderedDict()
    with open(csvFilename) as csvFile:
        csvReader = csv.reader(csvFile, delimiter = ',')
        lineCount = 0
        for row in csvReader:
            lineCount += 1
            if lineCount == 1:
                continue
            entry = Entry(row, lineCount)
            reorder = entry.GroupId() in entries
            entries[entry.GroupId()] = entry
            if reorder:
                entries.move_to_end(entry.GroupId())

    # Download data into a folder.
    DownloadAllData(entries, 'data')

    # Use entries and downloaded data to create a presentation
    GeneratePresentation(entries, 'data', 'cs148_final_projects.tex')

    # Create and dump mapping
    GenerateEntryIdMapping(entries, 'mapping.json')

    # Create and dump for table grading (import into Excel)
    GenerateGradingTable(entries, 'grading.csv')

if __name__ == "__main__": 
    cmdParser = argparse.ArgumentParser(description='Parser')
    cmdParser.add_argument('--csv', required=True)
    args = cmdParser.parse_args()
    Parse(args.csv) 
