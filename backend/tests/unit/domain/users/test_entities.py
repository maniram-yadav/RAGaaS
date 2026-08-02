"""Unit tests for the `User` domain entity."""

from __future__ import annotations

from uuid import UUID

from app.domain.users.entities import Role, User


def test_user_generates_a_unique_id_by_default() -> None:
    first = User(email="a@example.com", hashed_password="h", name="A")
    second = User(email="b@example.com", hashed_password="h", name="B")

    assert isinstance(first.id, UUID)
    assert first.id != second.id


def test_user_defaults_role_to_member_and_org_id_to_none() -> None:
    user = User(email="a@example.com", hashed_password="h", name="A")

    assert user.role == "member"
    assert user.org_id is None


def test_user_created_at_and_updated_at_default_to_now() -> None:
    user = User(email="a@example.com", hashed_password="h", name="A")

    assert user.created_at is not None
    assert user.updated_at is not None


def test_user_accepts_explicit_role_and_org_id() -> None:
    user = User(
        email="a@example.com", hashed_password="h", name="A", role="admin", org_id="org-1"
    )

    assert user.role == "admin"
    assert user.org_id == "org-1"


def test_user_default_role_is_the_role_member_enum_member() -> None:
    user = User(email="a@example.com", hashed_password="h", name="A")

    assert user.role is Role.MEMBER


def test_role_enum_has_admin_member_owner_and_matches_plain_strings() -> None:
    assert {r.value for r in Role} == {"admin", "member", "owner"}
    assert Role.ADMIN == "admin"
    assert Role.MEMBER == "member"
    assert Role.OWNER == "owner"


def test_user_accepts_a_role_enum_member_explicitly() -> None:
    user = User(email="a@example.com", hashed_password="h", name="A", role=Role.OWNER)

    assert user.role == Role.OWNER
    assert user.role == "owner"
