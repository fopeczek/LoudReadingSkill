import difflib
import bisect

from .util import just_letters


class TokenMatchedContent:
    _matched_content: list[int, int]  # index, size
    _token_size: int  # Equals -1 after calling the add_unknown method

    def __init__(self, token_size: int):
        self._matched_content = []
        self._token_size = token_size

    def add_match(self, index: int, size: int):
        self._matched_content.append((index, size))
        assert self.matched_size() <= self._token_size

    def matched_size(self) -> int:
        ans = sum(
            [size for _, size in self._matched_content]
        )  # Should be equal or less than token_size
        return ans

    @property
    def token_size(self) -> int:
        if self._token_size >= 0:
            return self._token_size
        return self.matched_size()

    def add_unknown(self):
        """Adds unknown index to all the non-identified characters. Must be called only after all the matches have been added."""
        assert self._token_size >= 0
        ms = self.matched_size()
        if ms < self._token_size:
            self._matched_content.append((-1, self._token_size - ms))
        self._token_size = -1

    @property
    def uniform_match(self) -> bool:
        assert self._token_size == -1
        assert len(self._matched_content) > 0
        return len(self._matched_content) == 1

    @property
    def dominant_match(self) -> int:
        assert self._token_size == -1
        assert len(self._matched_content) > 0
        return max(self._matched_content, key=lambda x: x[1])[0]

    @property
    def uniform_match_ignore_unknown(self) -> bool:
        # Returns True if there is exactly one match, and it is not an unknown.
        # Returns False if the majority match is unknown.
        assert self._token_size == -1
        assert len(self._matched_content) > 0
        dominant_match = self.dominant_match
        if dominant_match == -1:
            return False
        dominant_size = sum(
            [size for idx, size in self._matched_content if idx == dominant_match]
        )
        return (
            dominant_size >= self.token_size * 0.8
        )  # 80% of the token must be the dominant match


class MatchingContext:
    _correct_matched_content: list[TokenMatchedContent]
    _user_tokens_sizes: list[int]  # Just sizes of each user token
    _user_token_by_pos: list[
        int
    ]  # Index->Pos for user token. Effectively, this is a list of token starts.
    _correct_token_by_pos: list[int]  # Index->Pos for correct token.

    def __init__(self, correct_token_sizes: list[int], user_token_sizes: list[int]):
        self._correct_matched_content = [
            TokenMatchedContent(token_size) for token_size in correct_token_sizes
        ]
        self._user_tokens_sizes = user_token_sizes
        self._user_token_by_pos = [0]
        for size in user_token_sizes:
            self._user_token_by_pos.append(self._user_token_by_pos[-1] + size)
        self._correct_token_by_pos = [0]
        for size in correct_token_sizes:
            self._correct_token_by_pos.append(self._correct_token_by_pos[-1] + size)

    def find_user_token_by_pos(self, pos: int) -> int:
        return bisect.bisect_left(self._user_token_by_pos, pos)

    def find_correct_token_by_pos(self, pos: int) -> int:
        return bisect.bisect_right(self._correct_token_by_pos, pos) - 1

    def add_match(self, correct_pos: int, user_pos: int, size: int):
        assert size > 0
        correct_index_start = self.find_correct_token_by_pos(correct_pos)
        correct_index_end = self.find_correct_token_by_pos(correct_pos + size - 1)

        for correct_idx in range(correct_index_start, correct_index_end + 1):
            correct_token = self._correct_matched_content[correct_idx]
            correct_relpos = correct_pos - self._correct_token_by_pos[correct_idx]
            assert correct_token.token_size >= correct_relpos >= 0
            correct_size_left = correct_token.token_size - correct_relpos
            assert correct_token.token_size >= correct_size_left > 0

            user_index = self.find_user_token_by_pos(user_pos)
            while (
                True
            ):  # Iterate over all user tokens that are within the current correct token
                user_token_size = self._user_tokens_sizes[user_index]
                user_relpos = user_pos - self._user_token_by_pos[user_index]

                user_size_left = user_token_size - user_relpos

                common_size = min(correct_size_left, user_size_left, size)
                correct_token.add_match(user_index, common_size)
                correct_pos += common_size
                user_pos += common_size
                correct_size_left -= common_size
                size -= common_size
                user_size_left -= common_size
                if user_size_left == 0:
                    user_index += 1  # Next user token, continue the while loop
                if correct_size_left == 0:
                    break  # Next correct_pos, continue the outer for loop.
                if size == 0:
                    break  # Nothing left to do.
            if size == 0:
                break

    def add_unknowns(self):
        for token in self._correct_matched_content:
            token.add_unknown()

    @property
    def cleanly_matched_tokens(self) -> list[bool]:
        return [
            token.uniform_match_ignore_unknown
            for token in self._correct_matched_content
        ]

    @property
    def dominant_matches(self) -> list[int]:
        return [token.dominant_match for token in self._correct_matched_content]


