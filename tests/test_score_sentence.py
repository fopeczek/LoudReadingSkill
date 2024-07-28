from core import score_sentence


def test_scoring(reference: str, user: str, expected: list[int | bool]):
    ans, words = score_sentence(reference, reference, user)
    if words != [bool(x) for x in expected]:
        print(
            f"Error: «{reference}» vs «{user}»: expected {expected}, got {[int(x) for x in words]} errors at positions {[i for i, x in enumerate(expected) if x != words[i]]}"
        )
    else:
        print(f"OK: Reference: {reference}")


def test_respeak(correct: str, respeak: str, user: str, expected: list[bool | int]):
    ans, words = score_sentence(correct, respeak, user)
    if words != [bool(x) for x in expected]:
        print(
            f"Error: «{correct}»/{respeak} vs «{user}»: expected {expected}, got {[int(x) for x in words]} errors at positions {[i for i, x in enumerate(expected) if x != words[i]]}"
        )
    else:
        print(f"OK: Reference: {correct}")


def test():
    test_scoring("ab", "ac", [0])
    test_scoring("ba", "ca", [0])

    test_scoring("12345", "1x2345", [1])  # 80% is correct
    test_scoring("12345", "2345", [1])  # 80% is correct
    test_scoring("12345", "345", [0])  # less than 80% is correct
    test_scoring("12345", "1234", [1])

    test_scoring("123 abc def", "12X3 abc def", [0, 1, 1])
    test_scoring("123 abc def", "123 abc def", [1, 1, 1])
    test_scoring("123 abc def", "123abc def", [0, 0, 1])
    test_scoring("123 abc def", "123 XXX abc def", [1, 1, 1])

    test_scoring("123 abcdefghijklm 12 1234", "1234", [0, 0, 0, 1])
    test_scoring("123 abcdefghijklm 12 1234", "", [0, 0, 0, 0])
    test_scoring("123 abcdefghijklm 12 1234", "123", [1, 0, 0, 0])
    test_scoring("123 abcdefghijklm 12 1234", "abcdefghijklm", [0, 1, 0, 0])

    test_scoring("123 abcdefghijklm 12", "123 aXbcdeXghijkXm 12", [1, 0, 1])
    test_scoring("123 abcdefghijklm 12", "123 Xabcdefghijklm 12", [1, 1, 1])
    test_scoring("123 abcdefghijklm 12", "123X Xabcdefghijklm 12", [1, 1, 1])
    test_scoring("123 abcdefghijklm 12", "123 XabcdefghijklmX 12", [1, 1, 1])
    test_scoring("123 abcdefghijklm 12", "123 XabcdefghijklmX X12", [1, 1, 1])
    test_scoring("123 abcdefgh 12 1234", "123 abcXXXX 1234", [1, 0, 0, 1])
    test_scoring("123 1234567 12 1234", "123 1234567 12 1234", [1, 1, 1, 1])
    test_scoring(
        "123 abcdefgh 12 abcd 987654 ABCDEFGHIJ xyz",
        "123 abcdXefgh 12 abcd987654 ABCDEFGHIJ xyz",
        [1, 0, 1, 0, 0, 1, 1],
    )
    test_scoring("Ala ma kota", "Ala ma psa", [1, 1, 0])

    test_scoring(
        "Człowiek jest silniejszy, kiedy stawia czoła wyzwaniom. To odwaga napędza nas do działania.",
        "Człowiek jest silniejszy, kiedy stawia czoła wyzwaniom do odwagi napędza nas do działania.",
        [1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1],
    )


def respeak():
    test_respeak(
        "Życie to jak jazda na rowerze. Aby utrzymać równowagę, musisz się poruszać.",
        "Życie to jak jazda na rowerze. Aby utrzymać równowagę, musisz ją poruszać.",
        "Życie to jak jazda na rowerze. Aby utrzymać równowagę musisz się poruszać.",
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    )
    test_respeak("123", "1x3", "1x3", [1])
    test_respeak("123 456 789", "123 4x5 789", "123 4x5 789", [1, 1, 1])
    test_respeak("123", "123", "123", [1])


if __name__ == "__main__":
    # test()
    respeak()
