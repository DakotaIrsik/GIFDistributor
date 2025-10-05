"""
Comprehensive Tests for Upload Module (Issue #15)
Tests file deduplication, hashing, upload management, and storage
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from io import BytesIO
from upload import (
    FileHasher,
    DeduplicationStore,
    UploadManager,
    FileMetadata,
    UploadSession,
    UploadStatus,
    hash_file,
    check_duplicate,
)


class TestFileHasher:
    """Test cases for FileHasher class"""

    def test_hash_file_basic(self, tmp_path):
        """Test basic file hashing"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Hello, World!")

        file_hash = FileHasher.hash_file(str(test_file))

        assert len(file_hash) == 64  # SHA-256 produces 64 hex chars
        assert file_hash.isalnum()
        # Known SHA-256 of "Hello, World!"
        assert (
            file_hash
            == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        )

    def test_hash_file_consistency(self, tmp_path):
        """Test that same content produces same hash"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"consistent content")

        hash1 = FileHasher.hash_file(str(test_file))
        hash2 = FileHasher.hash_file(str(test_file))

        assert hash1 == hash2

    def test_hash_file_different_content(self, tmp_path):
        """Test that different content produces different hashes"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_bytes(b"content A")
        file2.write_bytes(b"content B")

        hash1 = FileHasher.hash_file(str(file1))
        hash2 = FileHasher.hash_file(str(file2))

        assert hash1 != hash2

    def test_hash_file_large_file(self, tmp_path):
        """Test hashing large file with chunking"""
        test_file = tmp_path / "large.bin"
        # Create 10MB file
        large_content = b"X" * (10 * 1024 * 1024)
        test_file.write_bytes(large_content)

        file_hash = FileHasher.hash_file(str(test_file))

        assert len(file_hash) == 64
        assert file_hash.isalnum()

    def test_hash_file_custom_chunk_size(self, tmp_path):
        """Test hashing with custom chunk size"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"chunk test content")

        hash1 = FileHasher.hash_file(str(test_file), chunk_size=4)
        hash2 = FileHasher.hash_file(str(test_file), chunk_size=8192)

        # Should produce same hash regardless of chunk size
        assert hash1 == hash2

    def test_hash_bytes(self):
        """Test hashing byte data"""
        data = b"test data"
        file_hash = FileHasher.hash_bytes(data)

        assert len(file_hash) == 64
        assert file_hash.isalnum()

    def test_hash_bytes_consistency(self):
        """Test byte hashing consistency"""
        data = b"consistent bytes"
        hash1 = FileHasher.hash_bytes(data)
        hash2 = FileHasher.hash_bytes(data)

        assert hash1 == hash2

    def test_hash_stream(self):
        """Test hashing from stream"""
        data = b"stream data content"
        stream = BytesIO(data)

        file_hash = FileHasher.hash_stream(stream)

        assert len(file_hash) == 64
        assert file_hash.isalnum()

    def test_hash_stream_consistency(self):
        """Test stream hashing produces consistent results"""
        data = b"consistent stream"

        stream1 = BytesIO(data)
        stream2 = BytesIO(data)

        hash1 = FileHasher.hash_stream(stream1)
        hash2 = FileHasher.hash_stream(stream2)

        assert hash1 == hash2

    def test_quick_hash_small_file(self, tmp_path):
        """Test quick hash for small file"""
        test_file = tmp_path / "small.txt"
        test_file.write_bytes(b"small file content")

        quick_hash = FileHasher.quick_hash(str(test_file))

        assert len(quick_hash) == 64
        assert quick_hash.isalnum()

    def test_quick_hash_large_file(self, tmp_path):
        """Test quick hash for large file (header + footer)"""
        test_file = tmp_path / "large.bin"
        # Create 5MB file
        large_content = b"A" * (5 * 1024 * 1024)
        test_file.write_bytes(large_content)

        quick_hash = FileHasher.quick_hash(str(test_file))

        assert len(quick_hash) == 64
        assert quick_hash.isalnum()

    def test_quick_hash_custom_sample_size(self, tmp_path):
        """Test quick hash with custom sample size"""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"X" * (3 * 1024 * 1024))

        hash1 = FileHasher.quick_hash(str(test_file), sample_size=512)
        hash2 = FileHasher.quick_hash(str(test_file), sample_size=1024)

        # Different sample sizes should produce different hashes
        assert hash1 != hash2

    def test_empty_file_hash(self, tmp_path):
        """Test hashing empty file"""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        file_hash = FileHasher.hash_file(str(test_file))

        # SHA-256 of empty string
        assert (
            file_hash
            == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )


class TestDeduplicationStore:
    """Test cases for DeduplicationStore"""

    def test_init_new_database(self, tmp_path):
        """Test initializing new database"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        # Database file is not created until first save (lazy initialization)
        assert not os.path.exists(db_path)
        assert store.db == {"files": {}, "uploads": {}}

    def test_init_existing_database(self, tmp_path):
        """Test loading existing database"""
        db_path = str(tmp_path / "existing.json")

        # Create initial database
        initial_data = {
            "files": {"hash123": {"file_hash": "hash123", "filename": "test.gif"}},
            "uploads": {},
        }
        with open(db_path, "w") as f:
            json.dump(initial_data, f)

        # Load database
        store = DeduplicationStore(db_path)

        assert "hash123" in store.db["files"]
        assert store.db["files"]["hash123"]["filename"] == "test.gif"

    def test_is_duplicate_false(self, tmp_path):
        """Test checking for non-existent duplicate"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        assert not store.is_duplicate("nonexistent_hash")

    def test_is_duplicate_true(self, tmp_path):
        """Test detecting existing duplicate"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        metadata = FileMetadata(
            file_hash="test_hash_123",
            filename="test.gif",
            size_bytes=1024,
            mime_type="image/gif",
            upload_time="2025-01-01T00:00:00",
        )
        store.add_file(metadata)

        assert store.is_duplicate("test_hash_123")

    def test_get_file_metadata_exists(self, tmp_path):
        """Test retrieving existing file metadata"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        metadata = FileMetadata(
            file_hash="hash456",
            filename="example.gif",
            size_bytes=2048,
            mime_type="image/gif",
            upload_time="2025-01-01T00:00:00",
            user_id="user123",
        )
        store.add_file(metadata)

        retrieved = store.get_file_metadata("hash456")

        assert retrieved is not None
        assert retrieved.file_hash == "hash456"
        assert retrieved.filename == "example.gif"
        assert retrieved.size_bytes == 2048
        assert retrieved.user_id == "user123"

    def test_get_file_metadata_not_exists(self, tmp_path):
        """Test retrieving non-existent metadata"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        retrieved = store.get_file_metadata("nonexistent")

        assert retrieved is None

    def test_add_file(self, tmp_path):
        """Test adding file metadata"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        metadata = FileMetadata(
            file_hash="newhash",
            filename="new.gif",
            size_bytes=512,
            mime_type="image/gif",
            upload_time="2025-01-01T00:00:00",
            title="New GIF",
            tags=["tag1", "tag2"],
        )
        store.add_file(metadata)

        # Verify it's in database
        assert store.is_duplicate("newhash")

        # Verify database file was written
        with open(db_path, "r") as f:
            db_data = json.load(f)
        assert "newhash" in db_data["files"]

    def test_remove_file_exists(self, tmp_path):
        """Test removing existing file"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        metadata = FileMetadata(
            file_hash="removeme",
            filename="remove.gif",
            size_bytes=100,
            mime_type="image/gif",
            upload_time="2025-01-01T00:00:00",
        )
        store.add_file(metadata)

        result = store.remove_file("removeme")

        assert result is True
        assert not store.is_duplicate("removeme")

    def test_remove_file_not_exists(self, tmp_path):
        """Test removing non-existent file"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        result = store.remove_file("doesntexist")

        assert result is False

    def test_get_all_files(self, tmp_path):
        """Test retrieving all files"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        for i in range(3):
            metadata = FileMetadata(
                file_hash=f"hash{i}",
                filename=f"file{i}.gif",
                size_bytes=i * 100,
                mime_type="image/gif",
                upload_time="2025-01-01T00:00:00",
            )
            store.add_file(metadata)

        all_files = store.get_all_files()

        assert len(all_files) == 3
        assert all(isinstance(f, FileMetadata) for f in all_files)

    def test_get_user_files(self, tmp_path):
        """Test retrieving files for specific user"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        # Add files for different users
        for i, user in enumerate(["user1", "user2", "user1"]):
            metadata = FileMetadata(
                file_hash=f"hash_{user}_{i}",
                filename=f"{user}_file.gif",
                size_bytes=1000,
                mime_type="image/gif",
                upload_time="2025-01-01T00:00:00",
                user_id=user,
            )
            store.add_file(metadata)

        user1_files = store.get_user_files("user1")

        assert len(user1_files) == 2
        assert all(f.user_id == "user1" for f in user1_files)

    def test_get_stats_empty(self, tmp_path):
        """Test statistics for empty store"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        stats = store.get_stats()

        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["unique_users"] == 0
        assert stats["avg_file_size_mb"] == 0

    def test_get_stats_with_files(self, tmp_path):
        """Test statistics with files"""
        db_path = str(tmp_path / "test.json")
        store = DeduplicationStore(db_path)

        # Add 3 files totaling 3MB
        for i in range(3):
            metadata = FileMetadata(
                file_hash=f"hash{i}",
                filename=f"file{i}.gif",
                size_bytes=1024 * 1024,  # 1MB each
                mime_type="image/gif",
                upload_time="2025-01-01T00:00:00",
                user_id=f"user{i % 2}",  # 2 unique users
            )
            store.add_file(metadata)

        stats = store.get_stats()

        assert stats["total_files"] == 3
        assert stats["total_size_bytes"] == 3 * 1024 * 1024
        assert stats["total_size_mb"] == 3.0
        assert stats["unique_users"] == 2
        assert stats["avg_file_size_mb"] == 1.0


