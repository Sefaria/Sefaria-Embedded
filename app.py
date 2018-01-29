# -*- coding: utf-8 -*-
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

from flask import Flask, render_template, request, send_file, abort

import requests

from constants import *
from gematriya import getGematriyaOfNumber

import re
from bidi.algorithm import get_display
from image_utils import ImageText
from PIL import Image, ImageFont
import os

category_colors = {
  "Commentary":         "#4871bf",
  "Tanakh":             "#004e5f",
  "Midrash":            "#5d956f",
  "Mishnah":            "#5a99b7",
  "Talmud":             "#ccb479",
  "Halakhah":           "#802f3e",
  "Kabbalah":           "#594176",
  "Philosophy":         "#7f85a9",
  "Liturgy":            "#ab4e66",
  "Tanaitic":           "#00827f",
  "Parshanut":          "#9ab8cb",
  "Chasidut":           "#97b386",
  "Musar":              "#7c406f",
  "Responsa":           "#cb6158",
  "Apocrypha":          "#c7a7b4",
  "Other":              "#073570",
  "Quoting Commentary": "#cb6158",
  "Sheets":             "#7c406f",
  "Community":          "#7c406f",
  "Targum":             "#7f85a9",
  "Modern Works":       "#7c406f",
  "Modern Commentary":  "#7c406f",
}

platform_settings = {
    "twitter": {
        "font_size": 30,
        "additional_line_spacing": 10,
        "image_width": 506,
        "image_height": 253,
        "margin": 20,
        "category_color_line_width": 7,
        "sefaria_branding": False,
        "branding_height": 0
    },
    "facebook": {
        "font_size": 76,
        "additional_line_spacing": 25,
        "image_width": 1200,
        "image_height": 630,
        "margin": 40,
        "category_color_line_width": 15,
        "sefaria_branding": False,
        "branding_height": 0

    },

    "instagram": {
        "font_size": 70,
        "additional_line_spacing": 20,
        "image_width": 1040,
        "image_height": 1040,
        "margin": 40,
        "category_color_line_width": 13,
        "sefaria_branding": True,
        "branding_height": 100
    }

}

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
    resource_category = Column(String)
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

@app.route("/embed/<resource>")
def root(resource):
    """Returns the embed page for a given Sefaria resource"""
    lang = request.args.get('lang')

    result = get_resource(resource)
    result = format_resource_for_view(result, lang)

    return render_template("embed.j2", ob=result)

@app.route("/image/<resource>")
def get_image(resource):
    lang = request.args.get('lang')
    platform = request.args.get('platform')

    if platform is None: platform = "facebook"

    result = get_resource(resource)

    text_color = (121, 121, 121)
    font_file = "TaameyFrankCLM-Medium.ttf" if lang == "he" else "Amiri-Regular.ttf"
    category_color_line_color = category_colors[result["resource_category"]]

    font_size = platform_settings[platform]["font_size"]
    image_width = platform_settings[platform]["image_width"]
    image_height = platform_settings[platform]["image_height"]
    margin = platform_settings[platform]["margin"]
    category_color_line_width = platform_settings[platform]["category_color_line_width"]
    additional_line_spacing = platform_settings[platform]["additional_line_spacing"]
    sefaria_branding = platform_settings[platform]["sefaria_branding"]
    branding_height = platform_settings[platform]["branding_height"]


    img = ImageText((image_width, image_height), background=(255, 255, 255, 255))

    text = result["HebrewText"] if lang == "he" else result["EnglishText"]
    title = result["HebrewSectionReference"] if lang == "he" else result["EnglishSectionReference"]

    text = ' '.join(text)

    text = cleanup_and_format_text(text, lang)


    if len(text) == 0:
        abort(204)

    if lang == "he":
        img.write_text_box((margin, -font_size * .75 +branding_height+margin), text, box_width=image_width - 2 * margin, font_filename=font_file,
                           font_size=font_size, color=text_color,
                           place='justify', RTL=True, additional_line_spacing=additional_line_spacing)


    else:
        img.write_text_box((margin, -font_size +branding_height+margin), text, box_width=image_width - 2 * margin, font_filename=font_file,
                           font_size=font_size, color=text_color,
                           place='justify', RTL=False)

    img.draw.line((0, category_color_line_width/2, image_width, category_color_line_width/2), fill=category_color_line_color, width=category_color_line_width)

    if (sefaria_branding):
        # Add Title Header
        font = ImageFont.truetype(os.path.dirname(os.path.realpath(__file__))+"/static/fonts/"+font_file, font_size)
        img.draw.line((0, branding_height/2+category_color_line_width, image_width, branding_height/2+category_color_line_width), fill=(247, 248, 248, 255), width=branding_height)
        w, h = img.draw.textsize(title, font=font)
        img.draw.text(((image_width - w) / 2, (branding_height+category_color_line_width/2 - h) / 2), cleanup_and_format_text(title,lang), fill=(35, 31, 32, 255), font=font)

        # Add footer
        footer = Image.open(os.path.dirname(os.path.realpath(__file__))+"/static/img/footer.png")
        img.paste(footer, (0, image_height-116))

    img.save(os.path.dirname(os.path.realpath(__file__))+"/generatedImages/sample-imagetext.png")



    return send_file('generatedImages/sample-imagetext.png', mimetype='image/png')



