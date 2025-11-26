"""Tests for the PasswordStoreRepository module."""

import pathlib

import pytest
from hoarder.passwords import PasswordSqlite3Repository, PasswordStore


@pytest.fixture(scope="function")
def temp_db_path(tmp_path):
    """Create a temporary database path for each test."""
    return tmp_path / "test_passwords.db"


@pytest.fixture(scope="function")
def password_repo(temp_db_path):
    """Create a PasswordSqlite3Repository instance for each test."""
    return PasswordSqlite3Repository(temp_db_path)


def test_init_creates_tables(temp_db_path):
    """Test that initialization creates the database tables."""
    _ = PasswordSqlite3Repository(temp_db_path)

    # Verify database file exists
    assert temp_db_path.exists()

    # Verify tables exist by trying to query them
    from hoarder.utils import Sqlite3FK

    with Sqlite3FK(temp_db_path) as con:
        cur = con.cursor()
        # Check titles table exists
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='titles';"
        )
        assert cur.fetchone() is not None

        # Check passwords table exists
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='passwords';"
        )
        assert cur.fetchone() is not None


def test_init_with_string_path(tmp_path):
    """Test that initialization works with string path."""
    db_path = str(tmp_path / "test.db")
    _ = PasswordSqlite3Repository(db_path)
    assert pathlib.Path(db_path).exists()


def test_save_empty_store(password_repo: PasswordSqlite3Repository):
    """Test saving an empty PasswordStore."""
    store = PasswordStore()
    password_repo.save(store)

    # Should not raise an error
    loaded = password_repo.load()
    assert len(loaded) == 0


def test_save_and_load_single_title_single_password(
    password_repo: PasswordSqlite3Repository,
):
    """Test saving and loading a store with one title and one password."""
    store = PasswordStore()
    store.add_password("title1", "password1")

    password_repo.save(store)
    loaded = password_repo.load()

    assert len(loaded) == 1
    assert "title1" in loaded
    assert loaded["title1"] == {"password1"}


def test_save_and_load_single_title_multiple_passwords(
    password_repo: PasswordSqlite3Repository,
):
    """Test saving and loading a store with one title and multiple passwords."""
    store = PasswordStore()
    store.add_password("title1", "password1")
    store.add_password("title1", "password2")
    store.add_password("title1", "password3")

    password_repo.save(store)
    loaded = password_repo.load()

    assert len(loaded) == 1
    assert "title1" in loaded
    assert loaded["title1"] == {"password1", "password2", "password3"}


def test_save_and_load_multiple_titles(
    password_repo: PasswordSqlite3Repository,
):
    """Test saving and loading a store with multiple titles."""
    store = PasswordStore()
    store.add_password("title1", "password1")
    store.add_password("title2", "password2")
    store.add_password("title3", "password3")

    password_repo.save(store)
    loaded = password_repo.load()

    assert len(loaded) == 3
    assert loaded["title1"] == {"password1"}
    assert loaded["title2"] == {"password2"}
    assert loaded["title3"] == {"password3"}


def test_save_and_load_complex_store(
    password_repo: PasswordSqlite3Repository,
):
    """Test saving and loading a complex store with multiple titles and passwords."""
    store = PasswordStore()
    store.add_password("title1", "password1")
    store.add_password("title1", "password2")
    store.add_password("title2", "password3")
    store.add_password("title2", "password4")
    store.add_password("title2", "password5")
    store.add_password("title3", "password6")

    password_repo.save(store)
    loaded = password_repo.load()

    assert len(loaded) == 3
    assert loaded["title1"] == {"password1", "password2"}
    assert loaded["title2"] == {"password3", "password4", "password5"}
    assert loaded["title3"] == {"password6"}


def test_save_duplicate_title_ignored(
    password_repo: PasswordSqlite3Repository,
):
    """Test that saving the same title twice doesn't create duplicates."""
    store1 = PasswordStore()
    store1.add_password("title1", "password1")

    store2 = PasswordStore()
    store2.add_password("title1", "password2")

    password_repo.save(store1)
    password_repo.save(store2)

    loaded = password_repo.load()
    # Should have both passwords for the same title
    assert len(loaded) == 1
    assert loaded["title1"] == {"password1", "password2"}


def test_save_duplicate_password_ignored(
    password_repo: PasswordSqlite3Repository,
):
    """Test that saving the same password twice for a title is ignored."""
    store = PasswordStore()
    store.add_password("title1", "password1")

    password_repo.save(store)
    password_repo.save(store)  # Save again

    loaded = password_repo.load()
    assert len(loaded) == 1
    assert loaded["title1"] == {"password1"}


