# CI/CD Pipeline Documentation

This project uses GitHub Actions for continuous integration and deployment.

## Workflows

### 1. Backend Tests (`backend-tests.yml`)
Runs Python/FastAPI backend tests using pytest.

**Triggers:**
- Push to `main` or `develop` branches (only if backend files change)
- Pull requests to `main` or `develop` (only if backend files change)

**What it does:**
- Sets up Python 3.13
- Installs Poetry and dependencies
- Caches virtualenv for faster runs
- Runs pytest with coverage
- Uploads coverage to Codecov

**Duration:** ~2-3 minutes

### 2. Frontend Tests (`frontend-tests.yml`)
Runs Flutter/Dart frontend tests.

**Triggers:**
- Push to `main` or `develop` branches (only if frontend files change)
- Pull requests to `main` or `develop` (only if frontend files change)

**What it does:**
- Sets up Flutter SDK (stable channel)
- Installs dependencies
- Runs code formatting check
- Runs static analysis (flutter analyze)
- Runs widget tests with coverage
- Uploads coverage to Codecov

**Duration:** ~3-4 minutes

### 3. Full CI Pipeline (`ci.yml`)
Runs both backend and frontend tests together.

**Triggers:**
- Push to `main` or `develop` branches (all files)
- Pull requests to `main` or `develop` (all files)

**What it does:**
- Runs backend and frontend tests in parallel
- Provides overall build status
- Fails if either backend or frontend tests fail

**Duration:** ~4-5 minutes (parallel execution)

## Setup Instructions

### 1. GitHub Repository Setup

The workflows are already configured and will run automatically when you push to GitHub. No additional setup needed for basic functionality.

### 2. Optional: Add Secrets

For production deployments or real API testing, add these secrets to your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:
   - `GOOGLE_API_KEY`: Your actual Gemini API key (for integration tests)

**Note:** The tests will use a mock API key if secrets aren't configured, so they'll still pass.

### 3. Optional: Codecov Integration

For coverage reports:

1. Sign up at [codecov.io](https://codecov.io)
2. Connect your GitHub repository
3. Add the Codecov token to GitHub secrets as `CODECOV_TOKEN` (optional, works without it for public repos)

## Workflow Files Location

```
.github/
└── workflows/
    ├── backend-tests.yml    # Backend-only tests
    ├── frontend-tests.yml   # Frontend-only tests
    └── ci.yml              # Combined CI pipeline
```

## Branch Protection Rules (Recommended)

To enforce passing tests before merging:

1. Go to **Settings** → **Branches**
2. Add a branch protection rule for `main`:
   - ✅ Require status checks to pass before merging
   - Select checks: `Backend Tests`, `Frontend Tests`
   - ✅ Require branches to be up to date before merging

## Local Testing Before Push

Always run tests locally before pushing:

### Backend:
```bash
cd backend
ai_backend/.venv/bin/python -m pytest -v
```
(On Windows: `ai_backend\.venv\Scripts\python.exe -m pytest -v`)

### Frontend:
```bash
cd flutter_app
flutter test
```

## Viewing Test Results

### On GitHub:
1. Go to **Actions** tab in your repository
2. Click on any workflow run
3. View logs and test results

### Coverage Reports:
- View on Codecov (if configured)
- Download coverage HTML reports from workflow artifacts

## Optimizations

The workflows include several optimizations:
- **Caching**: Dependencies are cached to speed up subsequent runs
- **Path filters**: Workflows only run when relevant files change
- **Parallel execution**: Backend and frontend tests run simultaneously
- **Matrix strategy**: Easy to add multiple Python/Flutter versions

## Troubleshooting

### Tests pass locally but fail in CI:
- Check environment variables (API keys)
- Verify Python/Flutter versions match
- Check for platform-specific issues (Windows vs Linux)

### Slow workflow execution:
- Cache might not be working (check cache keys)
- Dependencies might be reinstalling
- Consider splitting into more granular workflows

### Coverage upload fails:
- Codecov integration is optional
- Set `fail_ci_if_error: false` to make it non-blocking

## Adding More Workflows

To add new workflows (e.g., deployment, linting):

1. Create a new `.yml` file in `.github/workflows/`
2. Define triggers, jobs, and steps
3. Commit and push

Example workflow types:
- Deployment to production
- Code quality checks (linting, formatting)
- Security scanning
- Performance testing
- Documentation generation

## Status Badges

Add these badges to your README:

### Backend Tests
```markdown
![Backend Tests](https://github.com/YOUR_USERNAME/profu/actions/workflows/backend-tests.yml/badge.svg)
```

### Frontend Tests
```markdown
![Frontend Tests](https://github.com/YOUR_USERNAME/profu/actions/workflows/frontend-tests.yml/badge.svg)
```

### CI Pipeline
```markdown
![CI Pipeline](https://github.com/YOUR_USERNAME/profu/actions/workflows/ci.yml/badge.svg)
```

## Cost

GitHub Actions is **free** for public repositories with generous limits:
- 2,000 minutes/month for private repos (free tier)
- Unlimited for public repos

Your current setup uses ~5 minutes per push, so you're well within limits.

## Next Steps

1. **Push to GitHub**: The workflows will automatically run
2. **Check Actions tab**: View your first workflow runs
3. **Add branch protection**: Require passing tests before merge
4. **Monitor coverage**: Track test coverage over time
5. **Add status badges**: Show build status in README

## Support

For issues with workflows:
- Check the [GitHub Actions documentation](https://docs.github.com/en/actions)
- Review workflow logs in the Actions tab
- Test locally first to isolate CI-specific issues
