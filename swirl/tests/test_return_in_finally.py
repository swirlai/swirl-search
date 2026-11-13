"""
DS-5742: no `return` inside `finally` (Python 3.14 SyntaxWarning, PEP 765).

Two guards:
  1. Static: the tree compiles with SyntaxWarning promoted to an error, so
     the idiom cannot creep back in (a future Python makes it a SyntaxError).
  2. Behavioural: `finally: return` used to swallow exceptions raised inside
     the `except` handler itself. The live case was get_text_for_query's
     handler calling the non-existent `logger.err`, so every failure there
     raised AttributeError which the `finally` hid. With the fix the handler
     logs via logger.error and the function still returns its default.
"""

import ast
import pathlib
import warnings
from unittest.mock import MagicMock, patch

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
CHANGED = [
    'swirl.py',
    'swirl/rag_prompt.py',
    'swirl/tasks.py',
    'swirl/utils.py',
    'swirl/web_page.py',
]


@pytest.mark.parametrize('rel', CHANGED)
def test_no_return_in_finally_syntax_warning(rel):
    src = (REPO / rel).read_text()
    with warnings.catch_warnings():
        warnings.simplefilter('error', SyntaxWarning)
        compile(src, rel, 'exec')  # raises SyntaxWarning-as-error on `return` in `finally`


def test_tree_has_no_return_in_finally():
    paths = [p for p in REPO.glob('*.py')]
    for base in ('swirl', 'swirl_server', 'DevUtils'):
        paths += [p for p in (REPO / base).rglob('*.py') if 'migrations' not in p.parts]
    offenders = []
    for p in paths:
        try:
            tree = ast.parse(p.read_text(), str(p))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Try) and node.finalbody:
                for stmt in node.finalbody:
                    if any(isinstance(n, (ast.Return, ast.Break, ast.Continue)) for n in ast.walk(stmt)):
                        offenders.append(f'{p.relative_to(REPO)}:{stmt.lineno}')
    assert offenders == [], offenders


def test_get_text_for_query_failure_is_logged_not_swallowed():
    from swirl import web_page as wp

    response = MagicMock()
    response.url = 'https://example.com/doc'
    page = wp.DocumentWebPage(response)
    with patch.object(page, 'get_text', side_effect=RuntimeError('boom')), \
         patch.object(wp, 'logger') as log:
        out = page.get_text_for_query('q')

    assert out == ''
    assert log.error.called, 'handler must log via logger.error (was logger.err, an AttributeError)'
    assert 'boom' in log.error.call_args.args[0]


def test_html_to_text_returns_empty_string_on_parser_failure():
    from swirl import web_page as wp

    page = wp.DocumentWebPage(MagicMock())
    with patch.object(wp, 'BeautifulSoup', side_effect=RuntimeError('boom')):
        assert page.html_to_text('<p>hello</p>', skip_summary=True) == ''


def test_safe_urlparse_returns_none_on_bad_input():
    from swirl.utils import safe_urlparse
    assert safe_urlparse(object()) is None
