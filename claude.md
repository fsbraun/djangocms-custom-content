# Django CMS Project Setup Guide

This document describes the standard project setup for django CMS plugins and packages, based on the patterns established in djangocms-frontend and other django CMS ecosystem projects.

## Project Structure

```
project-root/
├── .github/
│   ├── dependabot.yml           # Automated dependency updates
│   └── workflows/
│       ├── codecov.yml          # Test coverage CI
│       ├── docs.yml             # Documentation build
│       └── lint-pr.yml          # PR title validation
├── docs/
│   ├── source/
│   │   ├── conf.py              # Sphinx configuration
│   │   └── index.rst            # Documentation index
│   ├── Makefile                 # Documentation build commands
│   └── requirements.txt         # Documentation dependencies
├── tests/
│   ├── requirements/
│   │   ├── base.txt             # Base test dependencies
│   │   ├── dj42_cms311.txt      # Django 4.2 + CMS 3.11
│   │   ├── dj42_cms41.txt       # Django 4.2 + CMS 4.1
│   │   ├── dj50_cms41.txt       # Django 5.0 + CMS 4.1
│   │   ├── dj51_cms41.txt       # Django 5.1 + CMS 4.1
│   │   ├── dj52_cms50.txt       # Django 5.2 + CMS 5.0
│   │   └── dj60_cms50.txt       # Django 6.0 + CMS 5.0
│   ├── test_app/                # Test Django application
│   │   ├── templates/           # Test templates
│   │   └── models.py
│   ├── fixtures.py              # Test fixtures and helpers
│   ├── test_settings.py         # Django test settings
│   └── urls.py                  # Test URL configuration
├── package_name/                # Main package
│   ├── locale/                  # Translations
│   ├── migrations/              # Database migrations
│   ├── static/                  # Static files
│   ├── templates/               # Django templates
│   ├── __init__.py              # Version definition
│   ├── apps.py                  # Django app configuration
│   ├── models.py                # Database models
│   ├── cms_plugins.py           # CMS plugin registration
│   └── admin.py                 # Django admin configuration
├── .editorconfig                # Editor configuration
├── .gitignore                   # Git ignore patterns
├── .pre-commit-config.yaml      # Pre-commit hooks
├── .readthedocs.yaml            # ReadTheDocs configuration
├── conftest.py                  # Pytest configuration
├── LICENSE                      # BSD-3-Clause license
├── MANIFEST.in                  # Package manifest
├── pyproject.toml               # Project configuration
├── README.rst                   # Project documentation
└── setup.py                     # Minimal setuptools wrapper
```

## Configuration Files

### pyproject.toml

The central configuration file using modern Python packaging standards:

**Key Sections:**

1. **Build System**
   ```toml
   [build-system]
   build-backend = "setuptools.build_meta"
   requires = ["setuptools", "setuptools-scm"]
   ```

2. **Project Metadata**
   - Name, description, readme, license, authors
   - Python version requirement: `>=3.10`
   - Django versions: 4.2, 5.0, 5.1, 5.2, 6.0
   - CMS versions: 3.11, 4.1, 5.0
   - Classifiers for PyPI
   - Dynamic version from package `__version__`

3. **Dependencies**
   - Core: `django-cms>=3.11`
   - Optional extras for CMS v3 and v4

4. **Tool Configurations**
   - **ruff**: Line length 119, linting rules (E, F, I, W)
   - **black**: Code formatting with exclusions
   - **isort**: Import sorting with Django/CMS sections
   - **coverage**: Branch coverage, source/omit patterns
   - **pytest**: Django settings module, test paths

### .pre-commit-config.yaml

Automated code quality checks before commits:

1. **pyupgrade** (v3.21.2): Upgrades Python syntax to 3.10+
2. **django-upgrade** (1.29.1): Upgrades Django syntax to 4.2+
3. **ruff**: Linting with auto-fix and formatting
4. **pyproject-fmt**: Formats pyproject.toml

### .editorconfig

Consistent coding style across editors:

- Default: 4-space indentation, LF line endings, UTF-8
- Python: 120 character line length, single quotes
- HTML/YAML: Custom indentation
- RST: 80 character line length

