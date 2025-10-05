"""
Unit tests for authentication module

Tests OAuth and email authentication flows, session management, and RBAC.

Issue: #3
"""

import unittest
from datetime import datetime, timedelta, timezone
from auth import (
    AuthManager,
    RBACManager,
    AuthProvider,
    UserRole,
    AuthenticationError,
    AuthorizationError,
    User,
)


class TestAuthManager(unittest.TestCase):
    """Test cases for AuthManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.auth = AuthManager(
            secret_key="test_secret_key",
            oauth_config={
                "google": {
                    "client_id": "test-google-client-id",
                    "client_secret": "test-google-secret",
                }
            },
        )

    def test_register_email_user(self):
        """Test email user registration"""
        user = self.auth.register_email_user(
            email="test@example.com", password="password123"
        )

        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.provider, AuthProvider.EMAIL)
        self.assertEqual(user.role, UserRole.USER)
        self.assertFalse(user.email_verified)

    def test_register_duplicate_email(self):
        """Test that duplicate email registration raises error"""
        self.auth.register_email_user(email="test@example.com", password="password123")

        with self.assertRaises(AuthenticationError):
            self.auth.register_email_user(
                email="test@example.com", password="different_password"
            )

    def test_authenticate_email_success(self):
        """Test successful email authentication"""
        self.auth.register_email_user(email="test@example.com", password="password123")

        user, session = self.auth.authenticate_email(
            email="test@example.com", password="password123", ip_address="192.168.1.1"
        )

        self.assertEqual(user.email, "test@example.com")
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, user.id)
        self.assertEqual(session.ip_address, "192.168.1.1")

    def test_authenticate_email_wrong_password(self):
        """Test authentication with wrong password"""
        self.auth.register_email_user(email="test@example.com", password="password123")

        with self.assertRaises(AuthenticationError):
            self.auth.authenticate_email(
                email="test@example.com", password="wrong_password"
            )

    def test_authenticate_email_nonexistent(self):
        """Test authentication with non-existent email"""
        with self.assertRaises(AuthenticationError):
            self.auth.authenticate_email(
                email="nonexistent@example.com", password="password123"
            )

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = self.auth._hash_password(password)

        # Verify correct password
        self.assertTrue(self.auth._verify_password(password, hashed))

        # Verify wrong password
        self.assertFalse(self.auth._verify_password("wrong_password", hashed))

    def test_session_creation(self):
        """Test session creation and validation"""
        user = self.auth.register_email_user(
            email="test@example.com", password="password123"
        )

        session = self.auth._create_session(
            user_id=user.id, ip_address="192.168.1.1", user_agent="Mozilla/5.0"
        )

        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, user.id)
        self.assertEqual(session.ip_address, "192.168.1.1")
        self.assertEqual(session.user_agent, "Mozilla/5.0")

    def test_validate_session(self):
        """Test session validation"""
        user = self.auth.register_email_user(
            email="test@example.com", password="password123"
        )

        session = self.auth._create_session(user.id)

        # Validate valid session
        validated_user = self.auth.validate_session(session.session_id)
        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user.id, user.id)

        # Validate invalid session
        invalid_user = self.auth.validate_session("invalid_session_id")
        self.assertIsNone(invalid_user)

    def test_session_expiration(self):
        """Test that expired sessions are invalidated"""
        # Create auth manager with very short session lifetime
        auth = AuthManager(session_lifetime_hours=0)
        user = auth.register_email_user(
            email="test@example.com", password="password123"
        )

        session = auth._create_session(user.id)

        # Manually expire the session
        auth._sessions[session.session_id].expires_at = datetime.now(
            timezone.utc
        ) - timedelta(hours=1)

        # Validate should return None for expired session
        validated_user = auth.validate_session(session.session_id)
        self.assertIsNone(validated_user)

        # Session should be deleted
        self.assertNotIn(session.session_id, auth._sessions)

    def test_logout(self):
        """Test logout functionality"""
        user, session = self.auth.authenticate_email(
            *self.auth.register_email_user(
                email="test@example.com", password="password123"
            )
            and ("test@example.com", "password123")
        )

        # Session should be valid
        self.assertIsNotNone(self.auth.validate_session(session.session_id))

        # Logout
        result = self.auth.logout(session.session_id)
        self.assertTrue(result)

        # Session should be invalid after logout
        self.assertIsNone(self.auth.validate_session(session.session_id))

        # Logout non-existent session
        result = self.auth.logout("non_existent_session")
        self.assertFalse(result)

    def test_oauth_authentication(self):
        """Test OAuth authentication flow"""
        user_info = {
            "email": "oauth@example.com",
            "name": "OAuth User",
            "picture": "https://example.com/photo.jpg",
        }

        user, session = self.auth.authenticate_oauth(
            provider=AuthProvider.GOOGLE,
            oauth_token="fake_oauth_token",
            user_info=user_info,
            ip_address="192.168.1.1",
        )

        self.assertEqual(user.email, "oauth@example.com")
        self.assertEqual(user.provider, AuthProvider.GOOGLE)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.metadata, user_info)
        self.assertIsNotNone(session.session_id)

    def test_oauth_authentication_existing_user(self):
        """Test OAuth authentication with existing user"""
        user_info = {"email": "oauth@example.com", "name": "OAuth User"}

        # First authentication creates user
        user1, session1 = self.auth.authenticate_oauth(
            provider=AuthProvider.GOOGLE, oauth_token="token1", user_info=user_info
        )

        # Second authentication should use existing user
        user2, session2 = self.auth.authenticate_oauth(
            provider=AuthProvider.GOOGLE, oauth_token="token2", user_info=user_info
        )

        # Should be same user, different sessions
        self.assertEqual(user1.id, user2.id)
        self.assertNotEqual(session1.session_id, session2.session_id)

    def test_oauth_authentication_no_email(self):
        """Test OAuth authentication without email raises error"""
        user_info = {"name": "No Email User"}

        with self.assertRaises(AuthenticationError):
            self.auth.authenticate_oauth(
                provider=AuthProvider.GOOGLE, oauth_token="token", user_info=user_info
            )

    def test_get_oauth_authorization_url(self):
        """Test OAuth authorization URL generation"""
        url = self.auth.get_oauth_authorization_url(
            provider=AuthProvider.GOOGLE,
            redirect_uri="https://app.com/callback",
            state="random_state",
        )

        self.assertIn("accounts.google.com", url)
        self.assertIn("client_id=test-google-client-id", url)
        self.assertIn("redirect_uri=https://app.com/callback", url)
        self.assertIn("state=random_state", url)

    def test_get_oauth_url_unconfigured_provider(self):
        """Test OAuth URL for unconfigured provider raises error"""
        with self.assertRaises(ValueError):
            self.auth.get_oauth_authorization_url(
                provider=AuthProvider.GITHUB,  # Not configured in setUp
                redirect_uri="https://app.com/callback",
            )

    def test_get_oauth_url_email_provider(self):
        """Test OAuth URL for EMAIL provider raises error"""
        with self.assertRaises(ValueError):
            self.auth.get_oauth_authorization_url(
                provider=AuthProvider.EMAIL, redirect_uri="https://app.com/callback"
            )


class TestRBACManager(unittest.TestCase):
    """Test cases for RBAC Manager"""

    def setUp(self):
        """Set up test fixtures"""
        self.rbac = RBACManager()

    def test_admin_permissions(self):
        """Test admin role has all permissions"""
        admin = User(
            id="admin1",
            email="admin@example.com",
            provider=AuthProvider.EMAIL,
            role=UserRole.ADMIN,
            created_at=datetime.now(timezone.utc),
        )

        self.assertTrue(self.rbac.can_perform(admin, "upload"))
        self.assertTrue(self.rbac.can_perform(admin, "delete"))
        self.assertTrue(self.rbac.can_perform(admin, "moderate"))
        self.assertTrue(self.rbac.can_perform(admin, "manage_users"))
        self.assertTrue(self.rbac.can_perform(admin, "view_analytics"))

    def test_moderator_permissions(self):
        """Test moderator role permissions"""
        moderator = User(
            id="mod1",
            email="mod@example.com",
            provider=AuthProvider.EMAIL,
            role=UserRole.MODERATOR,
            created_at=datetime.now(timezone.utc),
        )

        self.assertTrue(self.rbac.can_perform(moderator, "upload"))
        self.assertTrue(self.rbac.can_perform(moderator, "delete"))
        self.assertTrue(self.rbac.can_perform(moderator, "moderate"))
        self.assertTrue(self.rbac.can_perform(moderator, "view_analytics"))
        self.assertFalse(self.rbac.can_perform(moderator, "manage_users"))

    def test_user_permissions(self):
        """Test regular user permissions"""
        user = User(
            id="user1",
            email="user@example.com",
            provider=AuthProvider.EMAIL,
            role=UserRole.USER,
            created_at=datetime.now(timezone.utc),
        )

        self.assertTrue(self.rbac.can_perform(user, "upload"))
        self.assertTrue(self.rbac.can_perform(user, "delete_own"))
        self.assertFalse(self.rbac.can_perform(user, "delete"))
        self.assertFalse(self.rbac.can_perform(user, "moderate"))
        self.assertFalse(self.rbac.can_perform(user, "manage_users"))

    def test_require_permission_success(self):
        """Test require_permission with valid permission"""
        admin = User(
            id="admin1",
            email="admin@example.com",
            provider=AuthProvider.EMAIL,
            role=UserRole.ADMIN,
            created_at=datetime.now(timezone.utc),
        )

        # Should not raise
        self.rbac.require_permission(admin, "moderate")

    def test_require_permission_failure(self):
        """Test require_permission with invalid permission"""
        user = User(
            id="user1",
            email="user@example.com",
            provider=AuthProvider.EMAIL,
            role=UserRole.USER,
            created_at=datetime.now(timezone.utc),
        )

        with self.assertRaises(AuthorizationError):
            self.rbac.require_permission(user, "moderate")

    def test_add_permission(self):
        """Test adding permission to role"""
        user = User(
            id="user1",
            email="user@example.com",
            provider=AuthProvider.EMAIL,
            role=UserRole.USER,
            created_at=datetime.now(timezone.utc),
        )

        # User doesn't have 'moderate' permission initially
        self.assertFalse(self.rbac.can_perform(user, "moderate"))

        # Add permission
        self.rbac.add_permission(UserRole.USER, "moderate")

        # Now user should have it
        self.assertTrue(self.rbac.can_perform(user, "moderate"))

    def test_remove_permission(self):
        """Test removing permission from role"""
        admin = User(
            id="admin1",
            email="admin@example.com",
            provider=AuthProvider.EMAIL,
            role=UserRole.ADMIN,
            created_at=datetime.now(timezone.utc),
        )

        # Admin has 'delete' permission initially
        self.assertTrue(self.rbac.can_perform(admin, "delete"))

        # Remove permission
        self.rbac.remove_permission(UserRole.ADMIN, "delete")

        # Now admin shouldn't have it
        self.assertFalse(self.rbac.can_perform(admin, "delete"))


if __name__ == "__main__":
    unittest.main()
