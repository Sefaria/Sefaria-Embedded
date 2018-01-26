# sefaria-embedded
Provides an embedding interface for the Sefaria web app

### Features
* Minimal Javascript allows for a very lightweight page, great for fast loading times on slow connections, easy embedding
* English and Hebrew interface in the embedded page allows for multi-language viewing with super low resource usage
* Generates social media images for various platforms

### Installation instructions
* Clone the Repo
* Create a directory called `generatedImages` under the project folder. To do this, run `mkdir generatedImages` from the project's root directory. Make sure that the server user has write access to it by using a command such as `chmod 777 generatedImages`.
* Install the required Python requirements `pip install -r requirements.txt`
* Run the server: `python app.py`
