"""Offline tests: no API key, no network. Run: python -m unittest discover tests"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINT = ROOT / "scripts" / "tag_lint.py"
sys.path.insert(0, str(ROOT / "scripts"))
import ab  # noqa: E402


def lint(text: str, *args: str) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
    r = subprocess.run([sys.executable, str(LINT), f.name, *args], capture_output=True, text=True, encoding="utf-8")
    Path(f.name).unlink()
    return r.returncode, r.stdout


class TagLint(unittest.TestCase):
    def test_examples_pass(self):
        for name in ("reel-fa.txt", "reel-en.txt"):
            code, out = lint((ROOT / "examples" / name).read_text(encoding="utf-8"))
            self.assertEqual(code, 0, out)
            self.assertNotRegex(out, r"(?m)^(WARN|ERROR)", out)

    def test_language_detection(self):
        self.assertIn("lang fa", lint("سلام! این یه تسته.")[1])
        self.assertIn("lang en", lint("[excited] This is a test!")[1])

    def test_over_tagging_is_an_error(self):
        code, out = lint("[excited] One!\n[laughs] Two!\n[sighs] Three.\n")
        self.assertEqual(code, 1)
        self.assertIn("Over-tagged", out)

    def test_three_stacked_tags(self):
        self.assertIn("three tags stacked", lint("[excited] [laughs] [shouting] Now!\n" + "Plain line.\n" * 10)[1])

    def test_ssml_on_v4_and_tags_on_v2(self):
        self.assertIn("has no SSML", lint('Wait <break time="1s"/> now.\n')[1])
        code, out = lint("[excited] Hello there.\n", "--model", "eleven_multilingual_v2")
        self.assertEqual(code, 1)
        self.assertIn("reads [tags] aloud", out)

    def test_written_laughter_and_greeting(self):
        out = lint("Hey guys, welcome.\nThat was funny haha.\n")[1]
        self.assertIn("written laughter", out)
        self.assertIn("opens with a greeting", out)
        out = lint("سلام دوستان.\nخیلی باحال بود هاها.\n")[1]
        self.assertIn("written laughter", out)
        self.assertIn("opens with a greeting", out)

    def test_laughs_too_close(self):
        text = "[laughs] A.\n" + "Line.\n" * 3 + "[chuckles] B.\n" + "Line.\n" * 10
        self.assertIn("apart", lint(text)[1])

    def test_staging_tag(self):
        self.assertIn("staging", lint("[music] Go.\n" + "Line.\n" * 5)[1])

    def test_beat_labels_required(self):
        code, out = lint("[excited] Wait, this ends Friday!\n")
        self.assertEqual(code, 1)
        self.assertIn("no beat label", out)
        self.assertEqual(lint("Wait, this ends Friday.   # HOOK 5\n")[0], 0)
        self.assertEqual(lint("Plain narration.\n", "--no-beats")[0], 0)

    def test_arc_rules(self):
        self.assertIn("opens on a HOOK", lint("Some setup.   # SETUP 3\n")[1])
        out = lint("[excited] Wait!   # HOOK 5\n[whispers] Here's the trick...   # TIP 4\nit works.   # TIP 3\n")[1]
        self.assertIn("low tag needs a low beat", out)
        self.assertIn("does not lift the energy", out)

    def test_register_and_interjections(self):
        out = lint("برای دریافت لینک این را بخوانید که مهم است.   # HOOK 4\n")[1]
        self.assertIn("«را» is written register", out)
        self.assertIn("«است» is written register", out)
        self.assertIn("is written register", lint("It is not what you are thinking!   # HOOK 5\n")[1])

    def test_persian_readings(self):
        with tempfile.TemporaryDirectory() as d:
            lex = Path(d) / "lex.tsv"
            lex.write_text("بالاخره\tبِلاخَرِه\tguess\n", encoding="utf-8")
            out = lint("وای! بالاخره اومد!   # HOOK 5\n", "--lexicon", str(lex))[1]
            self.assertIn("long «ا/آ» 2 -> 1", out)
            lex.write_text("بالاخره\tبِلَخَرِه\t✓ confirmed by ear\n", encoding="utf-8")
            self.assertNotIn("reading not confirmed", lint("وای! بالاخره اومد!   # HOOK 5\n", "--lexicon", str(lex))[1])
        out = lint("وای! حتی فوق‌العاده بود، دقیقاً!   # HOOK 5\n")[1]
        self.assertIn("«حتی»", out)
        self.assertIn("«فوق‌العاده»", out)
        self.assertIn("tanwin", out)
        self.assertIn("«یه» -> «یا»", lint("وای! {یه|یا} چیز!   # HOOK 5\n")[1])

    def test_ab_plan_and_budget(self):
        out = lint("[excited] Wait!   # HOOK 5\n[whispers] The trick...   # TIP 2\nIt works!   # TIP 3\nComment now.   # CTA 4\n",
                   "--ab-budget", "20")[1]
        self.assertIn("A/B PLAN", out)
        self.assertIn("1. line 1   hook", out)
        self.assertIn("first [whispers]", out)
        self.assertIn("OVER BUDGET", out)

    def test_approval_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            s = Path(d) / "script.txt"
            s.write_text("Wait, this ends Friday.   # HOOK 5\n", encoding="utf-8")
            run = lambda *a: subprocess.run([sys.executable, str(LINT), str(s), *a], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run("--check-approved").returncode, 3)
            self.assertEqual(run("--approve").returncode, 0)
            self.assertEqual(run("--check-approved").returncode, 0)
            s.write_text("Wait, this ends Sunday.   # HOOK 5\n", encoding="utf-8")
            self.assertEqual(run("--check-approved").returncode, 3)
            s.write_text("[excited] Wait!\n", encoding="utf-8")
            self.assertNotEqual(run("--approve").returncode, 0)  # an ERROR (no beat label) blocks approval

    def test_strip_beats(self):
        import tag_lint
        self.assertEqual(tag_lint.strip_beats("# note\nHi there!   # HOOK 5\nNext.  # SETUP 3"), "Hi there!\nNext.")


class AB(unittest.TestCase):
    def test_respell_skips_tags_and_partial_words(self):
        lex = [("اپ", "اَپْ"), ("excited", "WRONG")]
        self.assertEqual(ab.respell("[excited] اپ و اپی", lex), "[excited] اَپْ و اپی")

    def test_listen_for_unconfirmed_readings(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ab.py"), "وای! بالاخره اومد!", "--out", d, "--dry-run"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertIn("LISTEN FOR «بالاخره»", r.stdout)

    def test_leak_detection(self):
        self.assertEqual(ab.leaks("[laughs] hi", "laughs hi"), ["laughs"])
        self.assertEqual(ab.leaks("[laughs] hi", "[laughter] hi"), [])
        self.assertEqual(ab.leaks("[whispers] hi", "(whispering) hi"), [])

    def test_dry_run_sends_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ab.py"), "[excited] Hi!", "Hi.", "--stability", "0.3",
                                "--stability", "0.5", "--out", d, "--dry-run"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("4 clips, 32 characters", r.stdout)
            self.assertEqual(list(Path(d).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
