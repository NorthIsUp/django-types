from .base import Result, run_pyright


def test_foreign_key_lazy_string_reference() -> None:
    """A model points at another app's model by name to avoid an import cycle.

    ForeignKey("other.Thing", ...) is the documented way to do that, but the
    string carries no type to solve the model var from. Left unsolved on the
    null=True overload it collapsed the whole field to None - so every read of
    it errored, and the field read as *absent* rather than *unknown*, which
    looks exactly like an unguarded nullable FK in the application.

    Any, rather than a narrower base like Model: the target is only knowable at
    runtime, and Model would reject every field access the related model
    actually has - `f.lazy_required.title` below is the ordinary use, and it is
    what a base-class annotation could not support.
    """
    results = run_pyright(
        """\
from django.db import models

class Foo(models.Model):
    lazy_nullable = models.ForeignKey("other.Thing", on_delete=models.CASCADE, null=True)
    lazy_required = models.ForeignKey("other.Thing", on_delete=models.CASCADE)

f = Foo()
reveal_type(f.lazy_nullable)
reveal_type(f.lazy_required)
name: str = f.lazy_required.title
"""
    )
    assert results == [
        Result(type="information", message='Type of "f.lazy_nullable" is "Any"', line=8, column=13),
        Result(type="information", message='Type of "f.lazy_required" is "Any"', line=9, column=13),
    ]


def test_unparameterized_json_field() -> None:
    """A model stores a free-form JSON blob and does not parameterise the field.

    models.JSONField() with no type argument is the common case. Without a
    default on the field's type var it was left unsolved, so every read and
    every assignment through the descriptor errored.

    Any, rather than a JSON union: one JSONField column legitimately holds an
    object, an array, a scalar or null - all four are assigned below - and
    reads index arbitrarily deep into whatever shape was stored. A dict-shaped
    default would reject three of the four assignments.
    """
    results = run_pyright(
        """\
from django.db import models

class Foo(models.Model):
    data = models.JSONField()
    maybe = models.JSONField(null=True)

f = Foo()
reveal_type(f.data)
f.data = {"a": 1}
f.data = [1, 2, 3]
f.data = "a string is valid json"
f.data = None
count: int = f.data["items"][0]["qty"]
"""
    )
    assert results == [
        Result(type="information", message='Type of "f.data" is "Any"', line=8, column=13),
    ]


def test_file_field_accepts_a_file_on_assignment() -> None:
    """Code assigns an in-memory file to a FileField - a test fixture, or a
    document generated at runtime.

    The descriptor is asymmetric: assignment takes a File or a path str, reads
    give back the FieldFile descriptor. The stub used the descriptor type on
    both sides, so assigning a ContentFile or SimpleUploadedFile was rejected.
    """
    results = run_pyright(
        """\
from django.core.files.base import ContentFile
from django.db import models

class Foo(models.Model):
    doc = models.FileField(upload_to="docs/")

f = Foo()
f.doc = ContentFile(b"x", name="x.txt")
f.doc = "docs/x.txt"
"""
    )
    assert results == []


def test_field_max_length_reads_as_optional() -> None:
    """Introspection code reads max_length off a field and guards for None.

    Fields that set no max_length - TextField, and CharField itself wherever the
    backend reports supports_unlimited_charfield - leave it None, and Django's
    own cast_db_type and description branch on that. The stub declared the
    attribute as int, which makes the guard look like dead code.
    """
    results = run_pyright(
        """\
from django.db.models import Field

def check(field: Field) -> None:
    reveal_type(field.max_length)
"""
    )
    assert results == [
        Result(type="information", message='Type of "field.max_length" is "int | None"', line=4, column=17),
    ]


def test_foreign_key_lazy_reference_can_be_parameterised() -> None:
    """A codebase that wants precision annotates the lazy reference explicitly.

    Any is the fallback, not a ceiling: ForeignKey[Thing]("app.Thing", ...) -
    with Thing imported under TYPE_CHECKING, which is what avoids the cycle the
    string reference existed for - still resolves to Thing, and composes with
    null=True. The default only applies when the call site says nothing.
    """
    results = run_pyright(
        """\
from django.db import models

class Thing(models.Model):
    title = models.CharField(max_length=10)

class Foo(models.Model):
    untyped = models.ForeignKey("app.Thing", on_delete=models.CASCADE)
    typed = models.ForeignKey[Thing]("app.Thing", on_delete=models.CASCADE)
    typed_null = models.ForeignKey[Thing | None]("app.Thing", on_delete=models.CASCADE, null=True)

f = Foo()
reveal_type(f.untyped)
reveal_type(f.typed)
reveal_type(f.typed_null)
"""
    )
    assert results == [
        Result(type="information", message='Type of "f.untyped" is "Any"', line=12, column=13),
        Result(type="information", message='Type of "f.typed" is "Thing"', line=13, column=13),
        Result(type="information", message='Type of "f.typed_null" is "Thing | None"', line=14, column=13),
    ]
