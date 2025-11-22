"""Tests for the PasswordStore module."""

import pytest
from hoarder.passwords import PasswordStore
from typeguard import suppress_type_checks


@pytest.fixture(scope="function")
def password_store():
    return PasswordStore()


def test_init(password_store: PasswordStore):
    """Test initialization and default value"""
    assert isinstance(
        password_store._store, dict  # pyright: ignore[reportPrivateUsage]
    )
    assert password_store["nonexistent"] == set()


def test_add_password_single(password_store: PasswordStore):
    """Test simple addition of password"""
    password_store.add_password("title1", "password1")

    passwords = password_store["title1"]
    assert len(passwords) == 1
    assert "password1" in passwords


def test_add_password_multiple_same_title(password_store: PasswordStore):
    """Test adding multiple passwords for the same title"""
    password_store.add_password("title1", "password1")
    password_store.add_password("title1", "password2")
    password_store.add_password("title1", "password3")

    passwords = password_store["title1"]
    assert len(passwords) == 3
    assert {"password1", "password2", "password3"} == passwords


def test_add_password_duplicate(password_store: PasswordStore):
    """Test adding a duplicate entry"""
    password_store.add_password("title1", "password1")
    password_store.add_password("title1", "password1")  # Duplicate

    passwords = password_store["title1"]
    assert len(passwords) == 1
    assert "password1" in passwords


def test_add_password_multiple_titles(password_store: PasswordStore):
    password_store.add_password("title1", "password1")
    password_store.add_password("title2", "password2")
    password_store.add_password("title3", "password3")

    assert password_store["title1"] == {"password1"}
    assert password_store["title2"] == {"password2"}
    assert password_store["title3"] == {"password3"}


def test_getitem_returns_copy(password_store: PasswordStore):
    """Test that __getitem__ returns a copy, not reference to internal set."""
    password_store.add_password("title1", "password1")

    passwords1 = password_store["title1"]
    passwords2 = password_store["title1"]

    # Should be equal but not the same object
    assert passwords1 == passwords2
    assert passwords1 is not passwords2

    # Modifying returned set shouldn't affect store
    passwords1.add("new_password")
    assert "new_password" not in password_store["title1"]


def test_getitem_nonexistent_title(password_store: PasswordStore):
    """Test accessing passwords for non-existent title."""
    passwords = password_store["nonexistent"]
    assert passwords == set()
    assert isinstance(passwords, set)


def test_remove_password_success(password_store: PasswordStore):
    """Test successfully removing an existing password."""
    password_store.add_password("title1", "password1")
    password_store.add_password("title1", "password2")

    result = password_store.remove_password("title1", "password1")
    assert result is True
    assert password_store["title1"] == {"password2"}


def test_remove_password_last_password_removes_title(password_store: PasswordStore):
    """Test removing the last password removes the title entirely."""
    password_store.add_password("title1", "password1")

    result = password_store.remove_password("title1", "password1")
    assert result is True
    assert "title1" not in password_store._store  # pyright: ignore[reportPrivateUsage]
    assert (
        password_store["title1"] == set()
    )  # Should return empty set for non-existent title


def test_remove_password_nonexistent_title(password_store: PasswordStore):
    """Test removing password from non-existent title."""
    result = password_store.remove_password("nonexistent", "password1")
    assert result is False


def test_remove_password_nonexistent_password(password_store: PasswordStore):
    """Test removing non-existent password from existing title."""
    password_store.add_password("title1", "password1")

    result = password_store.remove_password("title1", "nonexistent_password")
    assert result is False
    assert password_store["title1"] == {"password1"}  # Should remain unchanged


def test_iteration_empty_store(password_store: PasswordStore):
    """Test iteration over empty password store."""
    items = list(password_store)
    assert items == []


def test_iteration_with_data(password_store: PasswordStore):
    """Test iteration over password store with data."""
    password_store.add_password("title1", "password1")
    password_store.add_password("title1", "password2")
    password_store.add_password("title2", "password3")

    items = list(password_store)
    assert len(items) == 2

    # Convert to dict for easier testing
    result_dict = dict(items)
    assert result_dict["title1"] == {"password1", "password2"}
    assert result_dict["title2"] == {"password3"}


@pytest.fixture(scope="function")
def password_store_2():
    """Separate fixture for second password store."""
    return PasswordStore()


