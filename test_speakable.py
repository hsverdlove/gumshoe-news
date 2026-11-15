#!/usr/bin/env python3
"""Unit checks for speakable() text normalizations in make_bulletin.py."""
import unittest
from make_bulletin import (
    speakable, soften_stress_caps, soften_commas, normalize_initialisms, join_wrapped_lines,
)

class SpeakableTests(unittest.TestCase):
    def test_initialisms_dotted_and_spaced(self):
        s = speakable("The U.S. and the U.S.A. asked the F.B.I. and the D.O.J., along with the C.I.A., to look into it.")
        self.assertIn("The US and the USA", s)
        self.assertIn("the FBI and the DOJ", s)
        self.assertIn("the CIA", s)
        self.assertNotIn("U.S.", s)
        self.assertNotIn("F.B.I.", s)

    def test_spaced_script_style(self):
        s = speakable("The F A A and the F B I, plus the C E O and an A I model, and the F C C.")
        self.assertIn("The FAA and the FBI", s)
        self.assertIn("the CEO and an AI model", s)
        self.assertIn("the FCC", s)
        self.assertNotIn("F A A", s)
        self.assertNotIn("A I", s)

    def test_us_not_confused_with_pronoun(self):
        s = speakable("The US asked us to visit the U.S. Embassy.")
        self.assertIn("The US asked us to visit the US Embassy", s)
        # pronoun stays lowercase us
        self.assertIn("asked us to", s)

    def test_word_acronyms_stay_words(self):
        s = speakable("NATO skipped the summit, NASA launched, and OPEC cut production.")
        self.assertIn("NATO", s)
        self.assertIn("NASA", s)
        self.assertIn("OPEC", s)
        # dotted form should compact to the word
        self.assertEqual(speakable("N.A.T.O. skipped it."), "NATO skipped it.")

    def test_sentence_period_after_us(self):
        s = speakable("He flew to the U.S. The FBI followed.")
        self.assertIn("the US. The FBI followed.", s)

    def test_hegseth_from_pronunciations(self):
        s = speakable("Defense Secretary Pete Hegseth spoke today.")
        self.assertNotRegex(s, r"HEG")
        self.assertNotRegex(s, r"H, E, G")
        # hyphenated lowercase respelling, or plain name, but not caps stress
        self.assertTrue("heg-seth" in s or "Hegseth" in s, s)

    def test_hegseth_hyphen_stress_token(self):
        s = soften_stress_caps("Pete HEG-seth spoke.")
        self.assertEqual(s, "Pete heg-seth spoke.")

    def test_legit_camelcase_preserved(self):
        s = speakable("She bought an iPhone. McDonald opened. OpenAI and CoreWeave and VMware and PCMag all rose.")
        self.assertIn("iPhone", s)
        self.assertIn("McDonald", s)
        self.assertIn("OpenAI", s)
        self.assertIn("CoreWeave", s)
        self.assertIn("VMware", s)
        self.assertIn("PCMag", s)

    def test_anthropic_and_robotaxi(self):
        s = speakable("Anthropic is testing a robotaxi and a robo-taxi and Robotaxis.")
        self.assertIn("An-thropic", s)
        self.assertIn("robo-taxi", s)
        # no regression to an-THROP-ic style
        self.assertNotIn("THROP", s)

    def test_hyphen_stress_lowercased(self):
        self.assertEqual(soften_stress_caps("Pete HEG-seth spoke"), "Pete heg-seth spoke")
        self.assertEqual(soften_stress_caps("Goo-TEH-resh said kah-SAY-ah"), "Goo-teh-resh said kah-say-ah")
        # letter spellings with spaces stay
        self.assertEqual(soften_stress_caps("O V H cloud and B T C Pay"), "O V H cloud and B T C Pay")

    def test_city_state(self):
        self.assertEqual(speakable("First, the York, ME forecast."), "First, the York Maine forecast.")
        self.assertEqual(speakable("Here's your Londonderry, NH forecast."), "Here's your Londonderry New Hampshire forecast.")
        self.assertEqual(speakable("First, the York, Maine forecast."), "First, the York Maine forecast.")
        self.assertIn("Portland Maine man", speakable("a Portland, Maine man refused"))
        self.assertIn("Washington DC", speakable("In Washington, D.C. today"))
        # clause comma after a city-like word that is NOT city-state must stay
        s = speakable("In Washington, a federal judge paused it.")
        self.assertIn("In Washington, a federal judge", s)

    def test_list_commas(self):
        self.assertEqual(
            speakable("We packed apples, oranges, and pears."),
            "We packed apples oranges and pears.",
        )
        self.assertEqual(
            speakable("We packed apples, oranges and pears."),
            "We packed apples oranges and pears.",
        )

    def test_clause_commas_kept(self):
        s = speakable("The open question, which she pressed him on, is still unanswered.")
        self.assertIn("question, which she pressed him on, is", s)
        s = speakable("I'm Ava, with Andrew at the desk.")
        self.assertIn("Ava, with Andrew", s)

    def test_newlines_joined(self):
        s = speakable("First, the York, Maine forecast\nthrough tomorrow.")
        self.assertNotIn("\n", s)
        self.assertIn("forecast through tomorrow", s)

    def test_weather_list_like(self):
        s = speakable("Monday, sunny, high near 50.")
        self.assertEqual(s, "Monday sunny high near 50.")


    def test_clause_and_appositive_commas_kept(self):
        s = speakable("The Park Service says it can't safely manage the park after the course operator leaves, pointing to staffing and a damaged seawall.")
        self.assertIn("leaves, pointing to staffing", s)
        s = speakable("The men, two brothers and their brother-in-law, were convicted of terrorism charges.")
        self.assertIn("The men, two brothers and their brother-in-law, were convicted", s)
        s = speakable("He said Fetterman may be, in his words, looking for an exit ramp.")
        self.assertIn("may be, in his words, looking", s)
        s = speakable("Ukraine's foreign minister, Andrii Sybiha, mocked Putin today.")
        self.assertIn("foreign minister, Andrii", s)
        self.assertIn(", mocked Putin", s)
        s = speakable("After meetings in Manila, he's due in Shenzhen, China, for the Asia-Pacific summit.")
        self.assertIn("China, for", s)
        self.assertIn(", China,", s)
        s = speakable("the announcers overlapped or failed, cues were missed, and there was dead air, with humans standing in.")
        self.assertIn("failed, cues were missed, and there was dead air,", s)
        s = speakable("A system in Amarillo, Texas, that was upgraded about three weeks ago then started doing the same thing.")
        self.assertIn("Texas, that was upgraded", s)
        self.assertNotIn(", Texas,", s)

    def test_verb_list_still_softened(self):
        # 1-2 word items with and: "seawalls, streets and walls" would drop; verb-led items should stay
        s = speakable("We packed apples, oranges, and pears at the market.")
        self.assertIn("apples oranges and pears", s)

if __name__ == "__main__":
    unittest.main()