def word_mapper(
    correct_tokens: list[str], user_tokens: list[str]
) -> tuple[list[int], list[bool]]:
    # Returns a best-effort list of correct word indices for each consecutive user word.
    # Each index of the returned list corresponds to the index of the user token.
    # Returned value is the index of the correct token that the user token has most in common with.
    # If the user token has no common tokens with correct_tokens, the value is -1.
    # Obviously, the non-zero values in the list are in non-decreasing order.
    #
    # For each correct token returns the corresponding user token, and bool indicating whether there was a clean match.

    sequence_matcher = difflib.SequenceMatcher(
        None, "".join(correct_tokens), "".join(user_tokens)
    )
    mb = sequence_matcher.get_matching_blocks()
    mb = [mb for mb in mb if mb.size > 0]

    if len(mb) == 0:
        return [-1] * len(user_tokens), [False] * len(correct_tokens)

    matching_context = MatchingContext(
        correct_token_sizes=[len(token) for token in correct_tokens],
        user_token_sizes=[len(token) for token in user_tokens],
    )

    for a, b, size in mb:
        matching_context.add_match(a, b, size)

    matching_context.add_unknowns()
    return matching_context.dominant_matches, matching_context.cleanly_matched_tokens


def _score_internal(correct_tokens: list[str], user_tokens: list[str]) -> list[bool]:
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
            user_pos_left = token_breaks[left_word_pos_idx]
            user_pos_right = token_breaks[left_word_pos_idx + 1]
            if user_pos_right <= correct_pos_right:
                # The word is correct.
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
        while user_pos_left <= correct_pos_left:
            words[left_word_pos_idx] = False
            left_word_pos_idx += 1
            if left_word_pos_idx == len(token_breaks) - 1:
                break
            user_pos_left = token_breaks[left_word_pos_idx]
            user_pos_right = token_breaks[left_word_pos_idx + 1]
        if left_word_pos_idx == len(token_breaks) - 1:
            break

    return words


def add_space_tokens(tokens: list[str]) -> list[str]:
    # Adds space token ([" "]) between each token, so "".join(correct_sentence_spaces) = correct_sentence_letters
    token_spaces = []
    for token in tokens:
        token_spaces.append(" ")
        token_spaces.append(token)
    token_spaces.append(" ")
    return token_spaces


def make_respeak_map(correct_sentence: str, respeak_sentence: str) -> list[int]:
    # Returns a list of correct word indices for each consecutive respeak word.
    # We will use the same logic as in the score_internal function.
    correct_sentence_letters = just_letters(correct_sentence)
    respeak_sentence_letters = just_letters(respeak_sentence)

    correct_tokens = correct_sentence_letters.split()
    respeak_tokens = respeak_sentence_letters.split()

    correct_tokens_spaces = add_space_tokens(correct_tokens)
    respeak_tokens_spaces = add_space_tokens(respeak_tokens)

    mapped_words, _ = word_mapper(correct_tokens_spaces, respeak_tokens_spaces)
    for i, idx in enumerate(mapped_words):
        if idx == -1 and i % 2 == 1:
            print(
                f"Warning: correct word {correct_tokens[i%2 + 1]} not found in the respeak sentence."
            )

    return mapped_words


def score_sentence_respeak(
    correct_token_sizes: list[int],
    correct2respeak_map: list[int],
    respeak_sentence: str,
    user_sentence: str,
) -> tuple[float, list[bool]]:
    """Scores the user sentence based on the proximity with the respeak sentece. The answer is mapped back
    to the correct tokens"""
    _, respeak_errors, _ = make_token_mapping_from_sentences(
        correct_sentence=respeak_sentence, user_sentence=user_sentence
    )

    correct_errors = [
        respeak_errors[correct2respeak_map[i]] for i in range(len(correct2respeak_map))
    ]

    return calc_score_from_error_list(correct_token_sizes, correct_errors)


