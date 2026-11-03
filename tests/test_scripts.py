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
            self.assertNotIn("WARN", out, out)

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


class AB(unittest.TestCase):
    def test_respell_skips_tags_and_partial_words(self):
        lex = [("کلش", "کِلَشْ"), ("excited", "WRONG")]
        self.assertEqual(ab.respell("[excited] کلش و کلشی", lex), "[excited] کِلَشْ و کلشی")

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
