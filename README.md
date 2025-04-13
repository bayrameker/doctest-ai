# DocTest AI - Intelligent Test Scenario Generator

An advanced AI-powered platform for automated test scenario generation from documentation.

## Overview

DocTest AI is a sophisticated platform that combines document analysis with artificial intelligence to automatically generate comprehensive test scenarios. The system intelligently processes various document types and creates structured test cases ready for automation.

## Features

- **Smart Document Processing**
  - Multi-format support (PDF, DOC, DOCX, TXT)
  - Advanced document analysis with NeuraDoc
  - Intelligent content extraction with Docling
  - Image and table recognition
  - Large document optimization (100+ pages)

- **AI Integration**
  - Multiple AI model support
    - OpenAI GPT-4
    - Azure OpenAI
    - Local LLM support (Ollama)
  - Smart model selection based on content
  - 98% accuracy in scenario generation

- **Test Framework Integration**
  - Selenium WebDriver
  - Cypress
  - Playwright
  - Cucumber/Gherkin
  - Automated test code generation

- **Modern Interface**
  - Clean, responsive design
  - Dark/Light themes
  - Multi-language support (EN/TR)
  - Real-time processing status
  - Interactive result viewer

## Technical Requirements

- Python 3.11+
- PostgreSQL 16+
- Required packages listed in `pyproject.toml`

## Installation

1. Clone the repository:
```bash
git clone https://github.com/bayrameker/doctest-ai.git
cd doctest-ai
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up environment variables:
```bash
FLASK_APP=app.py
DATABASE_URL=postgresql://user:password@localhost:5432/doctest
```

4. Initialize database:
```bash
flask db upgrade
```

## Usage

Start the application:

```bash
gunicorn --bind 0.0.0.0:5000 --timeout 300 main:app
```

Access the web interface at `http://localhost:5000`

## API Documentation

The platform provides a RESTful API for integration with existing test management systems. Full API documentation is available at `/api/docs`.

## Development

### Architecture
- Flask-based backend
- SQLAlchemy ORM
- Modern JavaScript frontend
- Responsive Bootstrap UI
- Modular document processing pipeline

### Key Components
- NeuraDoc: Enhanced document analysis
- Docling: LLM-optimized parsing
- Smart Processing: Intelligent content extraction
- Test Generator: AI-powered scenario creation

## Testing

Run the test suite:

```bash
pytest tests/
```

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please use the GitHub issue tracker.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Acknowledgments

- Thanks to all contributors who have helped shape this project
- Built with support from the open-source community