## Testing Infrastructure

### Test Settings (tests/test_settings.py)

Minimal Django settings for testing:

- **INSTALLED_APPS**: Essential Django apps, CMS, your package
- **MIDDLEWARE**: Django and CMS middleware stack
- **DATABASES**: SQLite3 for testing
- **CMS_TEMPLATES**: At least one template defined
- **CMS_CONFIRM_VERSION4**: True for v4 compatibility
- **Optional imports**: Handle djangocms-versioning for v4 tests

### Test Fixtures (tests/fixtures.py)

**TestFixture Base Class** provides:

- `setUp()`: Creates superuser, site, pages with placeholders
- `tearDown()`: Cleans up pages, versions, users
- **CMS v3/v4 compatibility methods**:
  - `publish(grouper, language)`: Publish content
  - `unpublish(grouper, language)`: Unpublish content
  - `create_page(title, **kwargs)`: Create test pages
  - `get_placeholders(page)`: Get page placeholders

### Test Requirements Structure

**base.txt**: Common dependencies for all test configurations
- pytest, pytest-django, coverage
- Code quality tools: black, ruff, isort, flake8
- Package installed in editable mode: `-e .`

**Version-specific files**: Matrix testing across Django/CMS versions
- Format: `dj<django_version>_cms<cms_version>.txt`
- Includes: `-r base.txt` + specific version pins
- Example: `dj50_cms41.txt` for Django 5.0 + CMS 4.1

### Test App (tests/test_app/)

Minimal Django app for testing:

- **templates/page.html**: Basic CMS page template with placeholders
- **models.py**: Can be empty or contain test models
- Must be in `INSTALLED_APPS` for test discovery

## CI/CD Configuration

### GitHub Actions Workflows

#### codecov.yml (Main Test Pipeline)

**Triggers**: Push to main, pull requests

**Matrix Strategy**:
- Python versions: 3.10, 3.11, 3.12, 3.13, 3.14
- 6 Django/CMS combinations
- OS: ubuntu-latest

**Exclusions**:
- Python 3.14: Only Django 5.2+ (incompatible with older versions)
- Python 3.10-3.11: Not Django 6.0 (end of support)
- Python 3.12-3.13: Not Django 4.2 + CMS 3.11 (compatibility)

**Steps**:
1. Checkout code with fetch-depth: 2
2. Setup Python with matrix version
3. Install dependencies using `uv pip` for speed
4. Run `coverage run -m pytest`
5. Upload results to Codecov

#### lint-pr.yml (PR Validation)

Validates PR titles against conventional commit specification:
- Types: feat, fix, docs, style, refactor, test, chore, ci
- Format: `type(scope): description`
- Uses: `amannn/action-semantic-pull-request@v6`

#### docs.yml (Documentation Build)

**Two Jobs**:

1. **build**: Sphinx HTML generation
   - Python 3.11
   - Cache pip dependencies
   - Run `make html`

2. **spelling**: Spell-check documentation
   - Depends on build job
   - Run `make spelling`
   - Uses sphinxcontrib-spelling

### Dependabot Configuration

Automated GitHub Actions updates:
- Package ecosystem: `github-actions`
- Schedule: Weekly
- Commit message prefix: `ci:`

## Documentation Setup

### Sphinx Configuration (docs/source/conf.py)

**Extensions**:
- `sphinx.ext.autodoc`: Auto-generate API docs
- `sphinx.ext.doctest`: Test code examples
- `sphinx.ext.intersphinx`: Link to other projects
- `sphinx.ext.todo`: TODO notes
- `sphinx.ext.coverage`: Documentation coverage
- `sphinx_copybutton`: Copy code button
- `sphinxcontrib.spelling`: Spell checking

**Theme**: Furo (modern, responsive)

**Version**: Read from package `__version__`

**Intersphinx**: Links to Python 3 documentation

### Documentation Requirements (docs/requirements.txt)

- Sphinx
- furo (theme)
- sphinx-autobuild (live reload)
- sphinx-copybutton (code copy buttons)
- sphinxcontrib-spelling (spell checking)
- pip-tools (dependency management)

