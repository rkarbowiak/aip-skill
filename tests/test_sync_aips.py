"""Unit tests for tools/sync_aips.py. Run with: python -m unittest discover -s tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import sync_aips  # noqa: E402
from sync_aips import Aip  # noqa: E402


def aip(number: int, title: str) -> Aip:
    a = Aip(id=number, scope="general", state="approved", category="fields", order=0, title=title, body="")
    a.filename = f"{number:04d}-{sync_aips.slugify(title)}.md"
    return a


LOCAL = {142: aip(142, "Time and duration"), 180: aip(180, "Backwards compatibility")}


class RewriteTarget(unittest.TestCase):
    def test_every_upstream_spelling_of_a_local_aip(self):
        for target in ["./0142.md", "./0142", "../0142.md", "/142", "https://aip.dev/142", "https://google.aip.dev/142"]:
            with self.subTest(target=target):
                self.assertEqual(sync_aips.rewrite_target(target, LOCAL), "0142-time-and-duration.md")

    def test_anchor_is_kept(self):
        self.assertEqual(
            sync_aips.rewrite_target("../0180.md#semantic-changes", LOCAL),
            "0180-backwards-compatibility.md#semantic-changes",
        )

    def test_aip_not_bundled_points_at_the_site(self):
        self.assertEqual(sync_aips.rewrite_target("./0162.md#x", LOCAL), "https://google.aip.dev/162#x")

    def test_site_relative_and_external_links(self):
        self.assertEqual(sync_aips.rewrite_target("/assets/misc/ebnf.txt", LOCAL), "https://google.aip.dev/assets/misc/ebnf.txt")
        self.assertEqual(sync_aips.rewrite_target("https://google.aip.dev/client-libraries/4232", LOCAL), "https://google.aip.dev/client-libraries/4232")
        self.assertEqual(sync_aips.rewrite_target("#guidance", LOCAL), "#guidance")

    def test_rewrite_links_handles_inline_and_reference_links(self):
        body = "See [time](./0142.md) and [compat][].\n\n[compat]: /180\n"
        out = sync_aips.rewrite_links(body, LOCAL)
        self.assertIn("[time](0142-time-and-duration.md)", out)
        self.assertIn("[compat]: 0180-backwards-compatibility.md", out)


class FrontMatter(unittest.TestCase):
    def test_nested_keys_are_flattened(self):
        meta, body = sync_aips.parse_front_matter(
            "---\nid: 158\nstate: approved\nplacement:\n  category: design-patterns\n  order: 60\n---\n\n# Pagination\n"
        )
        self.assertEqual(meta["id"], "158")
        self.assertEqual(meta["placement.category"], "design-patterns")
        self.assertTrue(body.startswith("# Pagination"))


class Summaries(unittest.TestCase):
    def test_prefers_first_guidance_sentence(self):
        body = "Intro sentence. More.\n\n## Guidance\n\nAPIs **must** do `x_y`. Then more.\n\n## Rationale\n\nWhy.\n"
        self.assertEqual(sync_aips.summarize(body), "APIs must do x_y.")

    def test_skips_code_and_intro_dependent_sentences(self):
        body = "Masks select fields.\n\n## Guidance\n\n```proto\nmessage A {}\n```\n\nThese masks are called masks.\n"
        self.assertEqual(sync_aips.summarize(body), "Masks select fields.")

    def test_numbered_rule_is_used_and_e_g_does_not_split(self):
        body = "Intro.\n\n## Guidance\n\n1.  APIs **must** use e.g. `expire_time` here. Next.\n"
        self.assertEqual(sync_aips.summarize(body), "APIs must use e.g. expire_time here.")


class Anchors(unittest.TestCase):
    def test_github_style(self):
        self.assertEqual(sync_aips.github_anchor("Status.message"), "statusmessage")
        self.assertEqual(sync_aips.github_anchor("HTTP/1.1+JSON representation"), "http11json-representation")
        self.assertEqual(sync_aips.github_anchor("`display_name`"), "display_name")

    def test_check_links_reports_missing_anchor_only(self):
        docs = {"a.md": "## Guidance\n\n[ok](#guidance) [bad](#nope) [x](b.md#there)\n", "b.md": "## There\n"}
        self.assertEqual(sync_aips.check_links(docs), ["a.md: link to missing anchor #nope (upstream issue)"])


if __name__ == "__main__":
    unittest.main()
