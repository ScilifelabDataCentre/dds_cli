# ProjectDownloader Tests

This directory contains comprehensive tests for the `ProjectDownloader` GUI utility class.

## Test Files

### `test_project_downloader.py`
Unit tests for the `ProjectDownloader` class, covering:
- Basic functionality (initialization, callbacks, file operations)
- Error handling and edge cases
- Progress tracking and calculation
- Threading safety
- Context manager behavior

### `test_project_downloader_integration.py`
Integration tests that simulate real-world usage with the DDS system:
- Complete download workflows
- Selective file downloads
- Error scenarios (authentication, API errors, network failures)
- Cancellation handling
- Resource cleanup

## Running the Tests

### Run All Tests
```bash
# From the project root
python -m pytest tests/gui_tests/test_project_downloader*.py -v
```

### Run Unit Tests Only
```bash
python -m pytest tests/gui_tests/test_project_downloader.py -v
```

### Run Integration Tests Only
```bash
python -m pytest tests/gui_tests/test_project_downloader_integration.py -v
```

### Run with Coverage
```bash
python -m pytest tests/gui_tests/test_project_downloader*.py --cov=dds_cli.dds_gui.utils.project_downloader --cov-report=html
```

### Use the Test Runner Script
```bash
python tests/gui_tests/run_project_downloader_tests.py
```

## Test Categories

### Unit Tests (`test_project_downloader.py`)

#### `TestDownloadProgress`
- Tests the `DownloadProgress` dataclass
- Validates field initialization and error handling

#### `TestDownloadResult`
- Tests the `DownloadResult` dataclass
- Validates success and failure scenarios

#### `TestProjectDownloader`
- **Initialization**: Tests various initialization scenarios
- **Callbacks**: Tests progress, completion, and error callbacks
- **File Operations**: Tests file listing, info retrieval, and downloads
- **Error Handling**: Tests various error conditions
- **Threading**: Tests thread safety of progress updates
- **Cleanup**: Tests resource cleanup and context manager behavior

### Integration Tests (`test_project_downloader_integration.py`)

#### `TestProjectDownloaderIntegration`
- **Full Workflow**: Complete download process from start to finish
- **Selective Downloads**: Downloading specific files only
- **Single File Downloads**: Individual file download operations
- **Failure Scenarios**: Handling download failures gracefully
- **Cancellation**: Testing download cancellation
- **Authentication Errors**: Handling auth failures
- **API Errors**: Handling API communication failures
- **Resource Cleanup**: Ensuring proper cleanup on exit
- **Progress Accuracy**: Validating progress calculations

## Mock Strategy

The tests use comprehensive mocking to avoid dependencies on:
- Actual DDS API endpoints
- File system operations
- Network requests
- Authentication systems

### Key Mocks
- `dds_cli.data_getter.DataGetter`: Mocked data getter with realistic file data
- `dds_cli.directory.DDSDirectory`: Mocked staging directory
- File system operations: Mocked to avoid actual file creation
- Network requests: Mocked to simulate various response scenarios

## Test Data

The integration tests use realistic test data including:
- Multiple file types (CSV, JSON, Python)
- Different file sizes and compression states
- Realistic file paths and metadata
- Various error scenarios

## Coverage

The tests aim for comprehensive coverage of:
- All public methods and properties
- Error handling paths
- Edge cases and boundary conditions
- Threading scenarios
- Callback mechanisms
- Resource management

## Dependencies

The tests require:
- `pytest` for test framework
- `unittest.mock` for mocking
- `threading` for concurrency tests
- `pathlib` for path handling

## Notes

- Tests are designed to run quickly without external dependencies
- All file operations are mocked to avoid side effects
- Network operations are simulated to ensure reliability
- Threading tests verify thread safety of progress updates
- Integration tests provide confidence in real-world usage scenarios
