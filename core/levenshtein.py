from enum import Enum

import numpy as np


class DiffenenceType(Enum):
    NoError = 0
    ErrorInWord = 1
    MissingPart = 2
    ExtraPart = 3


# def str_levenshtein_distance(s1: str, s2: str) -> int:
#     m, n = len(s1), len(s2)
#     dp = np.zeros((m + 1, n + 1), dtype=int)
#
#     for i in range(m + 1):
#         for j in range(n + 1):
#             if i == 0:
#                 dp[i][j] = j
#             elif j == 0:
#                 dp[i][j] = i
#             elif s1[i - 1] == s2[j - 1]:
#                 dp[i][j] = dp[i - 1][j - 1]
#             else:
#                 dp[i][j] = 1 + min(dp[i - 1][j],  # Deletion
#                                    dp[i][j - 1],  # Insertion
#                                    dp[i - 1][j - 1])  # Substitution
#
#     return dp[m][n]


class SingleCharacterOperation:
    _type: DiffenenceType
    _where_index: int
    _what_inserted: str | None

    def __init__(
        self, type: DiffenenceType, where_index: int, what_inserted: str = None
    ):
        self._type = type
        self._where_index = where_index
        self._what_inserted = what_inserted

    @property
    def operation_type(self) -> DiffenenceType:
        return self._type

    @property
    def where_index(self) -> int:
        return self._where_index

    @property
    def what_inserted(self) -> str | None:
        return self._what_inserted

    def __repr__(self):
        if self._type == DiffenenceType.ErrorInWord:
            ans = f"replace a character with «{self._what_inserted}» at {self._where_index}"
        elif self._type == DiffenenceType.MissingPart:
            ans = f"delete a character at {self._where_index}"
        elif self._type == DiffenenceType.ExtraPart:
            ans = f"insert «{self._what_inserted}» at {self._where_index}"
        elif self._type == DiffenenceType.NoError:
            ans = f"Correct character at {self._where_index}"
        else:
            assert False, "Unknown operation type"

        return ans


class MatchingSubstring:
    _original_text: str
    _original_index: int
    _user_index: int
    _length: int

    def __init__(
        self, original_text: str, original_index: int, user_index: int, length: int
    ):
        self._original_index = original_index
        self._user_index = user_index
        self._length = length
        self._original_text = original_text

    def __repr__(self):
        return f"Excerpt «{self._original_text[self._original_index:(self._original_index + self._length)]}» matches between original position {self._original_index} and user position {self._user_index}"

    def __iter__(self):  # Allows for 'a, b, size = matching_substring'
        return iter([self._original_index, self._user_index, self._length])


def str_levenshtein_distance(
    s1: str, s2: str
) -> tuple[int, list[SingleCharacterOperation]]:
    m, n = len(s1), len(s2)
    dp = np.zeros((m + 1, n + 1), dtype=int)
    operations = np.empty(
        (m + 1, n + 1), dtype=str
    )  # "D" for deletion, "I" for insertion, "S" for substitution

    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0:
                dp[i][j] = j
            elif j == 0:
                dp[i][j] = i
            elif s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],  # Deletion
                    dp[i][j - 1],  # Insertion
                    dp[i - 1][j - 1],
                )  # Substitution
                if dp[i][j] == dp[i - 1][j] + 1:
                    operations[i][j] = "D"
                elif dp[i][j] == dp[i][j - 1] + 1:
                    operations[i][j] = "I"
                else:
                    operations[i][j] = "S"

    # Traceback to get the sequence of operations
    sequence_of_operations = []
    i, j = m, n
    while i > 0 or j > 0:
        if operations[i][j] == "D":
            sequence_of_operations.append(
                SingleCharacterOperation(DiffenenceType.MissingPart, i, s1[i - 1])
            )
            i -= 1
        elif operations[i][j] == "I":
            sequence_of_operations.append(
                SingleCharacterOperation(DiffenenceType.ExtraPart, i, s2[j - 1])
            )
            j -= 1
        elif operations[i][j] == "S":
            sequence_of_operations.append(
                SingleCharacterOperation(DiffenenceType.ErrorInWord, i, s2[j - 1])
            )
            i -= 1
            j -= 1
        else:
            i -= 1
            j -= 1

    sequence_of_operations.reverse()

    return dp[m][n], sequence_of_operations


