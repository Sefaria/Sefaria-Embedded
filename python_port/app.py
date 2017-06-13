"""An embed server for Sefaria.org"""
import sys
from threading import Thread
from urlparse import urljoin
from time import time

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from flask import Flask
from flask import render_template

from constants import *
import requests


#Database
engine = create_engine('sqlite:///test.db', echo=False)
Session = sessionmaker(bind=engine)
# Or do:
# Session = sessionmaker()
# Session.configure(bind=engine)  # once engine is available

session = Session()

Base = declarative_base()
Base.metadata.create_all(engine)

class SefariaResource(Base):
    __tablename__ = 'sefaria_resources'
    id = Column(Integer, primary_key=True)
    HebrewText = Column(String)
    EnglishText = Column(String)
    HebrewSectionReference = Column(String)
    EnglishSectionReference = Column(String)

# Web App
app = Flask(__name__)

@app.route("/<resource>")
def root(resource):
    """Returns the embed page for a given Sefaria resource"""
    try:
        # result = get_resource(resource)
        # return result
        return "Hello"
    except:
        e = sys.exc_info()[0]
        print e
        return "There was an Error" 
    # result["defaultLanguageCode"] = "he"
    # result["originalURLPath"] = resource
    # return render_template("embed.j2", ob=result)


def get_resource(resource_name):
    """Looks for the Sefaria resource locally, otherwise fetches it from the api"""
    #Check if it exists locally
    # result = local_get_resource("fake_resource")

    # return result

    #If it does not exist locally, get it from the api
    result = fetch_resource(resource_name)
    return result

# Remote resource function
def fetch_resource(resource_name):
    """Issues a GET request to fetch resource and returns dictionary of the relevant data"""
    # url = urljoin(SEFARIA_API_NODE, resource_name)
    print resource_name
    # response = requests.get(url)
    # response = requests.get(urljoin(SEFARIA_API_NODE, resource_name))
    # response.encoding = "UTF-8"
    # full_json = response.json()

    # Parse the relevant parts of the json
    parsed_response = {}
    # parsed_response["HebrewText"] = full_json["he"]
    # parsed_response["EnglishText"] = full_json["text"]
    # parsed_response["HebrewSectionReference"] = full_json["heSectionRef"]
    # parsed_response["EnglishSectionReference"] = full_json["sectionRef"]

    return parsed_response

def local_get_resource(resource_hebrew_section_reference):
    print resource_hebrew_section_reference
    resource = session.query(SefariaResource).filter_by(HebrewSectionReference=resource_hebrew_section_reference).first()
    print "Resource: "+ resource
    return resource
def local_add_resource(resource_dict):
    resource = SefariaResource(
        HebrewText=resource_dict["HebrewText"],
        EnglishText=resource_dict["EnglishText"],
        HebrewSectionReference=resource_dict["HebrewSectionReference"],
        EnglishSectionReference=resource_dict["EnglishSectionReference"])

    session.add(resource)
    session.commit()
    # HebrewText = Column(String)
    # EnglishText = Column(String)
    # HebrewSectionReference = Column(String)
    # EnglishSectionReference = Column(String)

if __name__ == "__main__":
    app.run(port=3017)
