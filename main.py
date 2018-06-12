# -*- coding: utf-8 -*-
"""An embed server for Sefaria.org"""
import time
from StringIO import StringIO
from urlparse import urljoin
from datetime import datetime
from google.appengine.api import urlfetch

import logging
import json
from constants import *
from gematriya import getGematriyaOfNumber
import re
import os

from image_utils import ImageText

from flask import Flask, render_template, request, send_file, abort, send_from_directory
from bidi.algorithm import get_display

from PIL import Image, ImageFont, ImageDraw

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/<resource>")
def root(resource):
    route = request.args.get('route')
    lang = request.args.get('lang')
    result = remote_get_resource(resource)

    if route == "embed":
        result = format_resource_for_view(result, lang)
        return render_template("embed.j2", ob=result)

    else:
        platform = request.args.get('platform')

        if platform is None: platform = "facebook"

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
            img.write_text_box((margin, -font_size * .5 +branding_height), text, box_width=image_width - 2 * margin, font_filename=font_file,
                               font_size=font_size, color=text_color,
                               place='justify', RTL=True, additional_line_spacing=additional_line_spacing)


        else:
            img.write_text_box((margin, -font_size +branding_height), text, box_width=image_width - 2 * margin, font_filename=font_file,
                               font_size=font_size, color=text_color,
                               place='justify', RTL=False)

        img.draw.line((0, category_color_line_width/2, image_width, category_color_line_width/2), fill=category_color_line_color, width=category_color_line_width)

        if (sefaria_branding):
            # Add Title Header
            font = ImageFont.truetype(os.path.dirname(os.path.realpath(__file__))+"/static/fonts/"+font_file, font_size)
            img.draw.line((0, branding_height/2+category_color_line_width, image_width, branding_height/2+category_color_line_width), fill=(247, 248, 248, 255), width=branding_height)
            w, h = img.draw.textsize(title, font=font)
            img.draw.text(((image_width - w) / 2, (branding_height+category_color_line_width/2 - h) / 2), title, fill=(35, 31, 32, 255), font=font)

            # Add footer
            footer = Image.open(os.path.dirname(os.path.realpath(__file__))+"/static/img/footer.png")
            img.paste(footer, (0, image_height-116))

        #"""

        img_io = StringIO()
        img.save(img_io, format="png")
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')

def remote_get_resource(resource_name):
    """Issues a GET request to fetch resource and returns dictionary of the relevant data"""
    url = urljoin(SEFARIA_API_NODE, resource_name.replace(" ","%20"))
    params = dict(
        commentary=0,
        context=0
    )

    try:
        result = urlfetch.fetch(url, headers=params)
        if result.status_code == 200:
            full_json = json.loads(result.content)

            # Parse the relevant parts of the json
            parsed_response = {}
            parsed_response["HebrewText"] = full_json["he"] if type(full_json["he"]) is list else [full_json["he"]]
            parsed_response["EnglishText"] = full_json["text"] if type(full_json["text"]) is list else [
                full_json["text"]]
            parsed_response["HebrewSectionReference"] = full_json["heSectionRef"]
            parsed_response["EnglishSectionReference"] = full_json["sectionRef"]
            parsed_response["resource_category"] = full_json["primary_category"]
            parsed_response["resource_name"] = resource_name

            # Pass the resource back to the web app
            return parsed_response

        else:
            return result.status_code
    except urlfetch.Error:
        logging.exception('Caught exception fetching url')

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
        resource["meta_description"] = smart_truncate(resource["HebrewText"], length=50, suffix="")
    elif lang == 'en':
        resource["defaultLanguageCode"] = "en"
        resource["meta_description"] = smart_truncate(resource["EnglishText"], length=50, suffix="")
    else:
        resource["defaultLanguageCode"] = "en"
        resource["meta_description"] = smart_truncate(resource["EnglishText"], length=50, suffix="")

    del resource["HebrewText"]
    del resource["EnglishText"]

    return resource


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

if __name__ == '__main__':
    app.run()
