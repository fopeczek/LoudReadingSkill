from core import score_sentence


def test_scoring(reference: str, user: str, expected: list[int | bool]):
    (
        score_respeak,
        score_correct,
        flag_correct,
        words_correct,
        correct2respeak_map,
        words_respeak,
    ) = score_sentence(reference, reference, user)
    words = words_correct if flag_correct else words_respeak

    if words != [bool(x) for x in expected]:
        print(
            f"Error: «{reference}» vs «{user}»: expected {expected}, got {[int(x) for x in words]} errors at positions {[i for i, x in enumerate(expected) if x != words[i]]}"
        )
    else:
        print(f"OK: Reference: {reference}")


def test_respeak(correct: str, respeak: str, user: str, expected: list[bool | int]):
    (
        ans_respeak,
        ans_correct,
        correct_flag,
        words_correct,
        respeak_map,
        words_respeak,
    ) = score_sentence(correct, respeak, user)
    words = words_correct if correct_flag else words_respeak
    if words != [bool(x) for x in expected]:
        print(
            f"Error: «{correct}»/{respeak} vs «{user}»: expected {expected}, got {[int(x) for x in words]} errors at positions {[i for i, x in enumerate(expected) if x != words[i]]}"
        )
    else:
        print(f"OK: Reference: {correct}")


def test():
    test_respeak(
        "— Dziewiętnastego grudnia — podpowiedział klient Pozytywka.",
        "19 grudnia podpowiedział klient pozytywka.",
        "19 grudnia podpowiedział klient pozytywka.",
        [1, 1, 1, 1, 1, 1, 1, 1],
    )
    test_scoring(
        "Spojrzałem, gdzie mi wskazał oczami i ruchem głowy, za siebie. O jakieś trzysta metrów od nas leciał w dół starszy jegomość w binoklach, z wyglądu szanowny profesor uniwersytetu. W objęciach trzymał dziką, górską kozicę, która wyrywała się, wierzgając kopytami i rogami bodąc powietrze. Widocznie złapał się jej w locie, jak my krzewu  i razem z nią spadał w dalszym ciągu, ale powodowany bezsensowną nadzieją nie wypuszczał kozicy z objęć mimo jej oporu",
        "   Spojrzałem, gdzie mi wskazał oczami   ruchem głowy  za siebie. O jakieś trzysta metrów od nas leciał w dół starszy jegomość w binoklach, z wyglądu szanowny profesor uniwersytetu. W objęciach trzymał dziką, górską kozicę, która wyrywała się, wierzgając kopytami i rogami budąc powietrze. Widocznie złapał się jej w locie, jak my krzewu, i razem z nią spadał w dalszym ciągu. Ale powodowane bezsensowną nadzieją nie wypuszczał kozicy z objęć, mimo jej oporu.",
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    )

    test_scoring("bezmyślność", "pozmyślność", [0])
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
        "Nie ma się czym przejmować! Jakbyśmy siedzieli sobie gdzie przy stoliku w kawiarni! Głupota czy bezmyślność?",
        "Nie ma się czym przejmować. Jakbyśmy siedzieli sobie gdzie przy stoliku w kawiarni. Upota czy bezmyślność?",
        "Nie ma się czym przejmować, jakbyśmy siedzieli sobie gdzie przy stoliku w kawiarni. Głupota czy pozmyślność?",
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    )
    test_respeak(
        "Patrząc w dół wyczekiwałem okazji. Ukazał się krzew kosodrzewiny. Wyciągnąłem ręce i kiedy zrównałem się z nim - uchwyciłem. Szarpnęło, trzasnęło i oto lecę z krzakiem kosodrzewiny trzymanym oburącz, jakbym wybierał się z wizytą niosąc absurdalny bukiet.",
        "Patrząc w dół, wyczekiwałem okazji. Okazał się krzew kosobrzewiny. Wyciągnąłem ręce i kiedy zrównałem się z nim, uchwyciłem. Karpnęło, trzasnęło i oto lecył sprzakiem kosobrzewiny trzymanym obu rącz, jakbym wybierał się z wizytą niosąc absurdalny bukiet.",
        "Patrząc w dół, wyczekiwałem okazji. Uka... ukazał się krzewy koz... koz drzewiny. Drzewiny. Wyciągnąłem ręce i kiedy zroz... zrównąłem się z nim, uchwyciłem. Sz... szary pnęło, wszy wyrzasnęło i oto lecę z krzewkiem. Koz drzewiny. Koz drzewiny. Trzymałem. Zostawiam obu... obu rączki. Jak bym wybierał się z wizytą insyni... insyni... insyni... do surd... absur... Absur... Absurdalny bukiet.",
        [1, 1, 1, 1, 1, 1, 1, 1],
    )
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
    test()
    # respeak()