def make_list_of_matched_substrings(
    s: str, operations: list[SingleCharacterOperation]
) -> list[MatchingSubstring]:
    matching_substrings = []
    index_of_beginning_of_correct_run_of_original = 0
    index_of_beginning_of_correct_run_of_user = 0
    for operation in operations:
        if operation.operation_type == DiffenenceType.NoError:
            continue
        # We encountered an error, so we need to add the string so far to the list of matching substrings
        if index_of_beginning_of_correct_run_of_original < operation.where_index:
            if operation.operation_type == DiffenenceType.ErrorInWord:
                length = (
                    operation.where_index
                    - index_of_beginning_of_correct_run_of_original
                    - 1
                )
            elif operation.operation_type == DiffenenceType.MissingPart:
                length = (
                    operation.where_index
                    - index_of_beginning_of_correct_run_of_original
                    - 1
                )
            elif operation.operation_type == DiffenenceType.ExtraPart:
                length = (
                    operation.where_index
                    - index_of_beginning_of_correct_run_of_original
                )
            else:
                assert False, "Unknown operation type"
            if length > 0:
                matching_substrings.append(
                    MatchingSubstring(
                        s,
                        original_index=index_of_beginning_of_correct_run_of_original,
                        user_index=index_of_beginning_of_correct_run_of_user,
                        length=length,
                    )
                )
            if operation.operation_type == DiffenenceType.ErrorInWord:
                index_of_beginning_of_correct_run_of_original = operation.where_index
                index_of_beginning_of_correct_run_of_user = operation.where_index
            elif operation.operation_type == DiffenenceType.MissingPart:
                index_of_beginning_of_correct_run_of_original = operation.where_index
                index_of_beginning_of_correct_run_of_user = operation.where_index
            elif operation.operation_type == DiffenenceType.ExtraPart:
                index_of_beginning_of_correct_run_of_original = operation.where_index
                index_of_beginning_of_correct_run_of_user = operation.where_index
            else:
                assert False, "Unknown operation type"
    # Add the last matching substring
    matching_substrings.append(
        MatchingSubstring(
            s,
            original_index=index_of_beginning_of_correct_run_of_original,
            user_index=index_of_beginning_of_correct_run_of_user,
            length=len(s) - index_of_beginning_of_correct_run_of_original,
        )
    )
    return matching_substrings


class SequenceMatcher:
    def __init__(self, s1: str, s2: str):
        self._s1 = s1
        self._s2 = s2
        _, operations = str_levenshtein_distance(s1, s2)
        self._matching_substrings = make_list_of_matched_substrings(s1, operations)

    def get_matching_blocks(self):
        return self._matching_substrings


# # Example usage
# s1 = "Potem rozścieliłem w nowym legowisku jego kocyk, również otrzymany od Ani. Posłanie – kupione przez Młodego – było naprawdę fajne, wyglądało na wygodne, choć osobiście tego nie sprawdzałem. Kocyk zaś Elf znał, pachniał mu znajomo i miałem nadzieję, że pomoże psiakowi w zaadaptowaniu się do nowego miejsca."
# s2 = "Potema rozcięliłem w nowym logowisku jego kocyk, również otrzymany od Ani. Posłanie, kupione przez młodego, było naprawdę fajne. Wyglądało na wygodne, choć osobiście tego nie sprawdzałem. Kocyk zaś Elf znał, pachniał mu znajomo i miałam nadzieję, że pomoże psiakowi w zaadoptowaniu się do nowego miejsca."
#
# score, operations = str_levenshtein_distance(s1, s2)
#
# print(f"Expected distance: {", ".join([repr(o) for o in operations])}")
#
# mb = make_list_of_matched_substrings(s1, operations)
#
# for m in mb:
#     print(m)
