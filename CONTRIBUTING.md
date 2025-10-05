# Contributing to GIFDistributor

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment

## Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/GIFDistributor.git
   cd GIFDistributor
   ```
3. **Install dependencies**:
   ```bash
   npm install
   pip install -r requirements.txt
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Running Locally

```bash
# Start development servers
npm run dev

# Run tests
pytest .           # Python tests
npm test          # JavaScript tests

# Run linters
npm run lint      # JavaScript/TypeScript
black .           # Python formatting
```

### Code Style

**Python:**
- Follow PEP 8 style guide
- Use Black for formatting: `black .`
- Type hints for function signatures
- Docstrings for public functions and classes

**TypeScript/JavaScript:**
- Follow ESLint configuration
- Use Prettier-compatible formatting
- TypeScript for new code when possible
- Clear naming conventions

### Testing

- **All new features require tests**
- Python: Use `pytest` with fixtures
- JavaScript: Use Jest
- Maintain >80% code coverage
- Test edge cases and error handling

Example Python test:
```python
import pytest
from your_module import YourClass

def test_your_feature():
    instance = YourClass()
    result = instance.your_method()
    assert result == expected_value
```

Example JavaScript test:
```typescript
import { yourFunction } from './yourModule';

describe('yourFunction', () => {
  it('should return expected value', () => {
    const result = yourFunction(input);
    expect(result).toBe(expectedValue);
  });
});
```

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(analytics): add platform-specific metrics tracking

Implement tracking of engagement metrics broken down by platform
(Slack, Discord, Teams, etc.) to help users understand which
channels perform best.

Closes #42
```

```
fix(cdn): handle empty Range header correctly

The CDN helper was throwing an error when Range header was
an empty string. Now it gracefully falls back to full content.
```

### Commit Best Practices

- Keep commits atomic (one logical change per commit)
- Write clear, descriptive commit messages
- Reference issue numbers in commit messages
- Sign off commits if required by project policy

## Pull Request Process

1. **Update documentation** for any new features
2. **Add or update tests** for your changes
3. **Run all tests** and ensure they pass
4. **Update CHANGELOG.md** if applicable
5. **Create pull request** with clear description

### PR Description Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] No new warnings
```

## Module Guidelines

### Python Modules

Each module should:
- Have a clear, single responsibility
- Include comprehensive docstrings
- Provide type hints
- Handle errors gracefully
- Include unit tests in `test_*.py`

Example module structure:
```python
"""
Module Name - Brief Description

Detailed description of what this module does.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class YourDataClass:
    """Description of the data class"""
    field1: str
    field2: int


class YourClass:
    """
    Main class description

    Args:
        param1: Description of param1
        param2: Description of param2
    """

    def __init__(self, param1: str, param2: int):
        self.param1 = param1
        self.param2 = param2

    def your_method(self) -> Dict[str, Any]:
        """
        Method description

        Returns:
            Dictionary containing result data

        Raises:
            ValueError: When invalid input provided
        """
        # Implementation
        pass
```

### TypeScript/JavaScript Modules

Each module should:
- Export clear interfaces/types
- Use async/await for async operations
- Handle errors with try/catch
- Provide JSDoc comments

Example:
```typescript
/**
 * Your module description
 */

export interface YourInterface {
  field1: string;
  field2: number;
}

export class YourClass {
  /**
   * Constructor description
   * @param param1 - Description
   */
  constructor(private param1: string) {}

  /**
   * Method description
   * @returns Promise with result
   */
  async yourMethod(): Promise<YourInterface> {
    try {
      // Implementation
      return { field1: 'value', field2: 42 };
    } catch (error) {
      console.error('Error:', error);
      throw error;
    }
  }
}
```

## Adding New Integrations

When adding a new platform integration (e.g., Twitter, LinkedIn):

1. Create a new module: `platform_name.py`
2. Implement OAuth2 flow if needed
3. Add posting/sharing functionality
4. Create tests: `test_platform_name.py`
5. Add documentation: `docs/platform-name-setup.md`
6. Update README.md with new integration

## Documentation

- Update README.md for significant changes
- Add new docs to `docs/` directory
- Keep QUICKSTART.md current
- Update type definitions
- Add inline comments for complex logic

## Release Process

(For maintainers)

1. Update version in `package.json`
2. Update CHANGELOG.md
3. Create release tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. Create GitHub release with notes

## Questions?

- Open an issue for bugs or feature requests
- Check existing documentation in `docs/`
- Review closed PRs for examples

## Recognition

Contributors will be acknowledged in:
- CONTRIBUTORS.md (we'll create this)
- Release notes
- Documentation where applicable

Thank you for contributing to GIFDistributor! 🎉
