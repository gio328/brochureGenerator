import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from IPython.display import Markdown, display
from openai import OpenAI
import os
import requests
from helper import jsonToDict

# Some websites need you to use proper headers when fetching them:
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

class Website:
    def __init__(self, url):
        self.url = url
        self.text = None
        self.title = None
        self.links = None   

    def fetch_content(self):
        try:
            response = requests.get(self.url, headers=headers)  # Send a GET request to the URL
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
            response.encoding = 'utf-8' # Ensure the response encoding is set to utf-8
        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve the webpage. Error: {e}")
            return None

        try:
            soup = BeautifulSoup(response.content, 'lxml')  # Parse the HTML content using BeautifulSoup and lxml
            self.title = soup.title.string  # Extract the title of the webpage
            text_content = soup.get_text()  # Extract the entire text content
            self.text = ' '.join(text_content.split())  # Remove extra whitespaces
            

            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)

            # Extract all links
            self.links = [a['href'] for a in soup.find_all('a', href=True)]
            
            return self.text

        except Exception as e:
            print(f"Failed to parse the webpage content. Error: {e}")
            return None

webcontent = Website("https://www.weather.gov/lox/")
webcontent.fetch_content()
print('website title',webcontent.title)
print('website content', webcontent.text)
print("website Links =>", webcontent.links)

# Load environment variables in a file called .env
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Check the key
if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-proj-"):
    print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
elif api_key.strip() != api_key:
    print("An API key was found, but it looks like it might have space or tab characters at the start or end - please remove them - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")

openai = OpenAI() # Create an instance of the OpenAI class

# system prompt
links_system_prompt = "You are provided with a list of links found on a webpage. \
You are able to decide which of the links would be most relevant to include in a brochure about the website, \
such as links to an About page, or a Company page, or Careers/Jobs pages.\n"
links_system_prompt += "You should respond in JSON as in this example:"
links_system_prompt += """
{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page": "url": "https://another.full.url/careers"}
    ]
}
"""

links_user_prompt = "here are the links found on the website: \n"
links_user_prompt += "\n".join(webcontent.links)
links_user_prompt += "\n\nPlease decide which of the links would be most relevant to include in a brochure about the website, \" \
respond with the full https URL in JSON format. \
Do not include Terms of Service, Privacy, email links.\n"

messages = [
    {"role": "system", "content": links_system_prompt},
    {"role": "user", "content": links_user_prompt}
]

response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
# print("response from LLM: ", response.choices[0].message.content)
jsonlinks = response.choices[0].message.content
links = jsonToDict(jsonlinks)


def get_all_details(links):
    result = ""
    try:
        print('links =>', links)
        for link in links["links"]:
            if link['type'] and link['url']:
                result += f"\n\n{link['type']}\n"
                # print("link['url'] =>", link['url'])
                # print("fetching content...")
                result += Website(link['url']).fetch_content()
                # print("result =>", result)
    except Exception as e:
        print(f"Failed to parse the links. Error: {e}")
        return None
    # print("result =>", result)
    return result

link_details = get_all_details(links)
print("link_details: ", link_details)

system_prompt = "You are an assistant that analyzes the contents of several relevant pages from a company website \
and creates a short brochure about the company for prospective customers, investors and recruits. Respond in markdown.\
Include details of company culture, customers and careers/jobs if you have the information."


user_prompt = f"You are looking at a website called: {webcontent.title}\n"
user_prompt += f"Here are the contents of its landing page and other relevant pages; use this information to build a short brochure of the website in markdown.\n"
user_prompt += link_details
user_prompt = user_prompt[:5_000] # Truncate if more than 5,000 characters

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]

response2 = openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
print(response2.choices[0].message.content)