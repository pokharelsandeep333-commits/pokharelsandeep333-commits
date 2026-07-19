import json
import os
import re
import sys
import random

WORDS = ["PYTHON", "TERMINAL", "LINUX", "DOCKER", "SERVER", "UBUNTU", "HACKER", "GITHUB", "REACT", "NODEJS"]
MAX_MISTAKES = 6

GALLOWS = [
r"""
  +---+
  |   |
      |
      |
      |
      |
=========""",
r"""
  +---+
  |   |
  O   |
      |
      |
      |
=========""",
r"""
  +---+
  |   |
  O   |
  |   |
      |
      |
=========""",
r"""
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========""",
r"""
  +---+
  |   |
  O   |
 /|\  |
      |
      |
=========""",
r"""
  +---+
  |   |
  O   |
 /|\  |
 /    |
      |
=========""",
r"""
  +---+
  |   |
  O   |
 /|\  |
 / \  |
      |
========="""
]

def load_state():
    try:
        with open(".hangman_state.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"word": random.choice(WORDS), "guessed": [], "mistakes": 0}

def save_state(state):
    with open(".hangman_state.json", "w") as f:
        json.dump(state, f)

def render_board(state):
    word = state["word"]
    guessed = state["guessed"]
    mistakes = state["mistakes"]
    
    display_word = " ".join([letter if letter in guessed else "_" for letter in word])
    board = "### `> ./hangman.sh`\n\n```text\n"
    board += GALLOWS[mistakes] + "\n\n"
    board += f"WORD: {display_word}\n\n"
    board += f"MISTAKES: {mistakes}/{MAX_MISTAKES}\n"
    
    if mistakes >= MAX_MISTAKES:
        board += f"\nGAME OVER! The word was {word}. A new game will start on the next guess.\n"
    elif all(l in guessed for l in word):
        board += f"\nYOU WON! The word was {word}. A new game will start on the next guess.\n"
        
    board += "```\n\n"
    board += "### Guess a Letter:\n"
    
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    keyboard = []
    for letter in alphabet:
        if letter in guessed:
            keyboard.append(f"~{letter}~")
        else:
            url = f"https://github.com/pokharelsandeep333-commits/pokharelsandeep333-commits/issues/new?title=Hangman%20Guess:%20{letter}&labels=hangman&body=Just%20click%20Submit%20new%20issue!"
            keyboard.append(f"[`{letter}`]({url})")
            
    board += " ".join(keyboard)
    return board

def update_readme(board):
    with open("README.md", "r") as f:
        content = f.read()
        
    pattern = r"(<!-- HANGMAN_START -->).*?(<!-- HANGMAN_END -->)"
    replacement = f"\\1\n{board}\n\\2"
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open("README.md", "w") as f:
        f.write(new_content)

def main():
    guess = os.environ.get("GUESS", "").upper().strip()
    if not guess or not guess.isalpha() or len(guess) != 1:
        # Just render current board without processing guess (useful for first initialization)
        state = load_state()
        board = render_board(state)
        update_readme(board)
        return
        
    state = load_state()
    
    if state["mistakes"] >= MAX_MISTAKES or all(l in state["guessed"] for l in state["word"]):
        state = {"word": random.choice(WORDS), "guessed": [], "mistakes": 0}
        
    if guess not in state["guessed"]:
        state["guessed"].append(guess)
        if guess not in state["word"]:
            state["mistakes"] += 1
            
    save_state(state)
    board = render_board(state)
    update_readme(board)

if __name__ == "__main__":
    main()