class TestUploadManager:
    """Test cases for UploadManager"""

    def test_init_default(self, tmp_path):
        """Test default initialization"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        assert os.path.exists(storage_dir)
        assert manager.storage_dir == storage_dir
        assert manager.dedupe_store is not None

    def test_init_custom_dedupe_store(self, tmp_path):
        """Test initialization with custom dedupe store"""
        storage_dir = str(tmp_path / "uploads")
        db_path = str(tmp_path / "custom_dedupe.json")
        dedupe_store = DeduplicationStore(db_path)

        manager = UploadManager(storage_dir=storage_dir, dedupe_store=dedupe_store)

        assert manager.dedupe_store == dedupe_store

    def test_check_duplicate_no_duplicate(self, tmp_path):
        """Test checking non-duplicate file"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "test.gif"
        test_file.write_bytes(b"unique content")

        is_dup, metadata = manager.check_duplicate(str(test_file))

        assert not is_dup
        assert metadata is None

    def test_check_duplicate_is_duplicate(self, tmp_path):
        """Test detecting duplicate file"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        # Upload file first time
        test_file = tmp_path / "test.gif"
        test_file.write_bytes(b"content to duplicate")

        success, msg, metadata = manager.upload_file(str(test_file))
        assert success

        # Check for duplicate
        is_dup, dup_metadata = manager.check_duplicate(str(test_file))

        assert is_dup
        assert dup_metadata is not None
        assert dup_metadata.file_hash == metadata.file_hash

    def test_upload_file_success(self, tmp_path):
        """Test successful file upload"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "upload.gif"
        content = b"GIF content here"
        test_file.write_bytes(content)

        success, msg, metadata = manager.upload_file(
            str(test_file),
            filename="custom.gif",
            mime_type="image/gif",
            user_id="user123",
            title="Test Upload",
            tags=["test", "upload"],
            description="Test description",
        )

        assert success
        assert "successfully" in msg.lower()
        assert metadata is not None
        assert metadata.filename == "custom.gif"
        assert metadata.user_id == "user123"
        assert metadata.title == "Test Upload"
        assert metadata.tags == ["test", "upload"]
        assert metadata.description == "Test description"
        assert metadata.size_bytes == len(content)

    def test_upload_file_not_found(self, tmp_path):
        """Test uploading non-existent file"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        success, msg, metadata = manager.upload_file("/nonexistent/file.gif")

        assert not success
        assert "not found" in msg.lower()
        assert metadata is None

    def test_upload_file_duplicate_rejected(self, tmp_path):
        """Test that duplicate upload is rejected"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "dup.gif"
        test_file.write_bytes(b"duplicate content")

        # First upload
        success1, msg1, metadata1 = manager.upload_file(str(test_file))
        assert success1

        # Second upload (duplicate)
        success2, msg2, metadata2 = manager.upload_file(str(test_file))

        assert not success2
        assert "duplicate" in msg2.lower()
        assert metadata2 is not None  # Returns existing metadata
        assert metadata2.file_hash == metadata1.file_hash

    def test_upload_file_skip_duplicate_check(self, tmp_path):
        """Test uploading with skip_duplicate_check flag"""
        storage_dir = str(tmp_path / "uploads")
        db_path = str(tmp_path / "dedupe.json")
        manager = UploadManager(
            storage_dir=storage_dir, dedupe_store=DeduplicationStore(db_path)
        )

        test_file = tmp_path / "test.gif"
        test_file.write_bytes(b"content")

        # Upload with skip_duplicate_check
        success1, msg1, metadata1 = manager.upload_file(
            str(test_file), skip_duplicate_check=True
        )

        # Both should succeed when skip_duplicate_check is True
        assert success1

    def test_upload_file_default_filename(self, tmp_path):
        """Test that filename defaults to basename"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "myfile.gif"
        test_file.write_bytes(b"content")

        success, msg, metadata = manager.upload_file(str(test_file))

        assert success
        assert metadata.filename == "myfile.gif"

    def test_upload_file_storage_path_structure(self, tmp_path):
        """Test that files are stored in hash-based directory structure"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "test.gif"
        test_file.write_bytes(b"test content")

        success, msg, metadata = manager.upload_file(str(test_file))

        assert success
        assert metadata.storage_path is not None

        # Verify path structure: storage_dir/XX/YY/hash
        file_hash = metadata.file_hash
        expected_path = os.path.join(
            storage_dir, file_hash[:2], file_hash[2:4], file_hash
        )
        assert metadata.storage_path == expected_path
        assert os.path.exists(metadata.storage_path)

    def test_get_file_path_exists(self, tmp_path):
        """Test getting file path for existing file"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "test.gif"
        test_file.write_bytes(b"content")

        success, msg, metadata = manager.upload_file(str(test_file))
        assert success

        path = manager.get_file_path(metadata.file_hash)

        assert path is not None
        assert os.path.exists(path)
        assert path == metadata.storage_path

    def test_get_file_path_not_exists(self, tmp_path):
        """Test getting file path for non-existent file"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        path = manager.get_file_path("nonexistent_hash")

        assert path is None

    def test_delete_file_success(self, tmp_path):
        """Test deleting existing file"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "delete.gif"
        test_file.write_bytes(b"to be deleted")

        success, msg, metadata = manager.upload_file(str(test_file))
        assert success

        file_hash = metadata.file_hash
        storage_path = metadata.storage_path

        # Delete file
        deleted = manager.delete_file(file_hash)

        assert deleted is True
        assert not os.path.exists(storage_path)
        assert not manager.dedupe_store.is_duplicate(file_hash)

    def test_delete_file_not_exists(self, tmp_path):
        """Test deleting non-existent file"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        deleted = manager.delete_file("nonexistent")

        assert deleted is False

    def test_delete_file_without_disk_removal(self, tmp_path):
        """Test deleting file metadata without removing from disk"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "keep.gif"
        test_file.write_bytes(b"keep on disk")

        success, msg, metadata = manager.upload_file(str(test_file))
        assert success

        file_hash = metadata.file_hash
        storage_path = metadata.storage_path

        # Delete metadata but keep file
        deleted = manager.delete_file(file_hash, remove_from_disk=False)

        assert deleted is True
        assert os.path.exists(storage_path)  # File still exists
        assert not manager.dedupe_store.is_duplicate(file_hash)  # Metadata gone

    def test_get_stats(self, tmp_path):
        """Test getting upload statistics"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        # Upload multiple files
        for i in range(3):
            test_file = tmp_path / f"file{i}.gif"
            test_file.write_bytes(b"X" * (1024 * 1024))  # 1MB each
            manager.upload_file(str(test_file), user_id=f"user{i % 2}")

        stats = manager.get_stats()

        assert stats["total_files"] == 3
        assert stats["total_size_mb"] == 3.0
        assert stats["unique_users"] == 2


