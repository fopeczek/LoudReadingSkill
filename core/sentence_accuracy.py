import difflib

from .util import just_letters


def score_internal(correct_tokens: list[str], user_tokens: list[str]) -> list[bool]:
    sequence_matcher = difflib.SequenceMatcher(
        None, "".join(correct_tokens), "".join(user_tokens)
    )
    mb = sequence_matcher.get_matching_blocks()
    mb = [mb for mb in mb if mb.size > 0]
    if len(mb) == 0:
        return [False] * len(correct_tokens)

    left_word_pos_idx = 0
    sequence_pos = 0
    words = [True] * (
        len(correct_tokens)
    )  # Each word will get a True if was correctly read, or False if not

    # token[i] == "".join(correct_tokens[:i])[token_breaks[i]:token_breaks[i+1]]
    token_lengths = [len(token) for token in correct_tokens]
    token_breaks = [sum(token_lengths[:i]) for i in range(0, 1 + len(correct_tokens))]

    correct_pos_left = mb[sequence_pos].a
    correct_pos_right = mb[sequence_pos].size

    # All the words before the first match are wrong.
    while token_breaks[left_word_pos_idx] + 1 < correct_pos_left:
        words[left_word_pos_idx] = False
        left_word_pos_idx += 1
        if left_word_pos_idx == len(token_breaks) - 1:
            return words

    while True:  # Driven by correct_pos.
        correct_pos_left = mb[sequence_pos].a
        correct_pos_right = mb[sequence_pos].size + mb[sequence_pos].a

        while True:
            left_word_pos = token_breaks[left_word_pos_idx]
            right_word_pos = token_breaks[left_word_pos_idx + 1]
            if right_word_pos <= correct_pos_right:
                left_word_pos_idx += 1
                if left_word_pos_idx == len(token_breaks) - 1:
                    break
                continue
            break
        if left_word_pos_idx == len(token_breaks) - 1:
            break

        sequence_pos += 1
        if sequence_pos == len(mb):
            # We are going to exit. All the words not read are wrong (missing).
            left_word_pos_idx += 1
            while left_word_pos_idx < len(token_breaks) - 1:
                words[left_word_pos_idx] = False
                left_word_pos_idx += 1
            break
        correct_pos_left = mb[sequence_pos].a
        correct_pos_right = mb[sequence_pos].size + mb[sequence_pos].a
        while left_word_pos <= correct_pos_left:
            words[left_word_pos_idx] = False
            left_word_pos_idx += 1
            if left_word_pos_idx == len(token_breaks) - 1:
                break
            left_word_pos = token_breaks[left_word_pos_idx]
            right_word_pos = token_breaks[left_word_pos_idx + 1]
        if left_word_pos_idx == len(token_breaks) - 1:
            break

    return words


def add_space_tokens(tokens: list[str]) -> list[str]:
    # Adds space token ([" "]) between each token, so "".join(correct_sentence_spaces) = correct_sentence_letters
    token_spaces = []
    for token in tokens:
        if len(token_spaces) == 0:
            token_spaces.append(token)
        else:
            token_spaces.append(" ")
            token_spaces.append(token)
    return token_spaces


def score_sentence(
    correct_sentence: str, user_sentence: str
) -> tuple[float, list[bool]]:
    correct_sentence_letters = just_letters(correct_sentence)
    user_sentence_letters = just_letters(user_sentence)

    correct_tokens = correct_sentence_letters.split()
    user_tokens = user_sentence_letters.split()

    correct_tokens_spaces = add_space_tokens(correct_tokens)
    user_tokens_spaces = add_space_tokens(user_tokens)

    ans = [True for _ in correct_tokens]

    words = score_internal(correct_tokens_spaces, user_tokens_spaces)

    # Each False in space word is propagated as False to the adjoining letter words
    for i in range(len(ans) - 1):
        if not words[2 * i]:
            ans[i] = False
        else:
            if not words[2 * i + 1]:
                ans[i] = False
                ans[i + 1] = False

    if not words[-1]:
        ans[-1] = False

    word_sizes = [len(word) for word in correct_tokens]
    total_word_count = sum(word_sizes)
    wrong_words_sizes = sum(word_sizes[i] for i in range(len(word_sizes)) if not ans[i])
    accuracy = (total_word_count - wrong_words_sizes) / total_word_count
    return accuracy, ans
