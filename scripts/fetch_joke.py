import urllib.request
import json
import re
import sys
import datetime
import ssl

def fetch_joke():
    url = "https://official-joke-api.appspot.com/jokes/programming/random"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=context) as response:
            data = json.loads(response.read().decode())
            joke = data[0]
            return joke['setup'], joke['punchline']
    except Exception as e:
        print(f"Error fetching joke: {e}")
        return None, None

def update_readme(setup, punchline):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    joke_content = f"""<!-- JOKE_START -->\n```text\n[ {timestamp} ] Fetching ./fortune ...\n\n> {setup}\n> ... {punchline}\n```\n<!-- JOKE_END -->"""

    try:
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()

        new_content = re.sub(
            r"<!-- JOKE_START -->.*?<!-- JOKE_END -->",
            joke_content,
            content,
            flags=re.DOTALL
        )

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print("README updated successfully.")
    except Exception as e:
        print(f"Error updating README: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup, punchline = fetch_joke()
    if setup and punchline:
        update_readme(setup, punchline)
    else:
        sys.exit(1)
