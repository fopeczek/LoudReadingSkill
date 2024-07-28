from pathlib import Path
import json


def create_and_load_file(file_name: Path, default_content):
    try:
        with open(file_name, "r") as fr:
            try:
                return json.load(fr)
            except json.JSONDecodeError:
                with open(file_name, "w") as fw:
                    jsonobj = json.dumps(default_content, indent=4)
                    fw.write(jsonobj)
    except FileNotFoundError:
        with open(file_name, "w") as fw:
            jsonobj = json.dumps(default_content, indent=4)
            fw.write(jsonobj)
    return default_content


def create_and_load_file_str(file_name: Path, default_content: str):
    if file_name.exists():
        with open(file_name, "r") as fr:
            return json.load(fr)
    else:
        with open(file_name, "w") as fw:
            fw.write(default_content)
    return default_content


ignored_letters = '!?".,;:-„”()[]{}'


def just_letters(s: str) -> str:
    tokens = s.lower().translate(str.maketrans("", "", ignored_letters)).split()
    # Last letter "ę" in each token replace with "e".
    for i in range(len(tokens)):
        token = tokens[i]
        if token[-1] == "ę":
            tokens[i] = token[:-1] + "e"

    return " ".join(tokens)


def just_letters_mapping(s: str) -> list[tuple[int, int]]:
    """Returns a list of tuples (start, end) of words in the string"""

    # Iterate a state machine with two states:
    # - on a letter, inside a word
    #   - each new letter extends the word
    #   - each new non-letter ends the word, commits it to ans, and sets a state to "not in a word"
    # - not in a word
    #   - each new non-letter (ignored_letters and space) extends the state
    #   - each new letter starts a new word.

    ans = []
    pos = 0
    start_pos = pos

    def in_a_word() -> int:
        nonlocal pos
        char = s[pos]
        return 0 if (char in ignored_letters or char.isspace()) else 1

    if len(s) == 0:
        return []

    in_word_state = 2

    while pos < len(s):
        if in_word_state == 2:
            if (in_word_state := in_a_word()) == 1:
                start_pos = pos
            else:
                in_word_state = 0
        elif in_word_state == 1:
            if (in_word_state := in_a_word()) == 0:
                ans.append((start_pos, pos))
        elif in_word_state == 0:
            if (in_word_state := in_a_word()) == 1:
                start_pos = pos

        pos += 1

    return ans