def test_save_appends_passwords(
    password_repo: PasswordSqlite3Repository,
):
    """Test that saving appends passwords rather than replacing."""
    store1 = PasswordStore()
    store1.add_password("title1", "password1")

    store2 = PasswordStore()
    store2.add_password("title1", "password2")
    store2.add_password("title2", "password3")

    password_repo.save(store1)
    password_repo.save(store2)

    loaded = password_repo.load()
    assert len(loaded) == 2
    assert loaded["title1"] == {"password1", "password2"}
    assert loaded["title2"] == {"password3"}


def test_load_empty_database(password_repo: PasswordSqlite3Repository):
    """Test loading from an empty database."""
    loaded = password_repo.load()
    assert isinstance(loaded, PasswordStore)
    assert len(loaded) == 0


def test_save_and_load_preserves_order(
    password_repo: PasswordSqlite3Repository,
):
    """Test that load returns titles in sorted order."""
    store = PasswordStore()
    store.add_password("zebra", "password1")
    store.add_password("alpha", "password2")
    store.add_password("beta", "password3")

    password_repo.save(store)
    loaded = password_repo.load()

    # Titles should be in sorted order when iterating
    titles = [title for title, _ in loaded]
    assert titles == ["alpha", "beta", "zebra"]


def test_save_with_existing_data_from_dict(
    password_repo: PasswordSqlite3Repository,
):
    """Test saving a PasswordStore initialized from a dictionary."""
    data = {
        "title1": {"password1", "password2"},
        "title2": {"password3"},
    }
    store = PasswordStore(data)

    password_repo.save(store)
    loaded = password_repo.load()

    assert len(loaded) == 2
    assert loaded["title1"] == {"password1", "password2"}
    assert loaded["title2"] == {"password3"}


def test_round_trip_multiple_operations(
    password_repo: PasswordSqlite3Repository,
):
    """Test multiple save/load operations maintain consistency."""
    # First save
    store1 = PasswordStore()
    store1.add_password("title1", "password1")
    password_repo.save(store1)

    loaded1 = password_repo.load()
    assert loaded1["title1"] == {"password1"}

    # Second save - add more
    store2 = PasswordStore()
    store2.add_password("title1", "password2")
    store2.add_password("title2", "password3")
    password_repo.save(store2)

    loaded2 = password_repo.load()
    assert loaded2["title1"] == {"password1", "password2"}
    assert loaded2["title2"] == {"password3"}

    # Third save - add to existing title
    store3 = PasswordStore()
    store3.add_password("title1", "password4")
    password_repo.save(store3)

    loaded3 = password_repo.load()
    assert loaded3["title1"] == {"password1", "password2", "password4"}
    assert loaded3["title2"] == {"password3"}


def test_load_returns_new_instance(
    password_repo: PasswordSqlite3Repository,
):
    """Test that load returns a new PasswordStore instance."""
    store = PasswordStore()
    store.add_password("title1", "password1")
    password_repo.save(store)

    loaded1 = password_repo.load()
    loaded2 = password_repo.load()

    # Should be different instances
    assert loaded1 is not loaded2
    # But should have same content
    assert loaded1["title1"] == loaded2["title1"]


def test_save_with_special_characters(
    password_repo: PasswordSqlite3Repository,
):
    """Test saving and loading titles and passwords with special characters."""
    store = PasswordStore()
    store.add_password("title with spaces", "password with spaces")
    store.add_password("title'with'quotes", "password'with'quotes")
    store.add_password('title"with"double', 'password"with"double')
    store.add_password("title\nwith\nnewlines", "password\nwith\nnewlines")

    password_repo.save(store)
    loaded = password_repo.load()

    assert len(loaded) == 4
    assert loaded["title with spaces"] == {"password with spaces"}
    assert loaded["title'with'quotes"] == {"password'with'quotes"}
    assert loaded['title"with"double'] == {'password"with"double'}
    assert loaded["title\nwith\nnewlines"] == {"password\nwith\nnewlines"}


def test_save_with_unicode_characters(
    password_repo: PasswordSqlite3Repository,
):
    """Test saving and loading titles and passwords with unicode characters."""
    store = PasswordStore()
    store.add_password("título", "contraseña")
    store.add_password("タイトル", "パスワード")
    store.add_password("заголовок", "пароль")

    password_repo.save(store)
    loaded = password_repo.load()

    assert len(loaded) == 3
    assert loaded["título"] == {"contraseña"}
    assert loaded["タイトル"] == {"パスワード"}
    assert loaded["заголовок"] == {"пароль"}


def test_create_tables_idempotent(temp_db_path):
    """Test that _create_tables can be called multiple times safely."""
    PasswordSqlite3Repository._create_tables(temp_db_path)
    PasswordSqlite3Repository._create_tables(temp_db_path)
    PasswordSqlite3Repository._create_tables(temp_db_path)

    # Should not raise an error and tables should exist
    from hoarder.utils import Sqlite3FK

    with Sqlite3FK(temp_db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='titles';"
        )
        assert cur.fetchone() is not None
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='passwords';"
        )
        assert cur.fetchone() is not None