class TestConvenienceFunctions:
    """Test standalone convenience functions"""

    def test_hash_file_function(self, tmp_path):
        """Test hash_file convenience function"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        result = hash_file(str(test_file))

        assert len(result) == 64
        assert result.isalnum()

    def test_check_duplicate_function_no_dup(self, tmp_path):
        """Test check_duplicate function with no duplicate"""
        db_path = str(tmp_path / "dedupe.json")
        store = DeduplicationStore(db_path)

        test_file = tmp_path / "unique.txt"
        test_file.write_bytes(b"unique content")

        is_dup, hash_result = check_duplicate(str(test_file), store)

        assert not is_dup
        assert hash_result is None

    def test_check_duplicate_function_is_dup(self, tmp_path):
        """Test check_duplicate function with duplicate"""
        db_path = str(tmp_path / "dedupe.json")
        store = DeduplicationStore(db_path)

        test_file = tmp_path / "dup.txt"
        content = b"duplicate content"
        test_file.write_bytes(content)

        # Add to store
        file_hash = FileHasher.hash_file(str(test_file))
        metadata = FileMetadata(
            file_hash=file_hash,
            filename="dup.txt",
            size_bytes=len(content),
            mime_type="text/plain",
            upload_time="2025-01-01T00:00:00",
        )
        store.add_file(metadata)

        is_dup, hash_result = check_duplicate(str(test_file), store)

        assert is_dup
        assert hash_result == file_hash


class TestDataClasses:
    """Test dataclass structures"""

    def test_file_metadata_creation(self):
        """Test FileMetadata dataclass"""
        metadata = FileMetadata(
            file_hash="abc123",
            filename="test.gif",
            size_bytes=1024,
            mime_type="image/gif",
            upload_time="2025-01-01T00:00:00",
            user_id="user1",
            title="Test GIF",
            tags=["tag1", "tag2"],
            description="A test GIF",
            storage_path="/path/to/file",
        )

        assert metadata.file_hash == "abc123"
        assert metadata.filename == "test.gif"
        assert metadata.size_bytes == 1024
        assert metadata.user_id == "user1"
        assert len(metadata.tags) == 2

    def test_upload_session_creation(self):
        """Test UploadSession dataclass"""
        session = UploadSession(
            session_id="session123",
            file_hash="hash123",
            filename="upload.gif",
            total_size=2048,
        )

        assert session.session_id == "session123"
        assert session.uploaded_bytes == 0
        assert session.status == UploadStatus.PENDING
        assert session.chunks_received == []

    def test_upload_status_enum(self):
        """Test UploadStatus enum values"""
        assert UploadStatus.PENDING == "pending"
        assert UploadStatus.IN_PROGRESS == "in_progress"
        assert UploadStatus.COMPLETED == "completed"
        assert UploadStatus.FAILED == "failed"
        assert UploadStatus.DUPLICATE == "duplicate"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_binary_file_upload(self, tmp_path):
        """Test uploading binary file"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "binary.bin"
        binary_content = bytes(range(256))
        test_file.write_bytes(binary_content)

        success, msg, metadata = manager.upload_file(
            str(test_file), mime_type="application/octet-stream"
        )

        assert success
        assert metadata.size_bytes == 256

    def test_very_long_filename(self, tmp_path):
        """Test handling very long filenames"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "short.gif"
        test_file.write_bytes(b"content")

        long_filename = "a" * 255 + ".gif"

        success, msg, metadata = manager.upload_file(
            str(test_file), filename=long_filename
        )

        assert success
        assert metadata.filename == long_filename

    def test_special_characters_in_metadata(self, tmp_path):
        """Test special characters in metadata fields"""
        storage_dir = str(tmp_path / "uploads")
        manager = UploadManager(storage_dir=storage_dir)

        test_file = tmp_path / "test.gif"
        test_file.write_bytes(b"content")

        success, msg, metadata = manager.upload_file(
            str(test_file),
            title="Test <>&\"'",
            tags=["tag with spaces", "tag-with-dashes", "tag_with_underscores"],
            description="Description with\nnewlines\nand\ttabs",
        )

        assert success
        assert metadata.title == "Test <>&\"'"
        assert len(metadata.tags) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