def format_resource_for_view(resource, lang):
    """format_resource_for_view receives a resource that was received from the database
    and modifies it to the proper format needed for view rendering"""

    # Add line numbers
    resource["hebrew_data"] = [[getGematriyaOfNumber(i + 1), resource["HebrewText"][i]]
                               for i in range(len(resource["HebrewText"]))]

    resource["english_data"] = [[i + 1, resource["EnglishText"][i]]
                                for i in range(len(resource["EnglishText"]))]

    resource["category_color"] = category_colors[resource["resource_category"]]


    if lang == 'he':
        resource["defaultLanguageCode"] = "he"
        resource["meta_description"] = get_first_50_characters(resource["HebrewText"])
    elif lang == 'en':
        resource["defaultLanguageCode"] = "en"
        resource["meta_description"] = get_first_50_characters(resource["EnglishText"])
    else:
        resource["defaultLanguageCode"] = "en"
        resource["meta_description"] = get_first_50_characters(resource["EnglishText"])

    del resource["HebrewText"]
    del resource["EnglishText"]

    return resource

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
    params = dict(
        commentary=0,
        context=0
    )
    response = requests.get(url, params=params)
    response.encoding = "UTF-8"
    full_json = response.json()

    # Parse the relevant parts of the json
    parsed_response = {}
    parsed_response["HebrewText"] = full_json["he"] if type(full_json["he"]) is list else [full_json["he"]]
    parsed_response["EnglishText"] = full_json["text"] if type(full_json["text"]) is list else [full_json["text"]]
    parsed_response["HebrewSectionReference"] = full_json["heSectionRef"]
    parsed_response["EnglishSectionReference"] = full_json["sectionRef"]
    parsed_response["resource_category"] = full_json["primary_category"]
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
    result["resource_category"] = resource.resource_category
    result["resource_name"] = resource.resource_name

    session.commit()
    return result

def local_add_resource(resource_dict):
    resource = SefariaResource(
        HebrewSectionReference=resource_dict["HebrewSectionReference"],
        EnglishSectionReference=resource_dict["EnglishSectionReference"],
        resource_category=resource_dict["resource_category"],
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

def smart_truncate(content, length=180, suffix='...'):
    if len(content) <= length:
        return content
    else:
        return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix

def cleanup_and_format_text(text, language):
#removes html tags, nikkudot and taamim. Applies BIDI algorithm to text so that letters aren't reversed in PIL.
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', text)
    text = text.replace(u"\u05BE", " ")  #replace hebrew dash with ascii

    if language == "he":
        strip_cantillation_vowel_regex = re.compile(ur"[^\u05d0-\u05f4\s^\x00-\x7F\x80-\xFF\u0100-\u017F\u0180-\u024F\u1E00-\u1EFF\u2000-\u206f]", re.UNICODE)
    else:
        strip_cantillation_vowel_regex = re.compile(ur"[^\s^\x00-\x7F\x80-\xFF\u0100-\u017F\u0180-\u024F\u1E00-\u1EFF\u2000-\u206f]", re.UNICODE)
    text = strip_cantillation_vowel_regex.sub('', text)
    text = smart_truncate(text)
    text = get_display(text)
    return text


if __name__ == "__main__":
    Thread(target=local_monitor_resources, args=(CACHE_MONITOR_LOOP_DELAY_IN_SECONDS,)).start()
    app.run(host='0.0.0.0', port=80)
