"""
Tests for Direct Browser Upload + Resumable Module
"""

import pytest
import os
import tempfile
import shutil
import hashlib
from datetime import datetime, timezone, timedelta

from direct_upload import (
    DirectUploadManager,
    DirectUploadRequest,
    DirectUploadResponse,
    UploadUrlConfig,
    UploadMethod,
    UploadStatus,
    SessionStore,
    ChunkMetadata,
)

from storage_cdn import StorageManager, StorageConfig, StorageBackend


@pytest.fixture
def temp_dir():
    """Create temporary directory for test storage"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def storage_manager(temp_dir):
    """Create test storage manager"""
    config = StorageConfig(
        backend=StorageBackend.LOCAL,
        bucket_name="test-bucket",
        base_path=os.path.join(temp_dir, "storage"),
        cdn_domain="cdn.test.com",
    )
    return StorageManager(config, signing_secret="test-secret-key")


@pytest.fixture
def session_store(temp_dir):
    """Create test session store"""
    db_path = os.path.join(temp_dir, "sessions.json")
    return SessionStore(db_path=db_path)


@pytest.fixture
def upload_manager(storage_manager, session_store):
    """Create test upload manager"""
    return DirectUploadManager(
        storage_manager=storage_manager,
        session_store=session_store,
        default_chunk_size=1024,  # Small chunk size for testing
    )


class TestDirectUpload:
    """Test direct upload functionality"""

    def test_initiate_small_file_upload(self, upload_manager):
        """Test initiating upload for small file (direct upload)"""
        request = DirectUploadRequest(
            filename="test.gif",
            file_size=500,  # Smaller than chunk size
            mime_type="image/gif",
            user_id="user123",
            content_hash="abc123",
        )

        response = upload_manager.initiate_upload(request)

        assert response.upload_method == UploadMethod.DIRECT
        assert response.session_id
        assert response.upload_url
        assert response.max_file_size > 0
        assert "key" in response.fields

    def test_initiate_large_file_upload(self, upload_manager):
        """Test initiating upload for large file (multipart upload)"""
        request = DirectUploadRequest(
            filename="large.mp4",
            file_size=5000,  # Larger than chunk size (1024)
            mime_type="video/mp4",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)

        assert response.upload_method == UploadMethod.MULTIPART
        assert response.session_id
        assert response.chunk_size == 1024
        assert response.total_chunks == 5  # 5000 / 1024 = 5 chunks

    def test_file_size_validation(self, upload_manager):
        """Test file size limit enforcement"""
        request = DirectUploadRequest(
            filename="huge.mp4",
            file_size=200 * 1024 * 1024,  # 200MB
            mime_type="video/mp4",
            user_id="user123",
        )

        config = UploadUrlConfig(max_file_size=100 * 1024 * 1024)  # 100MB limit

        with pytest.raises(ValueError, match="exceeds maximum"):
            upload_manager.initiate_upload(request, config)

    def test_mime_type_validation(self, upload_manager):
        """Test MIME type restrictions"""
        request = DirectUploadRequest(
            filename="doc.pdf",
            file_size=1000,
            mime_type="application/pdf",
            user_id="user123",
        )

        config = UploadUrlConfig(
            allowed_mime_types=["image/gif", "image/png", "video/mp4"]
        )

        with pytest.raises(ValueError, match="not allowed"):
            upload_manager.initiate_upload(request, config)


class TestMultipartUpload:
    """Test multipart/chunked upload functionality"""

    def test_get_chunk_upload_url(self, upload_manager):
        """Test getting signed URL for chunk upload"""
        # Initiate multipart upload
        request = DirectUploadRequest(
            filename="large.mp4",
            file_size=5000,
            mime_type="video/mp4",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)
        session_id = response.session_id

        # Get URL for chunk 0
        chunk_url = upload_manager.get_chunk_upload_url(
            session_id=session_id,
            chunk_number=0,
            chunk_size=1024,
            chunk_hash="chunk0hash",
        )

        assert chunk_url
        assert "chunk_0000" in chunk_url

    def test_mark_chunk_uploaded(self, upload_manager):
        """Test marking chunks as uploaded"""
        # Initiate upload
        request = DirectUploadRequest(
            filename="test.mp4",
            file_size=3000,
            mime_type="video/mp4",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)
        session_id = response.session_id

        # Mark chunk 0 as uploaded
        result = upload_manager.mark_chunk_uploaded(
            session_id=session_id, chunk_number=0, chunk_size=1024, chunk_hash="hash0"
        )

        assert result["uploaded_chunks"] == 1
        assert result["total_chunks"] == 3
        assert result["progress_percent"] > 0
        assert result["status"] == UploadStatus.IN_PROGRESS.value

        # Mark chunk 1
        result = upload_manager.mark_chunk_uploaded(
            session_id=session_id, chunk_number=1, chunk_size=1024, chunk_hash="hash1"
        )

        assert result["uploaded_chunks"] == 2
        assert result["progress_percent"] > 33

        # Mark final chunk
        result = upload_manager.mark_chunk_uploaded(
            session_id=session_id,
            chunk_number=2,
            chunk_size=952,  # Remainder
            chunk_hash="hash2",
        )

        assert result["uploaded_chunks"] == 3
        assert result["total_chunks"] == 3
        assert result["status"] == UploadStatus.COMPLETED.value
        assert result["is_complete"] is True

    def test_finalize_multipart_upload(self, upload_manager, storage_manager):
        """Test finalizing multipart upload by assembling chunks"""
        # Create test data
        test_data = b"A" * 1024 + b"B" * 1024 + b"C" * 500

        # Initiate upload
        request = DirectUploadRequest(
            filename="test.bin",
            file_size=len(test_data),
            mime_type="application/octet-stream",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)
        session_id = response.session_id

        # Upload chunks to storage
        chunks = [test_data[0:1024], test_data[1024:2048], test_data[2048:2548]]

        for i, chunk in enumerate(chunks):
            # Upload chunk to storage
            chunk_key = f"uploads/chunks/{session_id}/chunk_{i:04d}"
            storage_manager.upload(chunk_key, chunk)

            # Mark as uploaded
            chunk_hash = hashlib.sha256(chunk).hexdigest()
            upload_manager.mark_chunk_uploaded(
                session_id=session_id,
                chunk_number=i,
                chunk_size=len(chunk),
                chunk_hash=chunk_hash,
            )

        # Finalize upload
        result = upload_manager.finalize_upload(session_id)

        assert result["status"] == "completed"
        assert result["file_size"] == len(test_data)
        assert result["storage_key"]
        assert result["file_hash"]

        # Verify final file
        final_data, _ = storage_manager.download(result["storage_key"])
        assert final_data == test_data
        assert hashlib.sha256(final_data).hexdigest() == result["file_hash"]

    def test_finalize_incomplete_upload(self, upload_manager):
        """Test finalizing upload with missing chunks fails"""
        request = DirectUploadRequest(
            filename="test.mp4",
            file_size=3000,
            mime_type="video/mp4",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)
        session_id = response.session_id

        # Only upload chunk 0 (missing chunks 1 and 2)
        upload_manager.mark_chunk_uploaded(
            session_id=session_id, chunk_number=0, chunk_size=1024, chunk_hash="hash0"
        )

        # Should fail to finalize
        with pytest.raises(ValueError, match="incomplete"):
            upload_manager.finalize_upload(session_id)


class TestUploadProgress:
    """Test upload progress tracking"""

    def test_get_upload_progress(self, upload_manager):
        """Test getting upload progress"""
        request = DirectUploadRequest(
            filename="test.mp4",
            file_size=4096,
            mime_type="video/mp4",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)
        session_id = response.session_id

        # Initial progress
        progress = upload_manager.get_upload_progress(session_id)
        assert progress["uploaded_chunks"] == 0
        assert progress["total_chunks"] == 4
        assert progress["progress_percent"] == 0
        assert progress["is_complete"] is False

        # Upload 2 chunks
        for i in range(2):
            upload_manager.mark_chunk_uploaded(
                session_id=session_id,
                chunk_number=i,
                chunk_size=1024,
                chunk_hash=f"hash{i}",
            )

        progress = upload_manager.get_upload_progress(session_id)
        assert progress["uploaded_chunks"] == 2
        assert progress["progress_percent"] == 50.0
        assert len(progress["missing_chunks"]) == 2
        assert 2 in progress["missing_chunks"]
        assert 3 in progress["missing_chunks"]

    def test_resume_upload(self, upload_manager):
        """Test resuming interrupted upload"""
        request = DirectUploadRequest(
            filename="test.mp4",
            file_size=5000,
            mime_type="video/mp4",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)
        session_id = response.session_id

        # Upload some chunks
        upload_manager.mark_chunk_uploaded(
            session_id=session_id, chunk_number=0, chunk_size=1024, chunk_hash="hash0"
        )

        upload_manager.mark_chunk_uploaded(
            session_id=session_id, chunk_number=2, chunk_size=1024, chunk_hash="hash2"
        )

        # Resume upload
        resume_info = upload_manager.resume_upload(session_id)

        assert resume_info["can_resume"] is True
        assert resume_info["uploaded_chunks"] == 2
        assert resume_info["total_chunks"] == 5
        assert resume_info["next_chunk"] == 1  # Missing chunk 1
        assert resume_info["chunk_size"] == 1024


class TestUploadAbort:
    """Test aborting uploads"""

    def test_abort_upload(self, upload_manager, storage_manager):
        """Test aborting an upload"""
        # Create upload session
        request = DirectUploadRequest(
            filename="test.mp4",
            file_size=3000,
            mime_type="video/mp4",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)
        session_id = response.session_id

        # Upload a chunk
        chunk_key = f"uploads/chunks/{session_id}/chunk_0000"
        storage_manager.upload(chunk_key, b"test" * 256)

        upload_manager.mark_chunk_uploaded(
            session_id=session_id, chunk_number=0, chunk_size=1024, chunk_hash="hash0"
        )

        # Abort with cleanup
        result = upload_manager.abort_upload(session_id, cleanup=True)
        assert result is True

        # Check session status
        progress = upload_manager.get_upload_progress(session_id)
        assert progress["status"] == UploadStatus.ABORTED.value

        # Verify chunk was deleted
        assert not storage_manager.exists(chunk_key)


class TestSessionStore:
    """Test session persistence"""

    def test_create_and_get_session(self, session_store):
        """Test creating and retrieving session"""
        from direct_upload import UploadSession

        session = UploadSession(
            session_id="test123",
            user_id="user456",
            filename="test.mp4",
            total_size=1000,
            mime_type="video/mp4",
            chunk_size=100,
            total_chunks=10,
        )

        session_store.create_session(session)

        retrieved = session_store.get_session("test123")
        assert retrieved is not None
        assert retrieved.session_id == "test123"
        assert retrieved.user_id == "user456"
        assert retrieved.total_chunks == 10

    def test_update_session(self, session_store):
        """Test updating session"""
        from direct_upload import UploadSession

        session = UploadSession(
            session_id="test123",
            user_id="user456",
            filename="test.mp4",
            total_size=1000,
            mime_type="video/mp4",
            chunk_size=100,
            total_chunks=10,
        )

        session_store.create_session(session)

        # Update session
        session.status = UploadStatus.COMPLETED
        session_store.update_session(session)

        retrieved = session_store.get_session("test123")
        assert retrieved.status == UploadStatus.COMPLETED

    def test_delete_session(self, session_store):
        """Test deleting session"""
        from direct_upload import UploadSession

        session = UploadSession(
            session_id="test123",
            user_id="user456",
            filename="test.mp4",
            total_size=1000,
            mime_type="video/mp4",
            chunk_size=100,
            total_chunks=10,
        )

        session_store.create_session(session)
        assert session_store.get_session("test123") is not None

        session_store.delete_session("test123")
        assert session_store.get_session("test123") is None

    def test_cleanup_expired_sessions(self, session_store):
        """Test cleaning up expired sessions"""
        from direct_upload import UploadSession

        # Create expired session
        expired_session = UploadSession(
            session_id="expired123",
            user_id="user456",
            filename="test.mp4",
            total_size=1000,
            mime_type="video/mp4",
            chunk_size=100,
            total_chunks=10,
            expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )

        # Create valid session
        valid_session = UploadSession(
            session_id="valid123",
            user_id="user456",
            filename="test2.mp4",
            total_size=1000,
            mime_type="video/mp4",
            chunk_size=100,
            total_chunks=10,
        )

        session_store.create_session(expired_session)
        session_store.create_session(valid_session)

        # Cleanup
        cleaned = session_store.cleanup_expired_sessions()

        assert cleaned == 1
        assert session_store.get_session("expired123") is None
        assert session_store.get_session("valid123") is not None


class TestUploadStats:
    """Test upload statistics"""

    def test_get_stats(self, upload_manager):
        """Test getting upload statistics"""
        # Create multiple uploads
        for i in range(3):
            request = DirectUploadRequest(
                filename=f"test{i}.mp4",
                file_size=2000,
                mime_type="video/mp4",
                user_id="user123",
            )
            upload_manager.initiate_upload(request)

        stats = upload_manager.get_stats()

        assert stats["total_sessions"] == 3
        assert UploadStatus.PENDING.value in stats["by_status"]
        assert stats["by_status"][UploadStatus.PENDING.value] == 3


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_invalid_session_id(self, upload_manager):
        """Test operations with invalid session ID"""
        with pytest.raises(ValueError, match="Session not found"):
            upload_manager.get_chunk_upload_url("invalid_session", 0, 1024)

        with pytest.raises(ValueError, match="Session not found"):
            upload_manager.get_upload_progress("invalid_session")

    def test_invalid_chunk_number(self, upload_manager):
        """Test uploading invalid chunk number"""
        request = DirectUploadRequest(
            filename="test.mp4",
            file_size=3000,
            mime_type="video/mp4",
            user_id="user123",
        )

        response = upload_manager.initiate_upload(request)
        session_id = response.session_id

        # Try to upload chunk beyond total
        with pytest.raises(ValueError, match="Invalid chunk number"):
            upload_manager.get_chunk_upload_url(session_id, 99, 1024)

    def test_resume_expired_session(self, upload_manager):
        """Test resuming expired session"""
        from direct_upload import UploadSession

        # Create expired session manually
        expired_session = UploadSession(
            session_id="expired123",
            user_id="user123",
            filename="test.mp4",
            total_size=3000,
            mime_type="video/mp4",
            chunk_size=1024,
            total_chunks=3,
            expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )

        upload_manager.sessions.create_session(expired_session)

        with pytest.raises(ValueError, match="expired"):
            upload_manager.resume_upload("expired123")

    def test_resume_completed_upload(self, upload_manager):
        """Test resuming already completed upload"""
        from direct_upload import UploadSession

        completed_session = UploadSession(
            session_id="completed123",
            user_id="user123",
            filename="test.mp4",
            total_size=3000,
            mime_type="video/mp4",
            chunk_size=1024,
            total_chunks=3,
            status=UploadStatus.COMPLETED,
        )

        upload_manager.sessions.create_session(completed_session)

        with pytest.raises(ValueError, match="already completed"):
            upload_manager.resume_upload("completed123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