### Read the Docs (.readthedocs.yaml)

**Configuration**:
- Version: 2
- Build OS: ubuntu-22.04
- Python: 3.11
- Sphinx configuration path
- Output formats: HTML, EPUB, PDF
- Install from docs/requirements.txt

## Package Structure

### Version Management

**djangocms_custom_content/__init__.py**:
```python
__version__ = "0.1.0"
default_app_config = "djangocms_custom_content.apps.CustomContentConfig"
```

Version is:
- Defined in `__init__.py`
- Read by setuptools via `pyproject.toml`: `version = { attr = "package.__version__" }`
- Used in documentation via Sphinx conf.py

### Django App Configuration

**apps.py**:
```python
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class CustomContentConfig(AppConfig):
    name = "djangocms_custom_content"
    verbose_name = _("django CMS Custom Content")
    default_auto_field = "django.db.models.BigAutoField"
```

### CMS Plugin Structure

**models.py**: CMSPlugin subclass
- Inherit from `cms.models.CMSPlugin`
- Define fields for plugin configuration
- Use `gettext_lazy` for translatable strings
- Include `verbose_name` and `verbose_name_plural`

**cms_plugins.py**: Plugin registration
- Subclass `CMSPluginBase`
- Decorate with `@plugin_pool.register_plugin`
- Define `model`, `name`, `render_template`
- Set `cache = True` for performance
- Configure `fieldsets` for admin interface
- Override `render()` for custom context or template selection

