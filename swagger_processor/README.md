# Swagger Processor

A high-performance Rust library for processing OpenAPI/Swagger definitions with Python bindings. This library efficiently splits API definitions into individual components, normalizes paths, and merges related endpoints while maintaining optimal performance through parallel processing.

## Features

- **Fast API Definition Processing**: Leverages Rust's performance for rapid processing of large API definitions
- **Path Normalization**: Automatically normalizes versioned paths (e.g., `/v1/users`, `/v2/users` → `/users`)
- **Parallel Processing**: Uses multi-threading for optimal performance on large API definitions
- **Python Integration**: Seamless integration with Python projects through PyO3
- **Flexible Input**: Supports both local files and remote URLs (JSON/YAML)
- **Comprehensive Logging**: Built-in logging support for debugging and monitoring

## Prerequisites

Before installing this library, you'll need to set up the Rust toolchain and Maturin for building Python extensions.

### 1. Install Rust

#### Option A: Using rustup (Recommended)

```bash
# Install rustup (Rust installer and version management tool)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Follow the on-screen instructions, then restart your shell or run:
source ~/.cargo/env

# Verify installation
rustc --version
cargo --version
```

#### Option B: Using Package Managers

**macOS (Homebrew):**
```bash
brew install rust
```

**Ubuntu/Debian:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Windows:**
- Download and run the installer from [rustup.rs](https://rustup.rs/)
- Or use Chocolatey: `choco install rust`

### 2. Install Python Development Headers

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3-dev python3-pip
```

**macOS:**
```bash
# Usually included with Python installation
# If using Homebrew Python:
brew install python
```

**Windows:**
- Python development headers are typically included with Python installations from python.org
- If using conda: `conda install python-dev`

### 3. Install Maturin

Maturin is the build tool for creating Python extensions written in Rust.

```bash
# Install maturin using pip
pip install maturin

# Or using cargo
cargo install maturin

# Verify installation
maturin --version
```

## Development Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd swagger-processor
```

### 2. Set up Python Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Development Dependencies

```bash
# Install Python development dependencies
pip install maturin pytest black flake8 mypy

# Install additional dependencies if needed
pip install pyyaml requests
```

## Building and Installation

### Development Build

For development and testing, use the development build which includes debug symbols and is faster to compile:

```bash
# Build and install in development mode
maturin develop

# Or with specific Python interpreter
maturin develop --interpreter python3.9
```

This command:
- Compiles the Rust code in debug mode
- Creates Python bindings
- Installs the module in your current Python environment
- Allows for quick iteration during development

### Release Build

For production use or performance testing, create an optimized release build:

```bash
# Build optimized release version
maturin develop --release

# Or build wheel for distribution
maturin build --release
```

The release build:
- Enables all compiler optimizations
- Strips debug symbols
- Provides maximum runtime performance
- Takes longer to compile

### Building Wheels for Distribution

To create distributable wheel files:

```bash
# Build wheel for current platform
maturin build --release

# Build wheel for specific Python versions
maturin build --release --interpreter python3.8 python3.9 python3.10 python3.11

# The wheels will be created in target/wheels/
```

## Usage

After installation, you can use the library in Python:

```python
from swagger_processor import APIDefinitionProcessor
import logging

# Set up logging (optional)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create processor instance
processor = APIDefinitionProcessor(logger)

# Process API definition from URL
definitions = processor.process_api_definition("https://api.example.com/swagger.json")

# Process API definition from local file
definitions = processor.process_api_definition("./api-spec.yaml")

# Iterate through processed definitions
for definition in definitions:
    if definition['type'] == 'path':
        print(f"Path: {definition['path']}")
    elif definition['type'] == 'verb':
        print(f"Verb: {definition['verb']} {definition['path']}")
```

## Development Workflow

### 1. Make Changes

Edit the Rust source code in `src/lib.rs` or other Rust files.

### 2. Rebuild and Test

```bash
# Quick development rebuild
maturin develop

# Run Python tests
python -m pytest tests/

# Or run specific test
python test_example.py
```

### 3. Code Quality

```bash
# Format Rust code
cargo fmt

# Lint Rust code
cargo clippy

# Run Rust tests
cargo test

# Format Python code
black *.py tests/

# Lint Python code
flake8 *.py tests/
```

### 4. Performance Testing

```bash
# Build release version for performance testing
maturin develop --release

# Run performance tests
python benchmark.py
```

## Project Structure

```
swagger-processor/
├── src/
│   └── lib.rs              # Main Rust source code
├── Cargo.toml              # Rust dependencies and metadata
├── pyproject.toml          # Python project configuration
├── tests/                  # Python tests
├── examples/               # Usage examples
└── README.md              # This file
```

## Dependencies

### Rust Dependencies (Cargo.toml)

```toml
[dependencies]
pyo3 = { version = "0.25", features = ["extension-module"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
serde_yaml = "0.9"
reqwest = { version = "0.11", features = ["json"] }
tokio = { version = "1.0", features = ["full"] }
rayon = "1.7"
```

### Python Dependencies

```bash
pip install maturin pyyaml requests
```

## Troubleshooting

### Common Issues

1. **Rust not found**: Ensure Rust is installed and `~/.cargo/bin` is in your PATH
2. **Python headers missing**: Install python3-dev or python-devel package
3. **Maturin build fails**: Try updating maturin: `pip install --upgrade maturin`
4. **Permission denied**: Use virtual environment or `--user` flag with pip

### Debug Build Issues

```bash
# Clean build artifacts
cargo clean

# Rebuild with verbose output
maturin develop --verbose

# Check Rust compilation
cargo check
```

### Performance Issues

- Always use `--release` flag for production builds
- Monitor memory usage with large API definitions
- Enable logging to debug processing bottlenecks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request