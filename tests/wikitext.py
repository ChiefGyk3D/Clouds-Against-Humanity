# SPDX-License-Identifier: Apache-2.0
"""Read a wiki page without its generated navigation blocks (issue #417).

scripts/gen_wiki_nav.py writes a navigation block at the top and the bottom of every page: links to the
page's track, its previous and next page and related pages. That is navigation, not lesson content, so a test that
counts the links a page makes, names pages it must NOT link, or looks at the first lines of a page reads the page
through this helper and sees what the author wrote. Since issue #441 the longest pages also carry a generated
contents block (links to the page's own headings); it is stripped too. The stripping itself is
gen_wiki_nav.strip_generated, tested in tests/test_wiki_page_nav.py and tests/test_wiki_page_contents.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import gen_wiki_nav


def page_text(path: Path) -> str:
    """The text of a wiki page file with the generated navigation blocks and the contents block removed."""
    return gen_wiki_nav.strip_generated(Path(path).read_text(encoding="utf-8"))
