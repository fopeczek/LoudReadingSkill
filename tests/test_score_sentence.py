from core.scoring import score_sentence


def test_scoring(reference: str, user: str, expected: float):
    ans = score_sentence(reference, user)
    if ans[0] != expected:
        print(f"Error: expected {expected}, got {ans[0]}")
    print(ans[1])


def test():
    test_scoring("123 abc def", "123 abc def", 1)
    test_scoring("123 abc def", "12X3 abc def", 2 / 3)
    test_scoring("123 abc def", "123abc def", 1 / 3)
    test_scoring("123 abc def", "123 XXX abc def", 1 / 3)

    test_scoring(
        "123 abcdefgh 12 abcd 987654 ABCDEFGHIJ xyz",
        "123 abcdXefgh 12 abcd987654 ABCDEFGHIJ xyz",
        4 / 7,
    )
    test_scoring("123 abcdefghijklm 12 1234", "1234", 1 / 4)
    test_scoring("123 abcdefghijklm 12 1234", "", 0 / 4)
    test_scoring("123 abcdefghijklm 12 1234", "abcdefghijklm", 1 / 4)
    test_scoring("123 abcdefghijklm 12 1234", "123", 1 / 4)

    test_scoring("123 abcdefghijklm 12", "123 aXbcdeXghijkXm 12", 2 / 3)
    test_scoring("123 abcdefghijklm 12", "123 Xabcdefghijklm 12", 2 / 3)
    test_scoring("123 abcdefghijklm 12", "123X Xabcdefghijklm 12", 1 / 3)
    test_scoring("123 abcdefghijklm 12", "123 XabcdefghijklmX 12", 2 / 3)
    test_scoring("123 abcdefghijklm 12", "123 XabcdefghijklmX X12", 1 / 3)
    test_scoring("123 abcdefgh 12 1234", "123 abcXXXX 1234", 2 / 4)
    test_scoring("123 1234567 12 1234", "123 1234567 12 1234", 4 / 4)

    test_scoring("Ala ma kota", "Ala ma psa", 2 / 3)
    test_scoring(
        "Człowiek jest silniejszy, kiedy stawia czoła wyzwaniom. To odwaga napędza nas do działania.",
        "Człowiek jest silniejszy, kiedy stawia czoła wyzwaniom do odwagi napędza nas do działania.",
        11 / 13,
    )


if __name__ == "__main__":
    test()
