from .base import Result, run_pyright


def test_client_generic_returns_a_response() -> None:
    """A test sends a verb the Client has no named helper for - PATCH, or a
    content-type negotiation case - via client.generic().

    Client overrides get/post/head/options/put/patch/delete/trace to return a
    response, but not generic(), so it inherited RequestFactory.generic() and the
    result typed as a WSGIRequest. Every .status_code and .content on it was then
    an unknown attribute of a request object.
    """
    results = run_pyright(
        """\
from django.test import Client

client = Client()
response = client.generic("PATCH", "/x/", data=b"{}", content_type="application/json")
reveal_type(response.status_code)
"""
    )
    assert [r for r in results if r.type == "error"] == []


def test_url_patterns_is_heterogeneous() -> None:
    """A URL-introspection helper walks the resolver tree to enumerate routes.

    include() nests a URLResolver inside url_patterns, so walking it means
    branching on URLResolver vs URLPattern. The stub declared the list as
    list[tuple[str, Callable]], which matches neither.
    """
    results = run_pyright(
        """\
from django.urls import get_resolver
from django.urls.resolvers import URLResolver

for entry in get_resolver().url_patterns:
    if isinstance(entry, URLResolver):
        reveal_type(entry.namespace)
    else:
        reveal_type(entry.name)
"""
    )
    assert [r for r in results if r.type == "error"] == []


def test_multivaluedict_getitem_returns_the_value() -> None:
    """A view reads a single query parameter and converts it.

    QueryDict[...] returns the last value for the key; getlist() is the API that
    returns every value. The stub returned the union of both, so int(params["pk"])
    was rejected on the list arm that subscripting never produces.
    """
    results = run_pyright(
        """\
from django.http import QueryDict

def read(params: QueryDict) -> int:
    return int(params["pk"])
"""
    )
    assert [r for r in results if r.type == "error"] == []


def test_streaming_response_accepts_str_chunks() -> None:
    """A view streams rendered text - SSE, CSV, NDJSON - a chunk at a time.

    StreamingHttpResponse encodes str chunks itself, so yielding str is ordinary
    usage, but the stub accepted only bytes.
    """
    results = run_pyright(
        """\
from django.http import StreamingHttpResponse

StreamingHttpResponse(iter(["a", "b"]))
"""
    )
    assert [r for r in results if r.type == "error"] == []


def test_session_payload_is_heterogeneous() -> None:
    """Code reads the logged-in user's id straight off a decoded session.

    django.contrib.auth writes that key as a str via pk.value_to_string, while
    other keys hold ints (_session_expiry) - the payload is heterogeneous by
    construction, and the stub declared dict[str, int], wrong for every key
    Django itself writes.
    """
    results = run_pyright(
        """\
from django.contrib.sessions.base_session import AbstractBaseSession

def owner(session: AbstractBaseSession) -> str:
    user_id: str = session.get_decoded()["_auth_user_id"]
    return user_id
"""
    )
    assert [r for r in results if r.type == "error"] == []


def test_refresh_from_db_takes_any_iterable() -> None:
    """A caller refreshes a named subset of fields, passing a tuple.

    The field names are a fixed set at the call site, so a tuple is the natural
    literal; the stub required list[str] specifically.
    """
    results = run_pyright(
        """\
from django.db import models

class Foo(models.Model):
    pass

Foo().refresh_from_db(fields=("a", "b"))
"""
    )
    assert [r for r in results if r.type == "error"] == []