def score_sentence_correct(
    correct_sentence: str, user_sentence: str
) -> tuple[float, list[bool], list[int]]:
    _, correct_errors, tokens = make_token_mapping_from_sentences(
        correct_sentence=correct_sentence, user_sentence=user_sentence
    )

    correct_token_sizes = [len(token) for token in tokens]
    ans = calc_score_from_error_list(correct_token_sizes, correct_errors)
    return ans[0], ans[1], correct_token_sizes


def calc_score_from_error_list(
    token_sizes: list[int], token_errors: list[bool]
) -> tuple[float, list[bool]]:
    assert len(token_errors) % 2 == 1
    correct_token_len = (len(token_errors) - 1) // 2
    ans = [True for _ in range(correct_token_len)]
    # Each False in space word is propagated as False to the adjoining letter words
    for i in range(0, len(ans)):
        if not token_errors[2 * i + 1]:
            ans[i] = False
        if not token_errors[2 * i + 2]:
            ans[i] = False
            if i + 1 < len(ans):
                ans[i + 1] = False

    if not token_errors[-1]:
        ans[-1] = False

    word_sizes = [wordlen for wordlen in token_sizes]
    total_word_count = sum(word_sizes)
    wrong_words_sizes = sum(word_sizes[i] for i in range(len(word_sizes)) if not ans[i])
    accuracy = (total_word_count - wrong_words_sizes) / total_word_count
    return accuracy, ans


def make_token_mapping_from_sentences(
    correct_sentence: str, user_sentence: str
) -> tuple[list[int], list[bool], list[str]]:
    correct_sentence_letters = just_letters(correct_sentence)
    user_sentence_letters = just_letters(user_sentence)

    correct_tokens = correct_sentence_letters.split()
    user_tokens = user_sentence_letters.split()

    correct_tokens_spaces = add_space_tokens(correct_tokens)
    user_tokens_spaces = add_space_tokens(user_tokens)

    words, word_errors = word_mapper(correct_tokens_spaces, user_tokens_spaces)

    return words, word_errors, correct_tokens


def score_sentence(
    correct_sentence: str, respeak_sentence: str, user_sentence: str
) -> tuple[float, list[bool]]:
    score_correct, words_correct, correct_token_sizes = score_sentence_correct(
        correct_sentence, user_sentence
    )

    correct2respeak_map = make_respeak_map(correct_sentence, respeak_sentence)
    score_respeak, words_respeak = score_sentence_respeak(
        correct_token_sizes, correct2respeak_map, respeak_sentence, user_sentence
    )
    if score_correct < score_respeak:
        return score_respeak, words_respeak

    return score_correct, words_correct

    # def score_sentence(
    #         correct_sentence: str,
    #         user_sentence: str
    # ) -> tuple[float, list[bool]]:
    #     correct_sentence_letters = just_letters(correct_sentence)
    #     user_sentence_letters = just_letters(user_sentence)
    #
    #     correct_tokens = correct_sentence_letters.split()
    #     user_tokens = user_sentence_letters.split()
    #
    #     correct_tokens_spaces = add_space_tokens(correct_tokens)
    #     user_tokens_spaces = add_space_tokens(user_tokens)
    #
    #     ans = [True for _ in correct_tokens]
    #     words = word_mapper(correct_tokens_spaces, user_tokens_spaces)[0]
    #
    #     # Each False in space word is propagated as False to the adjoining letter words
    #     for i in range(len(ans) - 1):
    #         if not words[2 * i]:
    #             ans[i] = False
    #         else:
    #             if not words[2 * i + 1]:
    #                 ans[i] = False
    #                 ans[i + 1] = False
    #
    #     if not words[-1]:
    #         ans[-1] = False
    #
    #     word_sizes = [len(word) for word in correct_tokens]
    #     total_word_count = sum(word_sizes)
    #     wrong_words_sizes = sum(word_sizes[i] for i in range(len(word_sizes)) if not ans[i])
    #     accuracy = (total_word_count - wrong_words_sizes) / total_word_count
    #     return accuracy, ans
