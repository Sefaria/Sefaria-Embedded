"""An embed server for Sefaria.org"""
import sys
import time
from threading import Thread
from urlparse import urljoin
from threading import Thread
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from flask import Flask, render_template, request

from constants import *
import requests


#Database
engine = create_engine('sqlite:///test.db', echo=False)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
# Or do:
# Session = sessionmaker()
# Session.configure(bind=engine)  # once engine is available

session = Session()

Base = declarative_base()

class SefariaResource(Base):
    __tablename__ = 'sefaria_resources'
    id = Column(Integer, primary_key=True)
    HebrewSectionReference = Column(String)
    EnglishSectionReference = Column(String)
    resource_name = Column(String)
    seen_count = Column(Integer, default=1)
    created_timestamp = Column(DateTime, server_default=func.now())
    last_seen_timestamp = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ResourceTextSection(Base):
    __tablename__ = 'resource_text_arrays'
    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey("sefaria_resources.id"), nullable=False)
    language_code = Column(String)
    text_index = Column(Integer) 
    text = Column(String)

Base.metadata.create_all(engine)
# session.commit()

# Web App
app = Flask(__name__)

@app.route("/<resource>")
def root(resource):
    """Returns the embed page for a given Sefaria resource"""
    result = get_resource(resource)
    render_obj = {}

    lang = request.args.get('lang')
    if lang == 'he':
        render_obj["defaultLanguageCode"] = "he"
        render_obj["meta_description"] = get_first_50_characters(result["HebrewText"])
    elif lang == 'en':
        render_obj["defaultLanguageCode"] = "en"
        render_obj["meta_description"] = get_first_50_characters(result["EnglishText"])
    else:
        render_obj["defaultLanguageCode"] = "en"
        render_obj["meta_description"] = get_first_50_characters(result["EnglishText"])

    render_obj["originalURLPath"] = resource
    render_obj["data"] = result

    return render_template("embed.j2", ob=render_obj)


# render_obj["error_code"] = 500
# render_obj["error_message"] = result
# return render_template("error.j2", ob=render_obj)

def get_resource(resource_name):
    """Looks for the Sefaria resource locally, otherwise fetches it from the api"""
    #Check if it exists locally
    result = local_get_resource(resource_name)

    if result is None:  #If it does not exist locally, get it from the api
        print "Result not found locally. Fetching from API..."
        result = remote_get_resource(resource_name)

    return result

# Remote resource function
def remote_get_resource(resource_name):
    """Issues a GET request to fetch resource and returns dictionary of the relevant data"""
    url = urljoin(SEFARIA_API_NODE, resource_name)

    response = requests.get(url)
    response = requests.get(urljoin(SEFARIA_API_NODE, resource_name))
    response.encoding = "UTF-8"
    full_json = response.json()

    # Parse the relevant parts of the json
    parsed_response = {}
    parsed_response["HebrewText"] = full_json["he"]
    parsed_response["EnglishText"] = full_json["text"]
    parsed_response["HebrewSectionReference"] = full_json["heSectionRef"]
    parsed_response["EnglishSectionReference"] = full_json["sectionRef"]
    parsed_response["resource_name"] = resource_name

    # Add the resource to the local data store
    local_add_resource(parsed_response)

    # Pass the resource back to the web app
    return parsed_response

def local_get_resource(resource_name):
    resource = session.query(SefariaResource).filter_by(resource_name=resource_name).first()

    if resource is None:
        return resource

    english_text_array = [] 
    for row in session.query(ResourceTextSection).filter_by(resource_id=resource.id, language_code="en").order_by(ResourceTextSection.text_index):
        english_text_array.append(row.text)
    

    hebrew_text_array = []
    for row in session.query(ResourceTextSection).filter_by(resource_id=resource.id, language_code="he").order_by(ResourceTextSection.text_index):
        hebrew_text_array.append(row.text)

    # Update the counter of how many times this resource has been seen
    resource.seen_count += 1

    result = {}
    result["HebrewText"] = hebrew_text_array
    result["EnglishText"] = english_text_array
    result["HebrewSectionReference"] = resource.HebrewSectionReference
    result["EnglishSectionReference"] = resource.EnglishSectionReference

    session.commit()
    return result

def local_add_resource(resource_dict):
    resource = SefariaResource(
        HebrewSectionReference=resource_dict["HebrewSectionReference"],
        EnglishSectionReference=resource_dict["EnglishSectionReference"],
        resource_name=resource_dict["resource_name"])
    session.add(resource)
    session.flush() #To make sure the id is assigned for future foreign key reference

    # add all of the section text in seperate table
    hebrew_text_index = 0
    for text in resource_dict["HebrewText"]:
        hebrew_text_index += 1
        text_section = ResourceTextSection(
            resource_id=resource.id,
            language_code="he",
            text_index=hebrew_text_index,
            text=text)
        session.add(text_section)

    english_text_index = 0
    for text in resource_dict["EnglishText"]:
        english_text_index += 1
        text_section = ResourceTextSection(
            resource_id=resource.id,
            language_code="en",
            text_index=english_text_index,
            text=text)
        session.add(text_section)

    session.commit()
    return

def local_monitor_resources(delay):
    session2 = Session()

    while True:
        for resource in session2.query(SefariaResource):
            seconds_old = (datetime.utcnow() - resource.last_seen_timestamp).total_seconds()
            if seconds_old > CACHE_LIFETIME_SECONDS:
                print "Deleting " + resource.resource_name + " which is " + str(seconds_old) + " seconds old"
                local_delete_resource(session2, resource.resource_name)
        time.sleep(delay)

def local_delete_resource(session2, resource_name):
    resource = session2.query(SefariaResource).filter_by(resource_name=resource_name).first()

    if resource is None:
        return resource

    for row in session2.query(ResourceTextSection).filter_by(resource_id=resource.id, language_code="en").order_by(ResourceTextSection.text_index):
        session2.delete(row)

    for row in session2.query(ResourceTextSection).filter_by(resource_id=resource.id, language_code="he").order_by(ResourceTextSection.text_index):
        session2.delete(row)

    session2.delete(resource)

    session2.commit()

def get_first_50_characters(array):
    result = ""
    for string in array:
        for char in string:
            result += char
            if len(result) >= 50:
                return result
    return result

if __name__ == "__main__":
    Thread(target=local_monitor_resources, args=(CACHE_MONITOR_LOOP_DELAY_IN_SECONDS,)).start()
    app.run(port=3017)