**templates/**: Plugin templates
- Use `{% load cms_tags %}`
- Access instance via `{{ instance }}`
- Render child plugins if `allow_children = True`

## Development Workflow

### Initial Setup

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd <project-name>
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e .
   pip install -r tests/requirements/base.txt
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Running Tests

**All tests**:
```bash
pytest
```

**With coverage**:
```bash
coverage run -m pytest
coverage report
coverage html  # Generate HTML report
```

**Specific test file**:
```bash
pytest tests/test_plugin.py
```

**Specific Django/CMS version**:
```bash
pip install -r tests/requirements/dj50_cms41.txt
pytest
```

### Code Quality

**Run pre-commit on all files**:
```bash
pre-commit run --all-files
```

**Manual formatting**:
```bash
ruff check . --fix
ruff format .
```

**Import sorting**:
```bash
isort .
```

### Documentation

**Build documentation**:
```bash
cd docs
make html
```

**Live documentation server**:
```bash
cd docs
make run  # Serves at http://0.0.0.0:8001
```

**Spell check**:
```bash
cd docs
make spelling
```

## Release Process

### Version Management

1. **Update version** in `package_name/__init__.py`:
   ```python
   __version__ = "1.0.0"
   ```

2. **Update CHANGELOG.rst** (if exists) with changes

3. **Commit version bump**:
   ```bash
   git add package_name/__init__.py CHANGELOG.rst
   git commit -m "chore: bump version to 1.0.0"
   ```

4. **Create git tag**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin main
   git push origin v1.0.0
   ```

5. **GitHub Release**:
   - Go to GitHub Releases
   - Create new release from tag
   - Add release notes
   - Publish release

6. **Automated PyPI Upload**:
   - GitHub Actions workflow triggers on release
   - Builds distribution packages
   - Uploads to PyPI using trusted publishing

### Pre-release Checklist

- [ ] All tests passing on CI
- [ ] Documentation builds without errors
- [ ] Version number updated
- [ ] CHANGELOG updated
- [ ] No uncommitted changes
- [ ] Pre-commit hooks pass

## Code Quality Standards

### Python Code

**Line Length**: 119-120 characters (ruff/flake8)

**Import Order** (isort):
1. FUTURE: `from __future__ import`
2. STDLIB: Python standard library
3. DJANGO: Django imports
4. CMS: django CMS imports
5. THIRDPARTY: External packages
6. FIRSTPARTY: Your package
7. LOCALFOLDER: Relative imports

**Linting Rules** (ruff):
- E: PEP 8 errors
- F: Pyflakes
- I: Import sorting
- W: PEP 8 warnings

**Ignored Rules**:
- E501: Line too long (handled by formatter)
- E701: Multiple statements on one line
- F401: Module imported but unused (sometimes needed)
- F403: Star imports (sometimes needed in Django settings)

### Template Code

**Django Templates**:
- Use `{% load cms_tags %}` for CMS functionality
- Use `{% load sekizai_tags %}` for CSS/JS blocks
- 2-space indentation
- 120 character line length

### RST Documentation

- 80 character line length
- Use proper heading hierarchy
- Include code blocks with language specification
- Add docstrings to public APIs

## Compatibility Guidelines

### Django CMS Version Support

**CMS v3** (3.11):
- Last major version before v4
- Uses Page model directly
- publish/unpublish methods on page objects
- No versioning system

**CMS v4** (4.1+):
- Requires djangocms-versioning
- PageContent model separate from Page
- Version-based publishing workflow
- Optional djangocms-url-manager support

**CMS v5** (5.0+):
- Latest architecture
- Django 5.2+ support
- Enhanced versioning features

### Django Version Support

Follow django CMS compatibility:
- **Django 4.2**: LTS, supports CMS 3.11 and 4.1
- **Django 5.0-5.1**: Current, supports CMS 4.1
- **Django 5.2**: Latest, supports CMS 5.0
- **Django 6.0**: Future, supports CMS 5.0

### Python Version Support

Support latest 3-5 Python versions:
- Minimum: Python 3.10
- Recommended: Python 3.11 or 3.12
- Maximum: Python 3.14 (or latest stable)

Use `python_requires = ">=3.10"` in pyproject.toml

## Common Patterns

### Plugin with Dynamic Templates

```python
class CustomPlugin(CMSPluginBase):
    model = CustomModel
    render_template = "default.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        if instance.template:
            self.render_template = instance.template
        return context
```

### CMS v3/v4 Compatible Tests

```python
from django.apps import apps

DJANGO_CMS4 = apps.is_installed("djangocms_versioning")

class MyTestCase(TestFixture, TestCase):
    def test_something(self):
        page = self.create_page("Test")
        self.publish(page, "en")
        # Works with both CMS v3 and v4
```

### Translatable Strings

```python
from django.utils.translation import gettext_lazy as _

class CustomContent(CMSPlugin):
    content = models.TextField(
        _("Content"),
        help_text=_("Enter custom content here."),
    )
```

## Troubleshooting

### Pre-commit Hook Failures

If pre-commit hooks fail:
```bash
# Fix automatically
pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

### Test Database Issues

Clear test database:
```bash
rm mydatabase  # SQLite database from tests
python manage.py migrate --run-syncdb
```

### Import Errors in Tests

Ensure package is installed in editable mode:
```bash
pip install -e .
```

### Documentation Build Errors

Check dependencies:
```bash
pip install -r docs/requirements.txt
cd docs
make clean
make html
```

## Best Practices

1. **Always run tests before committing**
2. **Use pre-commit hooks** for consistent code quality
3. **Write tests for new features** to maintain coverage
4. **Update documentation** when adding features
5. **Follow conventional commits** for PR titles
6. **Test across Django/CMS versions** using tox or CI
7. **Keep dependencies updated** via dependabot
8. **Use semantic versioning** for releases
9. **Document breaking changes** in CHANGELOG
10. **Maintain backwards compatibility** when possible

## Resources

- [django CMS Documentation](https://docs.django-cms.org/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## Summary

This setup provides:
- ✅ Multi-version testing (Python 3.10-3.14, Django 4.2-6.0, CMS 3.11-5.0)
- ✅ Automated code quality (pre-commit, ruff, black, isort)
- ✅ Comprehensive CI/CD (GitHub Actions)
- ✅ Professional documentation (Sphinx, ReadTheDocs)
- ✅ Test coverage reporting (Codecov)
- ✅ Automated releases (GitHub Actions + PyPI)
- ✅ Dependency management (dependabot)
- ✅ CMS v3/v4/v5 compatibility patterns

This is the standard setup used across the django CMS ecosystem for professional plugin and package development.
