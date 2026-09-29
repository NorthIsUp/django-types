from typing import ClassVar, TypeVar

from django.db import models
from typing_extensions import Self, assert_type

_M = TypeVar("_M", bound=models.Model)


class LiveManager(models.Manager["Article"]):
    def live(self) -> models.QuerySet["Article"]:
        return self.filter(published=True)


class Article(models.Model):
    published = models.BooleanField()

    objects: ClassVar[LiveManager] = LiveManager()


class AuditManager(models.Manager[_M]):
    def audited(self) -> models.QuerySet[_M]:
        return self.all()


class AuditedBase(models.Model):
    objects: ClassVar[AuditManager[Self]] = AuditManager()

    class Meta:
        abstract = True


class Note(AuditedBase): ...


class Plain(models.Model): ...


def check_manager_overrides() -> None:
    # A model's own manager narrows Model.objects without an override conflict.
    assert_type(Article.objects.live(), models.QuerySet[Article])
    assert_type(Note.objects.audited(), models.QuerySet[Note])
    # Models without one get Django's default Manager, specialised to the model.
    assert_type(Plain.objects, models.Manager[Plain])
    assert_type(Plain.objects.get(), Plain)