def test_or_operator_empty_stores(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test combining two empty password stores."""
    combined = password_store | password_store_2
    assert isinstance(combined, PasswordStore)
    assert list(combined) == []


def test_or_operator_one_empty(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test combining empty store with populated store."""
    password_store_2.add_password("title1", "password1")

    combined = password_store | password_store_2
    assert len(combined["title1"]) == 1
    assert combined["title1"] == {"password1"}
    assert len(password_store_2) == 1
    assert password_store_2["title1"] == {"password1"}

    # Test reverse combination
    combined_reverse = password_store_2 | password_store
    assert combined_reverse["title1"] == {"password1"}


def test_or_operator_non_overlapping(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test combining stores with non-overlapping titles."""
    password_store.add_password("title1", "password1")
    password_store_2.add_password("title2", "password2")

    combined = password_store | password_store_2
    assert combined["title1"] == {"password1"}
    assert combined["title2"] == {"password2"}


def test_or_operator_overlapping_titles(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test combining stores with overlapping titles."""
    password_store.add_password("title1", "password1")
    password_store.add_password("title1", "password2")

    password_store_2.add_password("title1", "password2")  # Duplicate
    password_store_2.add_password("title1", "password3")  # New

    combined = password_store | password_store_2
    assert combined["title1"] == {"password1", "password2", "password3"}


def test_or_operator_does_not_modify_originals(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test that | operator doesn't modify original stores."""
    password_store.add_password("title1", "password1")
    password_store_2.add_password("title2", "password2")

    combined = password_store | password_store_2

    # Original stores should be unchanged
    assert password_store["title1"] == {"password1"}
    assert password_store["title2"] == set()
    assert password_store_2["title1"] == set()
    assert password_store_2["title2"] == {"password2"}

    # Combined store should have both
    assert combined["title1"] == {"password1"}
    assert combined["title2"] == {"password2"}


def test_clear_passwords_existing_title(password_store: PasswordStore):
    """Test clearing passwords for an existing title."""
    password_store.add_password("title1", "password1")
    password_store.add_password("title1", "password2")
    password_store.add_password("title2", "password3")

    password_store.clear_passwords("title1")

    assert password_store["title1"] == set()
    # Note: title1 key still exists in defaultdict but with empty set
    assert password_store["title2"] == {"password3"}  # Other titles unaffected


def test_clear_passwords_nonexistent_title(password_store: PasswordStore):
    """Test clearing passwords for non-existent title (should not raise error)."""
    password_store.add_password("title1", "password1")

    # Should not raise an exception
    password_store.clear_passwords("nonexistent")

    # Original data should be unchanged
    assert password_store["title1"] == {"password1"}


def test_empty_strings(password_store: PasswordStore):
    """Test handling of empty strings for titles and passwords."""

    # Empty title with password
    with pytest.raises(ValueError):
        password_store.add_password("", "password1")

    # Title with empty password
    with pytest.raises(ValueError):
        password_store.add_password("title1", "")

    # Both empty
    with pytest.raises(ValueError):
        password_store.add_password("", "")


def test_init_with_data():
    """Test initialization with existing data."""
    data = {
        "title1": {"password1", "password2"},
        "title2": {"password3"},
    }
    store = PasswordStore(data)

    assert store["title1"] == {"password1", "password2"}
    assert store["title2"] == {"password3"}
    assert len(store) == 2


def test_init_with_data_creates_copies():
    """Test that initialization creates copies of the input data."""
    original_passwords = {"password1", "password2"}
    data = {"title1": original_passwords}
    store = PasswordStore(data)

    # Modifying original shouldn't affect store
    original_passwords.add("password3")
    assert store["title1"] == {"password1", "password2"}
    assert "password3" not in store["title1"]


def test_init_with_empty_dict():
    """Test initialization with empty dictionary."""
    store = PasswordStore({})
    assert len(store) == 0
    assert list(store) == []


def test_contains_existing_title(password_store: PasswordStore):
    """Test __contains__ with existing title."""
    password_store.add_password("title1", "password1")
    assert "title1" in password_store


def test_contains_nonexistent_title(password_store: PasswordStore):
    """Test __contains__ with non-existent title."""
    assert "nonexistent" not in password_store


def test_contains_after_removal(password_store: PasswordStore):
    """Test __contains__ after removing all passwords for a title."""
    password_store.add_password("title1", "password1")
    assert "title1" in password_store

    password_store.remove_password("title1", "password1")
    assert "title1" not in password_store


def test_len_empty_store(password_store: PasswordStore):
    """Test __len__ on empty store."""
    assert len(password_store) == 0


def test_len_with_data(password_store: PasswordStore):
    """Test __len__ with data."""
    password_store.add_password("title1", "password1")
    assert len(password_store) == 1

    password_store.add_password("title2", "password2")
    assert len(password_store) == 2

    password_store.add_password("title1", "password3")  # Same title
    assert len(password_store) == 2  # Should still be 2 titles


def test_len_after_removal(password_store: PasswordStore):
    """Test __len__ after removing passwords."""
    password_store.add_password("title1", "password1")
    password_store.add_password("title2", "password2")
    assert len(password_store) == 2

    password_store.remove_password("title1", "password1")
    assert len(password_store) == 1


def test_iteration_returns_copies(password_store: PasswordStore):
    """Test that iteration returns copies, not references."""
    password_store.add_password("title1", "password1")

    items = list(password_store)
    assert len(items) == 1

    title, passwords = items[0]
    # Modifying returned set shouldn't affect store
    passwords.add("new_password")
    assert "new_password" not in password_store["title1"]


def test_ior_operator_empty_stores(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test in-place union with two empty stores."""
    password_store |= password_store_2
    assert len(password_store) == 0
    assert isinstance(password_store, PasswordStore)


def test_ior_operator_one_empty(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test in-place union with one empty store."""
    password_store_2.add_password("title1", "password1")

    password_store |= password_store_2
    assert password_store["title1"] == {"password1"}
    assert len(password_store) == 1


def test_ior_operator_non_overlapping(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test in-place union with non-overlapping titles."""
    password_store.add_password("title1", "password1")
    password_store_2.add_password("title2", "password2")

    password_store |= password_store_2
    assert password_store["title1"] == {"password1"}
    assert password_store["title2"] == {"password2"}
    assert len(password_store) == 2


def test_ior_operator_overlapping_titles(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test in-place union with overlapping titles."""
    password_store.add_password("title1", "password1")
    password_store.add_password("title1", "password2")

    password_store_2.add_password("title1", "password2")  # Duplicate
    password_store_2.add_password("title1", "password3")  # New

    password_store |= password_store_2
    assert password_store["title1"] == {"password1", "password2", "password3"}


def test_ior_operator_modifies_original(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test that |= operator modifies the left operand."""
    password_store.add_password("title1", "password1")
    password_store_2.add_password("title2", "password2")

    original_id = id(password_store)
    password_store |= password_store_2

    # Should be same object (modified in place)
    assert id(password_store) == original_id
    assert password_store["title1"] == {"password1"}
    assert password_store["title2"] == {"password2"}


def test_ior_operator_does_not_modify_right_operand(
    password_store: PasswordStore, password_store_2: PasswordStore
):
    """Test that |= operator doesn't modify the right operand."""
    password_store.add_password("title1", "password1")
    password_store_2.add_password("title2", "password2")

    password_store |= password_store_2

    # Right operand should be unchanged
    assert password_store_2["title1"] == set()
    assert password_store_2["title2"] == {"password2"}


@suppress_type_checks
def test_add_password_type_error_title(password_store: PasswordStore):
    """Test that add_password raises TypeError for non-string title."""
    with pytest.raises(TypeError, match="title must be str"):
        password_store.add_password(
            123, "password1"
        )  # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError, match="title must be str"):
        password_store.add_password(
            None, "password1"
        )  # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError, match="title must be str"):
        password_store.add_password(
            ["title"], "password1"
        )  # pyright: ignore[reportArgumentType]


@suppress_type_checks
def test_add_password_type_error_password(password_store: PasswordStore):
    """Test that add_password raises TypeError for non-string password."""
    with pytest.raises(TypeError, match="password must be str"):
        password_store.add_password(
            "title1", 123
        )  # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError, match="password must be str"):
        password_store.add_password(
            "title1", None
        )  # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError, match="password must be str"):
        password_store.add_password(
            "title1", ["password"]
        )  # pyright: ignore[reportArgumentType]


def test_clear_passwords_removes_from_store(password_store: PasswordStore):
    """Test that clear_passwords actually removes the title from internal store."""
    password_store.add_password("title1", "password1")
    password_store.add_password("title1", "password2")

    assert "title1" in password_store._store  # pyright: ignore[reportPrivateUsage]
    password_store.clear_passwords("title1")
    assert "title1" not in password_store._store  # pyright: ignore[reportPrivateUsage]
