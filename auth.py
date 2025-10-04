"""
Authentication and Authorization Module

Provides OAuth2 and email-based authentication with session management.
Supports multiple OAuth providers (Google, GitHub, Microsoft) and email/password auth.

Issue: #3
Slug: auth
Priority: P0
"""

import os
import secrets
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class AuthProvider(Enum):
    """Supported authentication providers"""
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


class UserRole(Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"


@dataclass
class User:
    """User model"""
    id: str
    email: str
    provider: AuthProvider
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    email_verified: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Session:
    """Session model"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails"""
    pass


class AuthManager:
    """
    Main authentication manager

    Handles user authentication via OAuth2 and email/password,
    session management, and token generation.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        session_lifetime_hours: int = 24,
        oauth_config: Optional[Dict[str, Dict[str, str]]] = None
    ):
        """
        Initialize auth manager

        Args:
            secret_key: Secret key for signing tokens (auto-generated if not provided)
            session_lifetime_hours: Session lifetime in hours (default 24)
            oauth_config: OAuth provider configurations with client_id and client_secret
        """
        self.secret_key = secret_key or secrets.token_hex(32)
        self.session_lifetime = timedelta(hours=session_lifetime_hours)
        self.oauth_config = oauth_config or {}

        # In-memory storage (replace with database in production)
        self._users: Dict[str, User] = {}
        self._sessions: Dict[str, Session] = {}
        self._email_passwords: Dict[str, str] = {}  # email -> hashed_password

    def _hash_password(self, password: str, salt: Optional[str] = None) -> str:
        """Hash password with PBKDF2"""
        if salt is None:
            salt = secrets.token_hex(16)

        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return f"{salt}${pwd_hash.hex()}"

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = hashed.split('$')
            return self._hash_password(password, salt) == hashed
        except (ValueError, AttributeError):
            return False

    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        return secrets.token_urlsafe(32)

    def register_email_user(
        self,
        email: str,
        password: str,
        role: UserRole = UserRole.USER
    ) -> User:
        """
        Register a new user with email/password

        Args:
            email: User email address
            password: User password (will be hashed)
            role: User role (default USER)

        Returns:
            Created User object

        Raises:
            AuthenticationError: If email already exists
        """
        if email in self._email_passwords:
            raise AuthenticationError(f"Email {email} already registered")

        user_id = secrets.token_urlsafe(16)
        user = User(
            id=user_id,
            email=email,
            provider=AuthProvider.EMAIL,
            role=role,
            created_at=datetime.utcnow(),
            email_verified=False
        )

        self._users[user_id] = user
        self._email_passwords[email] = self._hash_password(password)

        return user

    def authenticate_email(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> tuple[User, Session]:
        """
        Authenticate user with email/password

        Args:
            email: User email
            password: User password
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)

        Returns:
            Tuple of (User, Session)

        Raises:
            AuthenticationError: If credentials are invalid
        """
        if email not in self._email_passwords:
            raise AuthenticationError("Invalid email or password")

        if not self._verify_password(password, self._email_passwords[email]):
            raise AuthenticationError("Invalid email or password")

        # Find user by email
        user = next(
            (u for u in self._users.values() if u.email == email),
            None
        )

        if not user:
            raise AuthenticationError("User not found")

        # Update last login
        user.last_login = datetime.utcnow()

        # Create session
        session = self._create_session(user.id, ip_address, user_agent)

        return user, session

    def authenticate_oauth(
        self,
        provider: AuthProvider,
        oauth_token: str,
        user_info: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> tuple[User, Session]:
        """
        Authenticate user with OAuth provider

        Args:
            provider: OAuth provider (GOOGLE, GITHUB, MICROSOFT)
            oauth_token: OAuth access token from provider
            user_info: User information from OAuth provider (must include email)
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)

        Returns:
            Tuple of (User, Session)

        Raises:
            AuthenticationError: If OAuth authentication fails
        """
        if provider == AuthProvider.EMAIL:
            raise AuthenticationError("Use authenticate_email for email auth")

        email = user_info.get('email')
        if not email:
            raise AuthenticationError("Email not provided by OAuth provider")

        # Find existing user or create new one
        user = next(
            (u for u in self._users.values()
             if u.email == email and u.provider == provider),
            None
        )

        if not user:
            user_id = secrets.token_urlsafe(16)
            user = User(
                id=user_id,
                email=email,
                provider=provider,
                role=UserRole.USER,
                created_at=datetime.utcnow(),
                email_verified=True,  # OAuth emails are pre-verified
                metadata=user_info
            )
            self._users[user_id] = user

        # Update last login
        user.last_login = datetime.utcnow()

        # Create session
        session = self._create_session(user.id, ip_address, user_agent)

        return user, session

    def _create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """Create a new session for user"""
        session_id = self._generate_session_id()
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + self.session_lifetime,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self._sessions[session_id] = session
        return session

    def validate_session(self, session_id: str) -> Optional[User]:
        """
        Validate session and return associated user

        Args:
            session_id: Session ID to validate

        Returns:
            User object if session is valid, None otherwise
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check if session expired
        if datetime.utcnow() > session.expires_at:
            del self._sessions[session_id]
            return None

        return self._users.get(session.user_id)

    def logout(self, session_id: str) -> bool:
        """
        Logout user by invalidating session

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if session was found and invalidated, False otherwise
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_oauth_authorization_url(
        self,
        provider: AuthProvider,
        redirect_uri: str,
        state: Optional[str] = None
    ) -> str:
        """
        Get OAuth authorization URL for provider

        Args:
            provider: OAuth provider
            redirect_uri: Redirect URI after authorization
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL

        Raises:
            ValueError: If provider is not configured or is EMAIL
        """
        if provider == AuthProvider.EMAIL:
            raise ValueError("EMAIL provider does not support OAuth flow")

        if provider.value not in self.oauth_config:
            raise ValueError(f"Provider {provider.value} not configured")

        config = self.oauth_config[provider.value]
        client_id = config.get('client_id')

        if not client_id:
            raise ValueError(f"No client_id configured for {provider.value}")

        # OAuth authorization endpoints
        auth_urls = {
            AuthProvider.GOOGLE: "https://accounts.google.com/o/oauth2/v2/auth",
            AuthProvider.GITHUB: "https://github.com/login/oauth/authorize",
            AuthProvider.MICROSOFT: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        }

        base_url = auth_urls.get(provider)
        if not base_url:
            raise ValueError(f"Unknown provider {provider.value}")

        # Build authorization URL
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'email profile'
        }

        if state:
            params['state'] = state

        query_string = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"


class RBACManager:
    """
    Role-Based Access Control Manager

    Manages permissions and authorization for users.
    """

    def __init__(self):
        # Define role permissions
        self.permissions = {
            UserRole.ADMIN: {
                'upload', 'delete', 'moderate', 'manage_users', 'view_analytics'
            },
            UserRole.MODERATOR: {
                'upload', 'delete', 'moderate', 'view_analytics'
            },
            UserRole.USER: {
                'upload', 'delete_own'
            }
        }

    def can_perform(self, user: User, action: str) -> bool:
        """
        Check if user can perform action

        Args:
            user: User object
            action: Action to check (e.g., 'upload', 'moderate')

        Returns:
            True if user has permission, False otherwise
        """
        user_permissions = self.permissions.get(user.role, set())
        return action in user_permissions

    def require_permission(self, user: User, action: str) -> None:
        """
        Require user to have permission, raise exception if not

        Args:
            user: User object
            action: Required action

        Raises:
            AuthorizationError: If user lacks permission
        """
        if not self.can_perform(user, action):
            raise AuthorizationError(
                f"User {user.email} lacks permission for action: {action}"
            )

    def add_permission(self, role: UserRole, action: str) -> None:
        """Add permission to role"""
        if role not in self.permissions:
            self.permissions[role] = set()
        self.permissions[role].add(action)

    def remove_permission(self, role: UserRole, action: str) -> None:
        """Remove permission from role"""
        if role in self.permissions:
            self.permissions[role].discard(action)


# Example usage
if __name__ == "__main__":
    # Initialize auth manager
    auth = AuthManager(
        oauth_config={
            'google': {
                'client_id': 'your-google-client-id',
                'client_secret': 'your-google-client-secret'
            },
            'github': {
                'client_id': 'your-github-client-id',
                'client_secret': 'your-github-client-secret'
            }
        }
    )

    # Register email user
    user = auth.register_email_user(
        email="user@example.com",
        password="secure_password_123"
    )
    print(f"Registered user: {user.email}")

    # Authenticate
    user, session = auth.authenticate_email(
        email="user@example.com",
        password="secure_password_123",
        ip_address="192.168.1.1"
    )
    print(f"Authenticated user: {user.email}, session: {session.session_id}")

    # Validate session
    validated_user = auth.validate_session(session.session_id)
    print(f"Session valid: {validated_user is not None}")

    # RBAC
    rbac = RBACManager()
    print(f"Can upload: {rbac.can_perform(user, 'upload')}")
    print(f"Can moderate: {rbac.can_perform(user, 'moderate')}")

    # Get OAuth URL
    oauth_url = auth.get_oauth_authorization_url(
        provider=AuthProvider.GOOGLE,
        redirect_uri="https://yourapp.com/auth/callback",
        state="random_state_token"
    )
    print(f"OAuth URL: {oauth_url}")
