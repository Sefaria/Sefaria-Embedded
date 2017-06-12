"""An embed server for Sefaria.org"""
from threading import Thread
from urlparse import urljoin
from time import time
import persistent
from BTrees.OOBTree import BTree

import ZODB
import ZODB.FileStorage
from flask import Flask
from flask import render_template

from constants import *
import requests

#Database
storage = ZODB.FileStorage.FileStorage('data.fs')
db = ZODB.DB(storage)

def init_db():
    """Makes sure the database is in the proper state"""
    with db.transaction() as conn:
        dbroot = conn.root()
        if "resources" in dbroot:
            return
        else:
            dbroot["resources"] = {}
        return

init_db()

# Web App
app = Flask(__name__)

@app.route("/<resource>")
def root(resource):
    """Returns the embed page for a given Sefaria resource"""
    result = get_resource(resource)

    result["defaultLanguageCode"] = "he"
    result["originalURLPath"] = resource
    return render_template("embed.j2", ob=result)


def get_resource(resource_name):
    """Looks for the Sefaria resource locally, otherwise fetches it from the api"""
    #Check if it exists locally
    with db.transaction() as conn:
        dbroot = conn.root()
        if resource_name in dbroot["resources"]:
            result = dbroot["resources"][resource_name]
            print "Found result locally\t" + result["HebrewSectionReference"]
            
            # Update the last-touched timestamp to prevent it being cleared from the cache
            result["last_touched"] = time()
            return result

    #If it does not exist locally, get it from the api
    result = fetch_resource(resource_name)
    return result

# Remote resource function
def fetch_resource(resource_name):
    """Issues a GET request to fetch resource and returns dictionary of the relevant data"""
    response = requests.get(urljoin(SEFARIA_API_NODE, resource_name))
    full_json = response.json()

    # Parse the relevant parts of the json
    parsed_response = {}
    parsed_response["HebrewText"] = full_json["he"]
    parsed_response["EnglishText"] = full_json["text"]
    parsed_response["HebrewSectionReference"] = full_json["heSectionRef"]
    parsed_response["EnglishSectionReference"] = full_json["sectionRef"]
    parsed_response["last_touched"] = time()

    print "Found result remotely\t" + parsed_response["HebrewSectionReference"]

    # Save it locally for the future
    with db.transaction() as conn:
        dbroot = conn.root()
        dbroot["resources"][resource_name] = parsed_response

    return parsed_response

class Resources(persistent.Persistent):
    def __init__(self):
        self.resources = BTree()
    
    def addResource(self, resource_name, resource):
        self.resources.insert(resource_name, resource)

if __name__ == "__main__":
    app.run(port=3017)
