"""An embed server for Sefaria.org"""

from urlparse import urljoin

from flask import Flask
from flask import render_template

from constants import *
import requests


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
    #If it does not exist locally, get it from the api
    manager = RemoteResourceManager(resource_name)
    result = manager.fetch_resource()
    return result

class RemoteResourceManager:
    """Deals with fetching Sefaria resource from api"""
    def __init__(self, resource_name):
        self.resource_name = resource_name

    def fetch_resource(self):
        """Issues a GET request to fetch resource and returns dictionary of the relevant data"""
        response = requests.get(urljoin(SEFARIA_API_NODE, self.resource_name))
        return self.__parse_raw_remote_resource(response.json())

    def __parse_raw_remote_resource(self, resource):
        parsed_response = {}
        parsed_response["HebrewText"] = resource["he"]
        parsed_response["EnglishText"] = resource["text"]
        parsed_response["HebrewSectionReference"] = resource["heSectionRef"]
        parsed_response["EnglishSectionReference"] = resource["sectionRef"]
        return parsed_response


def getResourceFromStore(resource):
    pass

def saveResource(resource):
    pass


if __name__ == "__main__":
    app.run(port=3017)
